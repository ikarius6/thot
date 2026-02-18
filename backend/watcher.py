import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from database import SessionLocal
from scanner import scan_file
from queue_worker import tagging_queue

class ImageEventHandler(FileSystemEventHandler):
    """Handles file system events for images."""
    
    def on_created(self, event):
        if event.is_directory:
            return
        if not event.src_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            return
        
        print(f"Watcher: Detected new file {event.src_path}")
        self._process_file(event.src_path)

    def on_moved(self, event):
        if event.is_directory:
            return
        if not event.dest_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            return

        print(f"Watcher: Detected move/rename {event.dest_path}")
        self._process_file(event.dest_path)

    def _process_file(self, path):
        # Small delay to ensure file is fully written/moved
        time.sleep(0.5)
        
        db = SessionLocal()
        try:
            image = scan_file(path, db)
            if image:
                # If we got an image (new or existing), ensure it's tagged
                # scan_file returns existing images too, so we can check if it needs tagging
                # But enqueue_image handles "already tagged" check internally via queue worker optims or we check here?
                # queue_worker checks if hash is tagged. So just enqueue it.
                print(f"Watcher: Enqueueing {image.filename} for tagging")
                tagging_queue.enqueue_image(image.id)
        except Exception as e:
            print(f"Watcher: Error processing {path}: {e}")
        finally:
            db.close()

    def on_deleted(self, event):
        if event.is_directory:
            return
        if not event.src_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            return

        print(f"Watcher: Detected deletion {event.src_path}")
        
        db = SessionLocal()
        try:
            from database import Image as DBImage
            # Find image by path
            image = db.query(DBImage).filter(DBImage.path == event.src_path).first()
            if image:
                print(f"Watcher: Mark inactive image {image.id} from DB")
                image.is_active = 0
                db.commit()
            else:
                print(f"Watcher: Deleted file not found in DB: {event.src_path}")
        except Exception as e:
            print(f"Watcher: Error handling deletion for {event.src_path}: {e}")
        finally:
            db.close()


class FolderWatcher:
    """Manages the watchdog observer."""
    
    def __init__(self):
        self.observer = Observer()
        self.handler = ImageEventHandler()
        self.watches = {}

    def start(self):
        """Start the observer."""
        if not self.observer.is_alive():
            try:
                self.observer.start()
                print("Watcher: Started")
            except RuntimeError:
                # Already started
                pass

    def stop(self):
        """Stop the observer."""
        self.observer.stop()
        self.observer.join()
        print("Watcher: Stopped")

    def add_folder(self, path):
        """Add a folder to watch."""
        if path in self.watches:
            return
        
        try:
            watch = self.observer.schedule(self.handler, path, recursive=False)
            self.watches[path] = watch
            print(f"Watcher: Monitoring {path}")
        except Exception as e:
            print(f"Watcher: Failed to watch {path}: {e}")

    def remove_folder(self, path):
        """Remove a folder from watch."""
        if path in self.watches:
            self.observer.unschedule(self.watches[path])
            del self.watches[path]
            print(f"Watcher: Stopped monitoring {path}")

# Singleton instance
folder_watcher = FolderWatcher()
