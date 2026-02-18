import os
import imagehash
from PIL import Image
from sqlalchemy.orm import Session
from database import Image as DBImage, ImageHash, SessionLocal


def scan_file(file_path: str, db: Session):
    """Scan a single file, compute phash, deduplicate, generate thumbnail.
    Returns: newly created Image object, existing Image object, or None if error/skipped.
    """
    if not os.path.exists(file_path):
        return None
    
    # Skip if this path is already in the database
    existing = db.query(DBImage).filter(DBImage.path == file_path).first()
    if existing:
        if not existing.is_active:
            print(f"Reactivating image: {file_path}")
            existing.is_active = 1
            db.commit()
        return existing

    try:
        with Image.open(file_path) as img:
            # Compute perceptual hash
            phash_value = str(imagehash.phash(img))

            # Find or create the ImageHash entry
            hash_entry = db.query(ImageHash).filter(ImageHash.phash == phash_value).first()
            if not hash_entry:
                hash_entry = ImageHash(phash=phash_value)
                db.add(hash_entry)
                db.flush()  # Get the id

            # Create the image record linked to the hash
            file_name = os.path.basename(file_path)
            new_image = DBImage(path=file_path, filename=file_name, hash_id=hash_entry.id)
            db.add(new_image)
            db.commit()

            # Generate thumbnail
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            img.thumbnail((300, 300))
            thumb_path = f"thumbnails/{new_image.id}.jpg"
            os.makedirs("thumbnails", exist_ok=True)
            img.save(thumb_path, "JPEG")

            dup_count = db.query(DBImage).filter(DBImage.hash_id == hash_entry.id).count()
            if dup_count > 1:
                print(f"Duplicate found: {file_name} (hash {phash_value}, {dup_count} copies)")
            else:
                print(f"Scanned: {file_name} (hash {phash_value})")
            
            return new_image

    except Exception as e:
        print(f"Error scanning {file_path}: {e}")
        db.rollback()
        return None


def scan_folder(folder_path: str, db: Session):
    """Scan top-level folder using scan_file."""
    if not os.path.exists(folder_path):
        return

    # First, handle existing files
    for entry in os.scandir(folder_path):
        if not entry.is_file():
            continue
        if not entry.name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            continue
        
        scan_file(entry.path, db)

    # Then, check for deleted files in this folder
    # We query all images in DB that start with this folder path
    # SQLite LIKE is case-insensitive by default for ASCII characters only, 
    # but paths might be case-sensitive depending on OS. Windows is usually case-insensitive.
    # We'll stick to simple startswith check in Python for safety or just depend on path exact match for now.
    
    # Get all images that SHOULD be in this folder
    # This might be slow if there are millions of images, but for now it's fine.
    # Better approach might be to query DB for all images whose path starts with folder_path
    
    # Important: Ensure the folder path has a trailing slash for correct matching
    folder_path_slash = os.path.join(folder_path, "")
    
    # Query images in this folder
    images_in_db = db.query(DBImage).filter(DBImage.path.startswith(folder_path)).all()
    
    deleted_count = 0
    for img in images_in_db:
        # Check if file still exists
        if not os.path.exists(img.path):
             print(f"Scanner: Removing missing file from DB: {img.path}")
             db.delete(img)
             deleted_count += 1
    
    if deleted_count > 0:
        db.commit()
        print(f"Scanner: Removed {deleted_count} missing files from DB")
