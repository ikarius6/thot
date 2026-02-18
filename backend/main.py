from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
import uvicorn
import os
import math
from database import SessionLocal, Image, ImageHash, WatchedFolder, Settings, engine
from scanner import scan_folder
from ai import tag_image
from queue_worker import tagging_queue
from watcher import folder_watcher
import subprocess
import sys
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

@app.on_event("startup")
def startup_event():
    # Load watched folders and start watcher
    db = SessionLocal()
    try:
        folders = db.query(WatchedFolder).all()
        for f in folders:
            if os.path.exists(f.path):
                folder_watcher.add_folder(f.path)
        folder_watcher.start()
        
        # Also ensure the queue worker is running to process any incoming items
        tagging_queue.start_worker_thread()
    finally:
        db.close()

@app.on_event("shutdown")
def shutdown_event():
    folder_watcher.stop()
    tagging_queue.stop()

origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create thumbnails directory if not exists
os.makedirs("thumbnails", exist_ok=True)
app.mount("/thumbnails", StaticFiles(directory="thumbnails"), name="thumbnails")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _serialize_image(img: Image, db: Session) -> dict:
    """Convert an Image ORM object to a JSON-friendly dict with tags and duplicate count."""
    tags = None
    duplicate_count = 1
    if img.image_hash:
        tags = img.image_hash.tags
        duplicate_count = db.query(func.count(Image.id)).filter(Image.hash_id == img.hash_id).scalar()
    return {
        "id": img.id,
        "path": img.path,
        "filename": img.filename,
        "hash_id": img.hash_id,
        "tags": tags,
        "duplicate_count": duplicate_count,
        "created_at": img.created_at.isoformat() if img.created_at else None,
    }


@app.post("/scan")
def scan_images(folder_path: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=400, detail="Folder not found")
    # Auto-save as watched folder
    existing = db.query(WatchedFolder).filter(WatchedFolder.path == folder_path).first()
    if not existing:
        db.add(WatchedFolder(path=folder_path))
        db.commit()
    
    # Start watching immediately
    folder_watcher.add_folder(folder_path)
    
    background_tasks.add_task(scan_folder, folder_path, db)
    return {"message": "Scanning started and folder watched"}


@app.get("/folders")
def get_folders(db: Session = Depends(get_db)):
    folders = db.query(WatchedFolder).order_by(WatchedFolder.created_at).all()
    return [{"id": f.id, "path": f.path} for f in folders]


@app.delete("/folders/{folder_id}")
def remove_folder(folder_id: int, db: Session = Depends(get_db)):
    folder = db.query(WatchedFolder).filter(WatchedFolder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    folder_watcher.remove_folder(folder.path)
    
    # Soft delete all images in this folder
    # We need to find all images that start with this folder path
    folder_path = folder.path
    if not folder_path.endswith(os.sep):
        folder_path += os.sep
        
    # Valid for both Windows and Linux usually, but let's be careful with case on Windows if needed.
    # For now, standard startswith
    images = db.query(Image).filter(Image.path.startswith(folder_path)).all()
    for img in images:
        img.is_active = 0
    
    db.delete(folder)
    db.commit()
    return {"message": f"Folder stopped watching. {len(images)} images marked inactive."}


@app.post("/scan-all")
def scan_all_folders(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    folders = db.query(WatchedFolder).all()
    if not folders:
        raise HTTPException(status_code=400, detail="No watched folders")
    for f in folders:
        if os.path.exists(f.path):
            background_tasks.add_task(scan_folder, f.path, db)
    return {"message": f"Scanning {len(folders)} folder(s)"}


@app.get("/system/pick-folder")
def pick_folder():
    """Open a native OS folder picker dialog on the server machine."""
    try:
        # Run a small script to open the dialog
        cmd = [
            sys.executable, "-c",
            "import tkinter as tk; from tkinter import filedialog; root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True); print(filedialog.askdirectory())"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        path = res.stdout.strip()
        if not path:
            return {"path": ""}
        # Normalize path for Windows
        path = path.replace('/', '\\')
        return {"path": path}
    except Exception as e:
        print(f"Error picking folder: {e}")
        return {"path": ""}


@app.get("/images")
def get_images(page: int = 1, page_size: int = 50, filter: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Image).options(joinedload(Image.image_hash)).filter(Image.is_active == 1)

    if filter == 'untagged':
        query = query.outerjoin(ImageHash, Image.hash_id == ImageHash.id).filter(
            (Image.hash_id == None) | (ImageHash.tags == None) | (ImageHash.tags == '')
        )
    elif filter == 'tagged':
        query = query.join(ImageHash, Image.hash_id == ImageHash.id).filter(
            ImageHash.tags != None, ImageHash.tags != ''
        )

    total = query.count()
    images = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "images": [_serialize_image(img, db) for img in images],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@app.get("/search")
def search_images(q: str, page: int = 1, page_size: int = 50, db: Session = Depends(get_db)):
    query = db.query(Image).options(joinedload(Image.image_hash)).join(ImageHash, Image.hash_id == ImageHash.id).filter(Image.is_active == 1)
    
    if ':' in q:
        import re
        try:
            key, value = q.split(':', 1)
            # Regex to match "key:" followed by any characters except comma (to stay within one tag if tags are comma-separated)
            # then the value. Or just simple "key:.*value" 
            # Given tags are "series:harry potter, character:harry potter"
            # We want "character:potter" to match "character:harry potter"
            # Pattern: \bkey\s*:\s*.*value
            
            # Using a safer pattern that respects the tag structure (comma separated)
            # \bkey:[^,]*value
            regex_pattern = f"\\b{re.escape(key)}:[^,]*{re.escape(value)}"
            query = query.filter(ImageHash.tags.op('REGEXP')(regex_pattern))
        except Exception:
            # Fallback to normal contains if regex construction fails
            query = query.filter(ImageHash.tags.contains(q))
    else:
        query = query.filter(ImageHash.tags.contains(q))
    total = query.count()
    images = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "images": [_serialize_image(img, db) for img in images],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@app.get("/images/{image_id}/full")
def get_full_image(image_id: int, db: Session = Depends(get_db)):
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image or not os.path.exists(image.path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image.path)


@app.get("/images/{image_id}")
def get_single_image(image_id: int, db: Session = Depends(get_db)):
    image = db.query(Image).options(joinedload(Image.image_hash)).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    result = _serialize_image(image, db)
    # Include list of duplicate locations
    if image.hash_id:
        duplicates = db.query(Image.path).filter(Image.hash_id == image.hash_id, Image.id != image.id).all()
        result["duplicate_paths"] = [d.path for d in duplicates]
    else:
        result["duplicate_paths"] = []
    return result


@app.post("/tag/{image_id}")
def trigger_tagging(image_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    image = db.query(Image).options(joinedload(Image.image_hash)).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    def tag_and_save(img_id, img_path, hash_id):
        new_db = SessionLocal()
        try:
            tags = tag_image(img_path)
            # Write tags to the hash, not the image
            h = new_db.query(ImageHash).filter(ImageHash.id == hash_id).first()
            if h:
                h.tags = tags
                new_db.commit()
                dup_count = new_db.query(Image).filter(Image.hash_id == hash_id).count()
                print(f"Tagged hash for image {img_id} ({dup_count} copies): {tags[:100]}...")
            else:
                print(f"Hash not found for image {img_id}")
        except Exception as e:
            print(f"Error tagging image {img_id}: {e}")
            new_db.rollback()
        finally:
            new_db.close()

    background_tasks.add_task(tag_and_save, image.id, image.path, image.hash_id)
    return {"message": "Tagging started"}


@app.put("/images/{image_id}/tags")
def update_tags(image_id: int, tags: str, db: Session = Depends(get_db)):
    image = db.query(Image).options(joinedload(Image.image_hash)).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    if not image.image_hash:
        raise HTTPException(status_code=400, detail="Image has no hash entry")
    image.image_hash.tags = tags
    db.commit()
    return _serialize_image(image, db)


# ── Queue endpoints ─────────────────────────────────────────────

@app.post("/queue/start")
def queue_start():
    return tagging_queue.start()

@app.post("/queue/pause")
def queue_pause():
    return tagging_queue.pause()

@app.post("/queue/resume")
def queue_resume():
    return tagging_queue.resume()

@app.post("/queue/stop")
def queue_stop():
    return tagging_queue.stop()

@app.get("/queue/status")
def queue_status():
    return tagging_queue.get_status()


# ── Settings endpoints ──────────────────────────────────────────

@app.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    settings = db.query(Settings).all()
    return {s.key: s.value for s in settings}

@app.post("/settings")
def update_settings(settings: dict, db: Session = Depends(get_db)):
    for key, value in settings.items():
        setting = db.query(Settings).filter(Settings.key == key).first()
        if setting:
            setting.value = str(value)
        else:
            db.add(Settings(key=key, value=str(value)))
    db.commit()
    return {"message": "Settings updated"}


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
