# utils/prompt_utils.py
from pathlib import Path

def load_file(path: Path) -> str:
    """
    Beolvas egy nyers szöveges promptot a megadott útvonalról.
    """
    try:
        if not path.exists():
            print(f"⚠️ HIÁNYZÓ FÁJL: {path}")
            return ""
        # A Path.read_text kényelmes, mert automatikusan kezeli a fájl megnyitását/zárását
        return path.read_text(encoding="utf-8").strip()
    except Exception as e:
        print(f"⚠️ Hiba a prompt betöltésekor ({path}): {e}")
        return ""
    

