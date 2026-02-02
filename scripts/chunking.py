from pathlib import Path
import re
from typing import List, Dict, Any
from config import DATA_DIR

def load_text_files() -> List[Dict[str, Any]]:
    """
    Betölti a DATA_DIR könyvtárban található .txt és .md fájlokat.
    Minden fájlt egy strukturált dict-ként ad vissza:
        - id: növekvő azonosító
        - text: a fájl teljes tartalma
        - metadata: fájlnév + forrás típusa
    Üres vagy hibás kódolású fájlokat kihagy.
    """
    docs = []
    idx = 1
    patterns = ["*.txt", "*.md"]

    for pattern in patterns:
        for path in sorted(DATA_DIR.glob(pattern)):
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                print(f"Nem sikerült beolvasni (kódolás hiba): {path}")
                continue

            # Üres fájlok kihagyása
            if not text.strip():
                print(f"Üres fájl, kihagyom: {path.name}")
                continue

            # Dokumentum hozzáadása
            docs.append(
                {
                    "id": idx,
                    "text": text,
                    "metadata": {
                        "filename": path.name,
                        "source": "local_markdown" if path.suffix == ".md" else "local_txt",
                    },
                }
            )
            idx += 1

    return docs

#Finomított overlap logika
def make_chunks(
    docs: List[Dict[str, Any]],
    max_len: int = 500,
    overlap_tokens: int = 50,
) -> List[Dict[str, Any]]:
    """
    Chunkolás mondatok alapján, opcionális overlap-pel.
    Minden chunk kap egy base_id mezőt, amit a RAG eval használ.
    """
    chunks: List[Dict[str, Any]] = []

    for doc in docs:
        text = doc["text"]

        # Az eredeti dokumentum ID-je → RAG eval ezt használja
        original_id = str(doc.get("id", ""))

        # Mondatokra bontás
        sentences = re.split(r"(?<=[.!?])\s+", text)

        current_chunk: List[str] = []
        current_len = 0

        for sentence in sentences:
            sentence_words = sentence.split()
            sentence_len = len(sentence_words)

            # Ha egy mondat túl hosszú → levágjuk
            if sentence_len > max_len:
                sentence = " ".join(sentence_words[:max_len])
                sentence_len = max_len

            # Ha belefér a chunkba → hozzáadjuk
            if current_len + sentence_len <= max_len:
                current_chunk.append(sentence)
                current_len += sentence_len

            else:
                # Chunk lezárása
                if current_chunk:
                    new_metadata = doc["metadata"].copy()
                    new_metadata["base_id"] = original_id

                    chunks.append({
                        "text": " ".join(current_chunk).strip(),
                        "metadata": new_metadata,
                    })

                # Overlap logika
                last_sentence = current_chunk[-1] if current_chunk else None
                if last_sentence and overlap_tokens > 0:
                    current_chunk = [last_sentence, sentence]
                else:
                    current_chunk = [sentence]

                current_len = sum(len(s.split()) for s in current_chunk)

        # Utolsó chunk mentése
        if current_chunk:
            final_text = " ".join(current_chunk).strip()
            if not chunks or chunks[-1]["text"] != final_text:
                new_metadata = doc["metadata"].copy()
                new_metadata["base_id"] = original_id

                chunks.append({
                    "text": final_text,
                    "metadata": new_metadata,
                })

    return chunks
