import threading
import time
from database import SessionLocal, Image, ImageHash, TagQueue
from ai import tag_image


class TaggingQueue:
    """Background worker that processes a tagging queue one image at a time.
    
    Tags are stored on ImageHash, so duplicates share tags automatically.
    If an image's hash already has tags, it's skipped (no AI call needed).
    """

    def __init__(self):
        self._thread = None
        self._pause_event = threading.Event()  # Set = running, Clear = paused
        self._stop_event = threading.Event()   # Set = stop requested
        self._pause_event.set()  # Start in "running" state
        self._state = "idle"  # idle / running / paused / stopped
        self._current_image_id = None
        self._lock = threading.Lock()

    # ── Public API ──────────────────────────────────────────────

    def enqueue_image(self, image_id: int):
        """Add a single image to the queue and ensure worker is running."""
        db = SessionLocal()
        try:
            # Check if already in queue
            exists = db.query(TagQueue).filter(
                TagQueue.image_id == image_id, 
                TagQueue.status.in_(["pending", "processing"])
            ).first()
            if not exists:
                entry = TagQueue(image_id=image_id, status="pending")
                db.add(entry)
                db.commit()
        finally:
            db.close()
        
        
        # Ensure worker is running
        self.start_worker_thread()

    def start_worker_thread(self):
        """Start the worker thread if not already running."""
        if self._thread and self._thread.is_alive():
            return
        
        self._stop_event.clear()
        self._pause_event.set()
        self._state = "running"
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def start(self):
        """Enqueue all images whose hash has no tags and start processing."""
        db = SessionLocal()
        try:
            # Clear any old queue entries (optional, but keeps it clean for a "fresh start")
            # For background watching, we might NOT want to clear, but "start" implies "restart/scan-all" usually.
            # I will keep the logic to clear pending/processing to avoid duplicates if they are re-added.
            db.query(TagQueue).filter(TagQueue.status.in_(["pending", "processing"])).delete(synchronize_session="fetch")
            db.commit()

            # Find all images whose hash has no tags (one per unique hash)
            untagged_images = (
                db.query(Image)
                .join(ImageHash, Image.hash_id == ImageHash.id)
                .filter((ImageHash.tags == None) | (ImageHash.tags == ""))
                .all()
            )

            # Deduplicate by hash_id — only queue one image per hash
            seen_hashes = set()
            to_queue = []
            for img in untagged_images:
                if img.hash_id not in seen_hashes:
                    seen_hashes.add(img.hash_id)
                    to_queue.append(img)

            if not to_queue:
                # Even if no images, we can start the worker to listen for future ones
                self.start_worker_thread()
                return {"message": "No untagged images found, worker started", "total": 0}

            for img in to_queue:
                entry = TagQueue(image_id=img.id, status="pending")
                db.add(entry)
            db.commit()

            total = len(to_queue)
        finally:
            db.close()

        self.start_worker_thread()
        return {"message": f"Started tagging {total} unique hashes", "total": total}

    def pause(self):
        """Pause after the current image finishes."""
        self._pause_event.clear()
        self._state = "paused"
        return {"message": "Queue paused"}

    def resume(self):
        """Resume processing."""
        self._pause_event.set()
        self._state = "running"
        return {"message": "Queue resumed"}

    def stop(self):
        """Stop processing and clear pending items."""
        self._stop_event.set()
        self._pause_event.set()  # Unblock if paused so thread can exit
        self._state = "stopped"

        db = SessionLocal()
        try:
            db.query(TagQueue).filter(TagQueue.status.in_(["pending", "processing"])).delete(synchronize_session="fetch")
            db.commit()
        finally:
            db.close()

        self._current_image_id = None
        self._state = "idle"
        return {"message": "Queue stopped and cleared"}

    def get_status(self):
        """Return current queue progress."""
        db = SessionLocal()
        try:
            total = db.query(TagQueue).count()
            done = db.query(TagQueue).filter(TagQueue.status == "done").count()
            errors = db.query(TagQueue).filter(TagQueue.status == "error").count()
            pending = db.query(TagQueue).filter(TagQueue.status.in_(["pending", "processing"])).count()
        finally:
            db.close()

        return {
            "state": self._state,
            "total": total,
            "done": done,
            "errors": errors,
            "pending": pending,
            "current_image_id": self._current_image_id,
        }

    # ── Worker loop ─────────────────────────────────────────────

    def _worker_loop(self):
        """Main loop: pick next pending item, tag its hash, repeat."""
        while not self._stop_event.is_set():
            self._pause_event.wait()

            if self._stop_event.is_set():
                break

            db = SessionLocal()
            image = None
            item = None
            try:
                item = db.query(TagQueue).filter(TagQueue.status == "pending").first()
                if not item:
                    self._state = "idle"
                    self._current_image_id = None
                    time.sleep(1) # Wait for new items
                    continue
                
                self._state = "running"
                item.status = "processing"
                db.commit()

                image = db.query(Image).filter(Image.id == item.image_id).first()
                if not image or not image.hash_id:
                    item.status = "error"
                    item.error_msg = "Image or hash not found"
                    db.commit()
                    continue

                hash_entry = db.query(ImageHash).filter(ImageHash.id == image.hash_id).first()

                # Skip if this hash already has tags (tagged by another duplicate)
                if hash_entry and hash_entry.tags:
                    item.status = "done"
                    db.commit()
                    print(f"Queue: Skipped image {image.id} — hash already tagged")
                    continue

                self._current_image_id = image.id
            finally:
                db.close()

            # Do the actual tagging (slow, GPU-bound)
            if image:
                try:
                    tags = tag_image(image.path)

                    db2 = SessionLocal()
                    try:
                        # Write tags to the hash (shared by all duplicates)
                        h = db2.query(ImageHash).filter(ImageHash.id == image.hash_id).first()
                        if h:
                            h.tags = tags
                        # Mark queue item as done
                        q_item = db2.query(TagQueue).filter(
                            TagQueue.image_id == image.id, TagQueue.status == "processing"
                        ).first()
                        if q_item:
                            q_item.status = "done"
                        db2.commit()

                        dup_count = db2.query(Image).filter(Image.hash_id == image.hash_id).count()
                        print(f"Queue: Tagged hash for image {image.id} ({dup_count} copies): {tags[:80]}...")
                    finally:
                        db2.close()

                except Exception as e:
                    print(f"Queue: Error tagging image {image.id}: {e}")
                    db3 = SessionLocal()
                    try:
                        q_item = db3.query(TagQueue).filter(
                            TagQueue.image_id == image.id, TagQueue.status == "processing"
                        ).first()
                        if q_item:
                            q_item.status = "error"
                            q_item.error_msg = str(e)[:200]
                        db3.commit()
                    finally:
                        db3.close()

        self._current_image_id = None
        if not self._stop_event.is_set():
            self._state = "idle"
            print("Queue: Worker stopped")


# Singleton instance
tagging_queue = TaggingQueue()
