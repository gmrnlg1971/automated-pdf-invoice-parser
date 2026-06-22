# Automated PDF Invoice Parser (AI Automation Agency)

This is a production-ready template for an AI Automation Agency (AAA) workflow. It monitors a directory for incoming PDF invoices (or resumes, purchase orders, etc.), uses the OpenAI/Anthropic API to extract structured data via Vision/OCR, and dumps the standardized JSON payload for downstream insertion into Airtable, Google Sheets, or a CRM.

## Features
- **Automated Directory Monitoring:** Uses watchdog to listen for new PDF files.
- **Multimodal LLM Extraction:** Bypasses brittle OCR tools by using modern Vision LLMs (e.g., GPT-4o) or PDF text extraction combined with prompt engineering.
- **Structured JSON Output:** Guarantees a strict JSON schema for seamless API integrations via `pydantic`.

## Setup
1. `pip install -r requirements.txt` (requires `openai`, `pydantic`, `PyPDF2`, `watchdog`)
2. Export your API Key: `export OPENAI_API_KEY="your-key-here"`
3. Run the watcher: `python main.py`

## Usage
Simply drop any PDF invoice into the `./inbox` directory and watch the structured data appear in the `./outbox` directory in real-time.
