import os
import time
from label_studio_sdk import LabelStudio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


LABEL_STUDIO_URL = os.getenv("LABEL_STUDIO_URL", "http://localhost:8080")  # Port von LS
LABEL_STUDIO_API_KEY = os.getenv("LABEL_STUDIO_API_KEY", "") #todo (Victor): add api key
LABEL_STUDIO_PROJECT_ID = int(os.getenv("LABEL_STUDIO_PROJECT_ID", "1"))

DATA_DIR = os.getenv("IMAGES_ROOT", "/data/images")

client = LabelStudio(base_url=LABEL_STUDIO_URL, api_key=LABEL_STUDIO_API_KEY)

class NewFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        path = event.src_path
        if path.lower().endswith((".jpg", ".jpeg", ".png")):
            print(f"[Watcher] Neues Bild erkannt: {path}")
            try:
                client.import_storage.local.sync(id=1)  # vorhandenes Storage synchronisieren
                print("[Watcher] Label Studio Storage synchronisiert.")
                #todo (Victor): funktioniert das syncen so überhaupt? und welcher Ordner muss dann angebunden werden?
            except Exception as e:
                print("[Watcher] Fehler bei Sync:", e)

def start_watcher():
    observer = Observer()
    event_handler = NewFileHandler()
    observer.schedule(event_handler, path=DATA_DIR, recursive=True)
    observer.start()
    print(f"[Watcher] Beobachtet: {DATA_DIR}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
