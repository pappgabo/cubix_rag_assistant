# scripts/debug_run.py
from scripts.ingest import load_text_files  # Feltételezve, hogy az ingest-ben van a betöltő
from scripts.chunking import make_chunks
from collections import Counter

def debug_chunking():
    # 1. Dokumentumok betöltése
    docs = load_text_files()
    print(f"--- Diagnosztika ---")
    print(f"Betöltött dokumentumok száma: {len(docs)}")

    if not docs:
        print("Hiba: Nem sikerült dokumentumokat betölteni. Ellenőrizd az elérési utat!")
        return

    # 2. Chunkolás futtatása
    # Figyelj a paraméternevekre: max_len és overlap
    chunks = make_chunks(docs, max_len=500, overlap_tokens=50)
    print(f"Létrehozott chunkok száma: {len(chunks)}")

    if not chunks:
        print("Hiba: Nem jöttek létre chunkok!")
        return

    # 3. Statisztika készítése doksinként
    # A chunk-ban a metaadatok között keressük a base_id-t
    try:
        per_doc = Counter(c["metadata"]["base_id"] for c in chunks)
        
        print("\n--- Chunk eloszlás (Top 20 dokumentum) ---")
        print("Base_ID: Chunk szám")
        for doc_id, count in per_doc.most_common(20):
            print(f"ID {doc_id}: {count} db")

        print("-" * 30)
        print(f"Minimum chunk/doksi: {min(per_doc.values())}")
        print(f"Maximum chunk/doksi: {max(per_doc.values())}")
        print(f"Átlagos chunk/doksi: {len(chunks)/len(per_doc):.2f}")
        
    except KeyError:
        print("\nHiba: A chunkok metaadataiban nem található 'base_id'.")
        print("Ellenőrizd a make_chunks függvényben, hogy mi az ID kulcsa (lehet, hogy 'doc_id'?)")

if __name__ == "__main__":
    debug_chunking()