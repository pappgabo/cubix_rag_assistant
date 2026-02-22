# utils/prompt_utils.py
import json
from pathlib import Path
from typing import List, Dict, Any

def load_prompt_test(path: Path) -> List[Dict[str, Any]]:
    """
    Beolvassa a teszteseteket tartalmazó JSON fájlt és Python listává alakítja.
    """
    try:
        if not path.exists():
            print(f"⚠️ HIÁNYZÓ TESZT FÁJL: {path}")
            return []
            
        # 1. Beolvassuk a nyers szöveget
        raw_content = path.read_text(encoding="utf-8").strip()
        if not raw_content:
            return []
            
        # 2. Parszoljuk a JSON-t (ez teszi lehetővé a case["id"] hivatkozást)
        data = json.loads(raw_content)
        
        # 3. Biztonsági ellenőrzés: ha a JSON nem lista, hibát jelezünk
        if not isinstance(data, list):
            print(f"⚠️ HIBA: A {path} fájl nem listát tartalmaz!")
            return []
            
        return data
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON formátum hiba a fájlban ({path}): {e}")
        return []
    except Exception as e:
        print(f"❌ Váratlan hiba a tesztek betöltésekor: {e}")
        return []