import json
from pathlib import Path
from typing import List, Dict, Any

def load_prompt_file(path: Path) -> str:
    """
    Nyers szöveges prompt beolvasása (system_prompt, user_prompt).
    """
    try:
        if not path.exists():
            print(f"⚠️ HIÁNYZÓ PROMPT FÁJL: {path}")
            return ""
        
        # Beolvassuk a teljes tartalmat stringként
        content = path.read_text(encoding="utf-8").strip()
        return content
    except Exception as e:
        print(f"❌ Hiba a prompt fájl beolvasásakor ({path.name}): {e}")
        return ""

def load_prompt_tests(path: Path) -> List[Dict[str, Any]]:
    """
    Tesztesetek (JSON) beolvasása és parszolása.
    Ez oldja meg, hogy ne string-indexelési hibát kapj!
    """
    try:
        if not path.exists():
            print(f"⚠️ HIÁNYZÓ TESZT FÁJL: {path}")
            return []
            
        raw_data = path.read_text(encoding="utf-8").strip()
        if not raw_data:
            return []
            
        # Itt történik a varázslat: a szövegből Python lista lesz
        data = json.loads(raw_data)
        
        if isinstance(data, list):
            return data
        else:
            print(f"⚠️ A {path.name} tartalma nem lista, hanem {type(data)}")
            return []
    except json.JSONDecodeError as e:
        print(f"❌ JSON formátum hiba a {path.name} fájlban: {e}")
        return []
    except Exception as e:
        print(f"❌ Váratlan hiba a tesztek betöltésekor: {e}")
        return []