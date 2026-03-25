import ollama
import json
import re
import os
import tempfile
from PIL import Image as PILImage
from database import SessionLocal, Settings

# Ollama client with timeout to prevent infinite hangs
_ollama_client = ollama.Client(timeout=300.0)  # 5 minute timeout

def get_model_name() -> str:
    db = SessionLocal()
    try:
        setting = db.query(Settings).filter(Settings.key == "llm_model").first()
        if setting and setting.value:
            return setting.value
        return "huihui_ai/qwen3-vl-abliterated:8b"
    except Exception as e:
        print(f"Error fetching model name: {e}")
        return "huihui_ai/qwen3-vl-abliterated:8b"
    finally:
        db.close()


def _ensure_compatible_image(image_path: str) -> str:
    """If the image is WebP (or other unsupported format), convert to JPEG temp file.
    Returns the path to use for Ollama (either original or temp file)."""
    if image_path.lower().endswith('.webp'):
        try:
            with PILImage.open(image_path) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                tmp = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
                img.save(tmp.name, 'JPEG', quality=90)
                return tmp.name
        except Exception as e:
            print(f"Warning: Could not convert {image_path}: {e}")
    return image_path

# Qwen3-VL is much better at vision tasks and following instructions than moondream
MODEL = "huihui_ai/qwen3-vl-abliterated:8b"

#TAGGING_PROMPT2 = """Describe this image comprehensively in JSON format:
#
#{
#  "description": "detailed description here",
#  "tags": ["tag1", "tag2", "tag3", ...],
#  "colors": ["color1", "color2", ...],
#  "objects": ["object1", "object2", ...],
#  "scene_type": "type of scene",
#  "mood": "emotional qualities",
#  "style": "visual style",
#  "content_rating": "safe/suggestive/adult/explicit/violent",
#  "content_flags": []
#}
#
#Be detailed and specific. Include as many relevant tags and objects as you can identify."""

TAGGING_PROMPT = """Analyze this image in detail and return a comprehensive JSON description.

Output format (JSON only, no markdown, no conversational text):
{
  "visual_summary": "A brief 1-2 sentence overview of the image",
  "type": "photo",
  "subject": "detailed description of main subject",
  "characters": ["character1", "character2"],
  "setting": "description of environment and context",
  "mood": "emotional tone and atmosphere",
  "colors": ["color1", "color2", "color3", "color4"],
  "style": "visual/artistic style description",
  "composition": "framing, perspective, and technical aspects",
  "elements": ["element1", "element2", "element3", "element4", "element5"],
  "lighting": "description of lighting conditions",
  "quality_notes": "image quality, resolution, notable technical aspects",
  "content_rating": "safe",
  "content_flags": []
}

Rules:
1. Return ONLY valid JSON. Do not write "Here is the JSON" or any other text outside the {}.
2. Escape all double quotes inside strings (e.g., "The sign says \"Hello\"").
3. Do not use markdown code blocks.
4. If a list is empty, return [].
5. Ensure all keys are present.

Field descriptions:
- visual_summary: 1-2 sentences describing the overall scene
- type: Image category (photo, illustration, digital_art, screenshot, 3d_render, painting, sketch, anime, etc.)
- subject: Main focus of the image, be specific and detailed
- characters: ONLY include names of famous, well-known, or fictional characters you can positively identify.
- setting: Where/what environment
- mood: Emotional qualities
- colors: List of 3-6 prominent colors
- style: Artistic or photographic style
- composition: Technical aspects
- elements: Array of 5-10 specific visible objects
- lighting: Light sources, quality
- quality_notes: Resolution, artifacts
- content_rating: safe | suggestive | adult | explicit | violent
- content_flags: [nudity, sexual, violence, gore, weapons, etc] or []
"""


def tag_image(image_path: str) -> str:
    """Tag an image with structured, categorized tags for granular search."""
    compatible_path = _ensure_compatible_image(image_path)
    try:
        model_name = get_model_name()
        print(f"Tagging with model: {model_name}")
        res = _ollama_client.chat(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise image analysis system. Return only valid JSON. Do not include any text before or after the JSON object."
                },
                {
                    'role': 'user',
                    'content': TAGGING_PROMPT,
                    'images': [compatible_path]
                }
            ],
            options={
                'temperature': 0.3  # Lower temperature for more deterministic/strict output
            }
        )
        print(res)

        raw = res['message']['content'].strip()
        tags = _parse_tags(raw)
        return tags

    except Exception as e:
        print(f"Error tagging {image_path}: {e}")
        raise
    finally:
        # Clean up temp file if we created one
        if compatible_path != image_path:
            try:
                os.unlink(compatible_path)
            except OSError:
                pass


def _parse_tags(raw: str) -> str:
    """Parse the AI response into a flat, searchable comma-separated tag string.
    Relying on a robust "Repair & Extract" strategy to handle malformed JSON.
    """
    # 1. Try strict JSON first (fast path)
    try:
        # Attempt to find the first JSON-like block
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            data = json.loads(json_match.group())
            return _process_data_to_tags(data)
    except (json.JSONDecodeError, AttributeError):
        pass

    # 2. Targeted Regex extraction (slow path for broken output)
    known_keys = [
        'visual_summary', 'type', 'subject', 'characters', 'setting', 'mood', 
        'colors', 'style', 'composition', 'elements', 'lighting', 'quality_notes', 
        'content_rating', 'content_flags'
    ]
    
    data = {}
    
    for key in known_keys:
        # Find "key": ...
        pattern = fr'"{key}"\s*:\s*'
        match = re.search(pattern, raw)
        if not match:
            continue

        start_index = match.end()
        
        # Find the start of the next key to delimit the value chunk
        next_indices = []
        for other_key in known_keys:
            if other_key == key: continue
            # Look for "other_key":
            try:
                nm = re.search(fr'"{other_key}"\s*:', raw[start_index:])
                if nm:
                    next_indices.append(start_index + nm.start())
            except re.error:
                pass
        
        end_index = min(next_indices) if next_indices else len(raw)
        value_chunk = raw[start_index:end_index].strip()
        
        # Parse the value chunk
        if value_chunk.startswith('['):
            # List handling
            # Try to extract quoted strings first: "item1", "item2"
            items = re.findall(r'"([^"]*)"', value_chunk)
            
            # If no items found (e.g., unclosed quotes or garbage), fallback to comma split
            if not items:
                clean_chunk = value_chunk.strip('[]')
                # Split by comma and clean up
                potential_items = clean_chunk.split(',')
                items = [p.strip().strip('"').strip() for p in potential_items if p.strip()]
            
            data[key] = items

        elif value_chunk.startswith('"'):
            # String handling
            # Try to capture valid string content
            m_str = re.search(r'"([^"]*)"', value_chunk)
            if m_str:
                data[key] = m_str.group(1)
            else:
                # Fallback: take everything until newline or end, strip quotes
                data[key] = value_chunk.strip('"')
        else:
             # Raw value (numbers, booleans, or unquoted text)
             data[key] = value_chunk

    if data:
        return _process_data_to_tags(data)

    # 3. Last resort fallback
    return _clean_fallback(raw)


def _process_data_to_tags(data: dict) -> str:
    """Convert valid dict to tag string."""
    tags = []
    
    single_fields = ['type', 'subject', 'setting', 'mood', 'style', 'composition', 'lighting', 'visual_summary', 'quality_notes', 'content_rating']
    
    for key in single_fields:
        val = data.get(key, '')
        if val and isinstance(val, str) and val.lower() not in ['none', 'n/a']:
             val = val.split(',')[0].strip()
             val = val.replace('\n', ' ') # Ensure no newlines
             if key == 'visual_summary': 
                 tags.append(f"summary:{val[:120]}") 
             else:
                 tags.append(f"{key}:{val}")

    list_fields = ['colors', 'characters', 'elements', 'content_flags']
    for key in list_fields:
        val = data.get(key, [])
        
        # Normalize to list if string
        if isinstance(val, str):
            val = [val]
            
        for item in val:
            if not isinstance(item, str): continue
            
            # Clean item
            item = item.strip().strip('"')
            item = item.replace('\n', ' ')
            
            if item and len(item) < 80:
                 # Singularize list keys
                 tag_key = key[:-1] 
                 tags.append(f"{tag_key}:{item}")
                 
    return ', '.join(tags)


def _clean_fallback(raw: str) -> str:
    """If JSON parsing fails completely, clean up the raw response into simple tags."""
    # Remove markdown formatting, extra whitespace
    cleaned = re.sub(r'[*#`\[\]{}]', '', raw)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    # Split on common delimiters and rejoin
    parts = re.split(r'[,\n;|]', cleaned)
    tags = [p.strip().lower() for p in parts if p.strip() and len(p.strip()) < 40]
    return ', '.join(tags[:15])  # Cap at 15 tags
