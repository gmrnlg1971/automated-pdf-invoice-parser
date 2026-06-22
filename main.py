import os
import json
import time
import threading
import queue
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

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
    """Simulates OCR extraction and saves JSON."""
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
        # Simulate processing delay
        time.sleep(1)
        
        # Mock structured data response
        structured_data = {
            "invoice_number": "INV-10294",
            "vendor_name": "Acme Corp",
            "total_amount": 1499.99,
            "due_date": "2026-07-15",
            "status": "extracted",
            "original_file": filepath.name
        }
        
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
