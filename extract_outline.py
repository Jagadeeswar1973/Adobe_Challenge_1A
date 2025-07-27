
import fitz  # PyMuPDF
import re
import os
import json

def extract_pdf_outline(pdf_path):
    # Open the PDF document
    doc = fitz.open(pdf_path)
    lines = []
    # Extract text lines with font size and position
    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]
        for bi, block in enumerate(blocks):
            if "lines" not in block:
                continue
            for line in block["lines"]:
                # Concatenate all spans' text in the line
                text = "".join(span["text"].strip() + " " 
                               for span in line["spans"] if span["text"].strip())
                text = text.strip()
                if not text:
                    continue
                # Average font size of spans in this line
                avg_font = 0
                if line["spans"]:
                    avg_font = sum(span["size"] for span in line["spans"]) / len(line["spans"])
                lines.append({
                    "text": text,
                    "font_size": avg_font,
                    "page": page_num + 1,
                    "block": page_num * 1000 + bi,  # unique block identifier across pages
                    "y": block.get("bbox", [0, 0, 0, 0])[1]  # y-coordinate of the line for ordering
                })
    # Sort lines by page, block, then vertical position
    lines.sort(key=lambda x: (x["page"], x["block"], x["y"]))
    
    # Merge lines that belong to the same block and font (to handle wrapped lines and numbered lines)
    merged_lines = []
    i = 0
    while i < len(lines):
        # If the line is just a section number (e.g., "2." or "4)"), merge it with the next line
        if re.fullmatch(r"[0-9]+[\.\)]", lines[i]["text"]) and i + 1 < len(lines):
            lines[i+1]["text"] = lines[i]["text"].rstrip() + " " + lines[i+1]["text"]
            # Carry over the larger font size (just in case of size mismatch)
            lines[i+1]["font_size"] = max(lines[i]["font_size"], lines[i+1]["font_size"])
            i += 1
            continue
        # If current and next line have the same block and font size, decide on merging
        if (i + 1 < len(lines) and lines[i]["block"] == lines[i+1]["block"] and 
                round(lines[i]["font_size"]) == round(lines[i+1]["font_size"])):
            cur_text = lines[i]["text"].strip()
            nxt_text = lines[i+1]["text"].strip()
            # If current ends with ':' and next starts with '-', do NOT merge (separate heading vs bullet)
            if cur_text.endswith(":") and nxt_text.startswith("-"):
                merged_lines.append(lines[i])
                i += 1
                continue
            else:
                # Merge current line into next line
                lines[i+1]["text"] = lines[i]["text"].rstrip() + " " + lines[i+1]["text"]
                lines[i+1]["font_size"] = max(lines[i]["font_size"], lines[i+1]["font_size"])
                # Do not append current line to merged_lines (it's merged into next)
        else:
            # No merge needed; add the current line as is
            merged_lines.append(lines[i])
        i += 1
    # Append the last line if it wasn't already added
    if i == len(lines) and (not merged_lines or merged_lines[-1] != lines[-1]):
        merged_lines.append(lines[-1])
    lines = merged_lines
    
    if not lines:
        return {"title": "", "outline": []}
    
    # Identify document title from the largest font size lines
    font_counts = {}
    for line in lines:
        fs = round(line["font_size"])
        font_counts[fs] = font_counts.get(fs, 0) + 1
    sorted_fonts = sorted(font_counts.keys(), reverse=True)
    largest_font = sorted_fonts[0]
    # Collect all lines that use this largest font size (they likely form the title together)
    title_lines = [ln for ln in lines if round(ln["font_size"]) == largest_font]
    title_lines.sort(key=lambda x: (x["page"], x["y"]))
    title_text = " ".join(ln["text"] for ln in title_lines).strip()
    # Compress any 3+ repeated letters in title (fix overlapping text artifacts)
    title_text = re.sub(r'([A-Za-z])\1{2,}', r'\1', title_text)
    # Remove title lines from further outline processing
    lines = [ln for ln in lines if round(ln["font_size"]) != largest_font]
    
    # Recompute font frequencies after removing title
    font_counts.clear()
    for line in lines:
        fs = round(line["font_size"])
        font_counts[fs] = font_counts.get(fs, 0) + 1
    sorted_fonts = sorted(font_counts.keys(), reverse=True)
    if not sorted_fonts:
        # No content lines left (rare case)
        return {"title": title_text, "outline": []}
    
    # Heuristic: drop the most frequent font if it dominates (likely body text)
    total_lines = sum(font_counts.values())
    if font_counts.get(sorted_fonts[0], 0) > 0.5 * total_lines:
        # If the largest font size accounts for more than half of lines, it's probably body text
        sorted_fonts = sorted_fonts[1:]
    else:
        # Otherwise, if a smaller font is very common, drop that common font (body text) from consideration
        most_freq_font = max(font_counts, key=font_counts.get)
        if most_freq_font != sorted_fonts[0] and font_counts[most_freq_font] > 0.3 * total_lines:
            sorted_fonts = [fs for fs in sorted_fonts if fs != most_freq_font]
    
    # Determine heading font levels (H1..H5)
    heading_fonts = []
    if sorted_fonts:
        # Always include the largest font (even if it appears only once) as a heading level
        heading_fonts.append(sorted_fonts[0])
        # Include subsequent font sizes only if they appear in multiple lines (to avoid random large text)
        for fs in sorted_fonts[1:]:
            if len(heading_fonts) >= 5:
                break
            if font_counts.get(fs, 0) > 1:
                heading_fonts.append(fs)
    heading_fonts.sort(reverse=True)
    level_map = {fs: f"H{idx}" for idx, fs in enumerate(heading_fonts, start=1)}
    
    # Build the outline by filtering lines that qualify as headings
    outline = []
    common_labels = {"Name", "Age", "Date", "Signature", "S.No", "Relationship", 
                     "Service", "Designation", "PAY + SI + NPA", "Rs."}
    for line in lines:
        fs = round(line["font_size"])
        if fs not in level_map:
            continue  # skip lines that are not in identified heading font sizes
        text = line["text"].strip()
        # Remove leading section numbers like "1. " or "3.2 " from the text
        text_no_num = re.sub(r'^[0-9]+\.\s*', '', text)
        # Skip if text (after removing numbering) is empty or too short to be a heading
        if not text_no_num or len(text_no_num) < 4:
            continue
        # Skip pure numeric strings (like "1.1.1") or common form labels
        if re.fullmatch(r"[0-9.]+", text_no_num) or text_no_num in common_labels:
            continue
        # Skip enumerated list items like "(a)", "(i)" which are likely not section headings
        if text_no_num[0] == '(' and re.match(r'^\([A-Za-z0-9]+\)', text_no_num):
            continue
        # Skip lines that end with a period (likely sentence), or known non-heading patterns
        if text_no_num.endswith('.') or text_no_num.startswith("Whether") or text_no_num.startswith("Name of") or text_no_num.startswith("Date of"):
            continue
        if ("Service Book" in text_no_num or "Government Servant" in text_no_num or 
            text_no_num.lower().startswith("version") or 
            (text_no_num.endswith("Board") and len(text_no_num.split()) > 2) or 
            re.search(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\b.*\b\d{4}\b", text_no_num)):
            # Skip lines that look like dates or version info, etc.
            continue
        outline.append({
            "level": level_map[fs],
            "text": text_no_num,
            "page": line["page"]
        })
    
    # Remove duplicate texts (e.g., running headers repeated on each page)
    seen = {}
    for item in outline:
        seen[item["text"]] = seen.get(item["text"], 0) + 1
    outline = [item for item in outline if seen[item["text"]] == 1]
    
    # Merge fragmented outline entries:
    # If two consecutive items have the same level and page, and the first does not end in '.' or ':'
    # and the second starts with a lowercase letter, merge them into one line.
    merged_outline = []
    for item in outline:
        if merged_outline:
            prev = merged_outline[-1]
            if (prev["level"] == item["level"] and prev["page"] == item["page"] and 
                    not prev["text"].endswith(('.', ':')) and item["text"][0].islower()):
                # Merge with previous item
                prev["text"] += " " + item["text"]
                continue
        merged_outline.append(item)
    outline = merged_outline
    
    # If the first outline item is a fragment (starts with lowercase), drop it
    if outline and outline[0]["text"][0].islower():
        outline.pop(0)
    
    return {"title": title_text, "outline": outline}

# Main function to process all PDFs in input directory
def main():
    input_dir = "input_pdfs"
    output_dir = "output_json"
    os.makedirs(output_dir, exist_ok=True)
    pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print(f"⚠️ No PDF files found in '{input_dir}'. Please add PDFs and rerun.")
        return
    for filename in pdf_files:
        pdf_path = os.path.join(input_dir, filename)
        result = extract_pdf_outline(pdf_path)
        output_path = os.path.join(output_dir, filename.replace(".pdf", ".json"))
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"Processed '{filename}' -> outline saved to '{output_path}'")

if __name__ == "__main__":
    main()
