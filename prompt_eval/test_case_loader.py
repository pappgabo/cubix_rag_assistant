from pathlib import Path
from typing import List, Dict, Any
import json

def load_prompt_tests(path: Path) -> List[Dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))
