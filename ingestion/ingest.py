import sys
from pathlib import Path
from ingestion.chunking import load_text_files

# ---------------------------------------------------------------------------
# A projekt gyökérkönyvtárának hozzáadása a sys.path-hoz
#
# A Python az importokat a futtatási könyvtárból próbálja feloldani.
# Ha a scriptet nem a projekt gyökeréből futtatod, akkor a config.py
# és más modulok nem lennének megtalálhatók.
#
# Ezért manuálisan hozzáadjuk a projekt gyökerét az import útvonalhoz.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Külső importok
# ---------------------------------------------------------------------------
import requests
from config import API_URL, DATA_DIR


# ---------------------------------------------------------------------------
# Szöveges fájlok beolvasása és dokumentumokká alakítása
#
# A data/ könyvtárból beolvassuk a .txt és .md fájlokat, majd
# egységes dokumentum-objektumokká alakítjuk őket.
# ---------------------------------------------------------------------------
def load_baseline_docs():
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

            if not text.strip():
                print(f"Üres fájl, kihagyom: {path.name}")
                continue

            slug = Path(path.name).stem  # pl. "aloo-matar"

            docs.append({
                "id": slug,
                "text": text,
                "metadata": {
                    "filename": path.name,
                    "slug": slug,
                    "source": "local_markdown" if path.suffix == ".md" else "local_txt",
                },
            })
            idx += 1

    return docs


# ---------------------------------------------------------------------------
# Főprogram: fájlok beolvasása és elküldése a Next.js API-nak
# ---------------------------------------------------------------------------
def main():
    print("Adatok betöltése a data/ mappából...")
    print("DATA_DIR:", DATA_DIR)

    # 1. Dokumentumok beolvasása
    docs = load_baseline_docs()
    print(f"Beolvasott érvényes dokumentumok száma: {len(docs)}")

    if not docs:
        print("Nincs mit küldeni, nincs érvényes .txt fájl.")
        return

    # -----------------------------------------------------------------------
    # 2. STRATÉGIA KIVÁLASZTÁSA
    #
    # A Next.js API a ?strategy= paraméter alapján dönti el,
    # hogy melyik PostgreSQL táblába indexeljen:
    #
    #   baseline  → documents_baseline
    #   chunked   → documents_chunked
    #
    # Ez lehetővé teszi, hogy külön pipeline-okat építs és tesztelj.
    # -----------------------------------------------------------------------
    target_strategy = "baseline"   # <-- átírható "chunked"-re is
    url_with_strategy = f"{API_URL}?strategy={target_strategy}"

    print(f"Küldés a(z) {target_strategy} táblába...")
    print("Cél URL:", url_with_strategy)

    # -----------------------------------------------------------------------
    # 3. Küldés a Next.js API-nak
    #
    # A dokumentumokat JSON formátumban küldjük el.
    # A szerver oldalon az API endpoint fogja feldolgozni és indexelni őket.
    # -----------------------------------------------------------------------
    try:
        response = requests.post(url_with_strategy, json=docs, timeout=30)
        print("Status code:", response.status_code)

        # Megpróbáljuk JSON-ként értelmezni a választ
        try:
            print("Response JSON:", response.json())
        except Exception:
            print("Nem sikerült JSON-ként értelmezni a választ:", response.text)

    except Exception as e:
        # Ha a POST kérés közben hiba történik (pl. nincs kapcsolat)
        print("Hiba történt a kérés közben:", e)


# ---------------------------------------------------------------------------
# Belépési pont
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
