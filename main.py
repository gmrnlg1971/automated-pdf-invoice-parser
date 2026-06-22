import os
import json
import time
import threading
import queue
import base64
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pydantic import BaseModel
import fitz  # PyMuPDF
from openai import OpenAI

class InvoiceData(BaseModel):
    invoice_number: str | None
    vendor_name: str | None
    total_amount: float | None
    due_date: str | None

# Absolute paths to ensure it works anywhere
BASE_DIR = Path(__file__).parent.resolve()
INBOX_DIR = BASE_DIR / "inbox"
OUTBOX_DIR = BASE_DIR / "outbox"

INBOX_DIR.mkdir(exist_ok=True)
OUTBOX_DIR.mkdir(exist_ok=True)

pdf_queue = queue.Queue()

def is_file_locked(filepath):
    """Wait and verify the file is not locked by the OS (copying)."""
    try:
        # Check if size changes over a short delay.
        initial_size = os.path.getsize(filepath)
        time.sleep(0.5)
        if os.path.getsize(filepath) != initial_size:
            return True
        # Try opening for appending to check for locks
        with open(filepath, 'a'):
            pass
        return False
    except IOError:
        return True
    except Exception:
        return True

def process_pdf(filepath: Path):
    """Uses OpenAI Vision (gpt-4o) to extract invoice data."""
    print(f"[*] Processing: {filepath.name}")
    
    # Wait until file is unlocked
    retries = 10
    while is_file_locked(filepath) and retries > 0:
        time.sleep(1)
        retries -= 1
        
    if retries == 0:
        print(f"[!] File {filepath.name} is locked or inaccessible. Skipping.")
        return

    try:
        doc = fitz.open(str(filepath))
        if len(doc) == 0:
            print(f"[X] Empty PDF: {filepath.name}")
            return
            
        page = doc[0]
        pix = page.get_pixmap(dpi=150)
        image_bytes = pix.tobytes("jpeg")
        doc.close()

        base64_image = base64.b64encode(image_bytes).decode('utf-8')

        client = OpenAI()
        response = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract the invoice details from this image. Use null if not found. Make sure due_date is YYYY-MM-DD."},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                }
            ],
            response_format=InvoiceData
        )
        
        extracted_data = response.choices[0].message.parsed
        structured_data = extracted_data.model_dump()
        structured_data["status"] = "extracted"
        structured_data["original_file"] = filepath.name
        
        # Robust path replacement
        out_filename = filepath.stem + '.json'
        out_filepath = OUTBOX_DIR / out_filename
        
        # Don't overwrite silently, suffix if exists
        counter = 1
        while out_filepath.exists():
            out_filepath = OUTBOX_DIR / f"{filepath.stem}_{counter}.json"
            counter += 1

        with open(out_filepath, 'w') as f:
            json.dump(structured_data, f, indent=4)
            
        print(f"[+] Successfully extracted data to {out_filepath.name}")
    except Exception as e:
        print(f"[X] Failed to process {filepath.name}: {e}")

def worker():
    """Background worker processing the queue."""
    while True:
        filepath = pdf_queue.get()
        if filepath is None:
            break
        try:
            process_pdf(filepath)
        finally:
            pdf_queue.task_done()

class InvoiceHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
            
        filepath = Path(event.src_path)
        if filepath.suffix.lower() != '.pdf':
            return
            
        print(f"[+] New PDF detected: {filepath.name}. Queuing...")
        pdf_queue.put(filepath)

def sweep_inbox():
    """Scan inbox on startup to catch files dropped during downtime."""
    print("[*] Sweeping inbox for existing PDFs...")
    count = 0
    for file in INBOX_DIR.iterdir():
        if file.is_file() and file.suffix.lower() == '.pdf':
            print(f"[*] Found existing PDF: {file.name}. Queuing...")
            pdf_queue.put(file)
            count += 1
    print(f"[*] Queued {count} existing PDFs.")

if __name__ == "__main__":
    # Start worker thread
    worker_thread = threading.Thread(target=worker, daemon=True)
    worker_thread.start()

    # Initial sweep
    sweep_inbox()

    # Setup watchdog
    event_handler = InvoiceHandler()
    observer = Observer()
    observer.schedule(event_handler, str(INBOX_DIR), recursive=False)
    observer.start()
    print(f"Watching directory '{INBOX_DIR}' for new PDFs. Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        observer.stop()
        
    observer.join()
    print("Waiting for queue to empty...")
    pdf_queue.put(None)
    worker_thread.join()
