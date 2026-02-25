import sys
from pathlib import Path
import requests
from config import API_URL, DATA_DIR

# Ensure project root is importable when running the script from outside the repo root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_baseline_docs():
    """
    Load all .txt and .md files from data/ and convert them into
    a unified document structure for ingestion.
    """
    docs = []
    patterns = ["*.txt", "*.md"]

    for pattern in patterns:
        for path in sorted(DATA_DIR.glob(pattern)):
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                print(f"Kódolási hiba miatt kihagyva: {path}")
                continue

            if not text.strip():
                print(f"Üres fájl kihagyva: {path.name}")
                continue

            slug = path.stem

            docs.append({
                "id": slug,
                "text": text,
                "metadata": {
                    "filename": path.name,
                    "slug": slug,
                    "source": "local_markdown" if path.suffix == ".md" else "local_txt",
                },
            })

    return docs


def main():
    print("Dokumentumok betöltése a data/ könyvtárból…")
    print("DATA_DIR:", DATA_DIR)

    docs = load_baseline_docs()
    print(f"Beolvasott dokumentumok: {len(docs)}")

    if not docs:
        print("Nincs érvényes dokumentum a küldéshez.")
        return

    # Choose which ingestion strategy the Next.js API should use
    target_strategy = "baseline"  # váltható: "chunked"
    url_with_strategy = f"{API_URL}?strategy={target_strategy}"

    print(f"Küldés a(z) {target_strategy} indexbe…")
    print("Cél URL:", url_with_strategy)

    # Send documents to the Next.js ingestion endpoint
    try:
        response = requests.post(url_with_strategy, json=docs, timeout=30)
        print("Status code:", response.status_code)

        try:
            print("Response JSON:", response.json())
        except Exception:
            print("Nem JSON válasz:", response.text)

    except Exception as e:
        print("Hiba történt a POST kérés során:", e)


if __name__ == "__main__":
    main()
