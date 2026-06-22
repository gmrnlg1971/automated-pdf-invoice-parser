import os
import json
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Ensure directories exist
os.makedirs("inbox", exist_ok=True)
os.makedirs("outbox", exist_ok=True)

class InvoiceHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith('.pdf'):
            return
        
        filepath = event.src_path
        filename = os.path.basename(filepath)
        print(f"[*] New PDF detected: {filename}")
        
        # Simulate processing delay
        time.sleep(1)
        
        # Here you would:
        # 1. Read PDF text (e.g. PyPDF2) or use Vision API
        # 2. Call OpenAI API with structured output schema (Pydantic)
        # 3. Save or forward the JSON response
        
        # Mock structured data response
        structured_data = {
            "invoice_number": "INV-10294",
            "vendor_name": "Acme Corp",
            "total_amount": 1499.99,
            "due_date": "2026-07-15",
            "status": "extracted"
        }
        
        out_filepath = os.path.join("outbox", filename.replace('.pdf', '.json'))
        with open(out_filepath, 'w') as f:
            json.dump(structured_data, f, indent=4)
            
        print(f"[+] Successfully extracted data to {out_filepath}")

if __name__ == "__main__":
    path = "inbox"
    event_handler = InvoiceHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    observer.start()
    print(f"Watching directory '{path}' for new PDFs. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
