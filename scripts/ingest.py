import sys
from pathlib import Path

# --- Projekt gyökérkönyvtárának hozzáadása a sys.path-hoz --------------------
# Ennek az az oka, hogy a Python futtatáskor nem mindig a projekt gyökerét
# tekinti importálási alapnak, ezért a config.py nem lenne megtalálható.
# A __file__ a jelenlegi fájl helye, innen lépünk kettőt vissza a gyökérig.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Ha a projekt gyökere még nincs a sys.path-ban, hozzáadjuk.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# --- Külső importok ----------------------------------------------------------
import requests
from config import API_URL, DATA_DIR


# --- Szöveges fájlok beolvasása és dokumentumokká alakítása ------------------
def load_text_files():
    docs = []   # Ide gyűjtjük a dokumentumokat
    idx = 1     # Automatikus ID számláló

    # Csak .txt és .md fájlokat keresünk
    patterns = ["*.txt", "*.md"]

    for pattern in patterns:
        # A DATA_DIR-ben megkeressük a mintára illeszkedő fájlokat
        for path in sorted(DATA_DIR.glob(pattern)):
            try:
                # Fájl beolvasása UTF-8 kódolással
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                # Ha nem sikerül beolvasni (pl. rossz kódolás), jelezzük és kihagyjuk
                print(f"Nem sikerült beolvasni (kódolás hiba): {path}")
                continue

            # Üres fájlok kihagyása
            if not text.strip():
                print(f"Üres fájl, kihagyom: {path.name}")
                continue

            # Dokumentum objektum összeállítása
            docs.append(
                {
                    "id": idx,          # Egyedi ID
                    "text": text,       # A fájl tartalma
                    "metadata": {       # Metaadatok a későbbi kereséshez
                        "filename": path.name,
                        "source": "local_markdown" if path.suffix == ".md" else "local_txt",
                    },
                }
            )
            idx += 1  # Következő ID

    return docs


# --- Főprogram: fájlok beolvasása és elküldése az API-nak --------------------
def main():
    print("Adatok betöltése a data/ mappából...")
    print("DATA_DIR:", DATA_DIR)

    # Dokumentumok beolvasása
    docs = load_text_files()
    print(f"Beolvasott érvényes dokumentumok száma: {len(docs)}")

    # Ha nincs érvényes dokumentum, nincs mit küldeni
    if not docs:
        print("Nincs mit küldeni, nincs érvényes .txt fájl.")
        return

    # API hívás POST-tal
    try:
        response = requests.post(API_URL, json=docs, timeout=30)
        print("Status code:", response.status_code)

        # Megpróbáljuk JSON-ként értelmezni a választ
        try:
            print("Response JSON:", response.json())
        except Exception:
            print(
                "Nem sikerült JSON-ként értelmezni a választ:",
                response.text
            )

    except Exception as e:
        # Ha a POST kérés közben hiba történik (pl. nincs kapcsolat)
        print("Hiba történt a kérés közben:", e)


# --- Belépési pont -----------------------------------------------------------
if __name__ == "__main__":
    main()
