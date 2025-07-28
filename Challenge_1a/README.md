
# Challenge 1a: PDF Processing Solution

## Overview
This repository provides a complete solution for **Challenge 1a of the Adobe India Hackathon 2025**. The objective is to implement a PDF processing pipeline that extracts structured outlines from PDF documents and outputs JSON files conforming to a specified schema. The entire solution is containerized with Docker and meets the required constraints.

---

## Solution Highlights

- 🧠 Extracts title and outline hierarchy (H1–H5) from PDFs using PyMuPDF
- 📦 Packaged in a lightweight Docker container
- 🚫 No internet dependency at runtime
- ✅ Output JSON conforms to the schema at `sample_dataset/schema/output_schema.json`

---

## Folder Structure

```
Challenge_1a/
├── sample_dataset/
│   ├── pdfs/            # Input PDF files for testing
│   ├── outputs/         # Output JSON samples
│   └── schema/
│       └── output_schema.json
├── process_pdfs.py      # Main Python script
├── requirements.txt     # Required libraries
├── Dockerfile           # Container definition
└── README.md            # This file
```

---

## Build Instructions

To build the Docker image (targeting AMD64):

```bash
docker build --platform=linux/amd64 -t adobe1a.processor .
```

---

## Run Instructions

To run the processor using mounted folders:

```bash
docker run --rm ^
  -v %cd%\input:/app/input:ro ^
  -v %cd%\output:/app/output ^
  --network none ^
  adobe1a.processor
```

📁 Place PDFs in `input/`, and JSONs will appear in `output/`.

---

## Output Format

Each `.pdf` file will produce a `.json` file with this format:

```json
{
  "title": "Document Title",
  "outline": [
    {
      "level": "H1",
      "text": "Section Heading",
      "page": 1
    },
    ...
  ]
}
```

The structure follows `sample_dataset/schema/output_schema.json`.

---

## Performance Testing

### On Windows CMD

You can measure execution time **manually** using a stopwatch or by noting start/end time:

```cmd
docker run --rm -v %cd%\input:/app/input:ro -v %cd%\output:/app/output --network none adobe1a.processor
```

### On PowerShell (Automatic)

Use PowerShell to time the execution:

```powershell
Measure-Command {
  docker run --rm `
    -v "${PWD}/input:/app/input:ro" `
    -v "${PWD}/output:/app/output" `
    --network none `
    adobe1a.processor
}
```

You’ll see output like:

```
Seconds             : 8
Milliseconds        : 320
...
```

✅ Must be under **10 seconds** for a 50-page PDF.

---

## Requirements Checklist

- [x] All PDFs in input directory are processed
- [x] JSON output files generated
- [x] Output conforms to schema
- [x] Processing completes under 10s for large PDFs
- [x] No internet access required
- [x] Memory under 16GB
- [x] Docker runs on AMD64 CPU architecture

---

## License

This project uses only open-source libraries and does not rely on external services or proprietary models.

---

## Author

Developed by [Jagadeeswar Reddy](https://github.com/Jagadeeswar1973)

