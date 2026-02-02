import requests
from scripts.chunking import load_text_files, make_chunks # Az import marad!
from config import API_URL

def main():
    print("--- INGEST FOLYAMAT INDÍTÁSA ---")
    
    # 1. Meghívjuk a logikát a másik fájlból
    docs = load_text_files()
    
    # 2. Itt használjuk a base_id-s chunkolót
    chunks = make_chunks(docs, max_len=500, overlap_tokens=50)
    
    # 3. Beküldés az API-nak
    target_strategy = "chunked"
    url = f"{API_URL}?strategy={target_strategy}"
    
    response = requests.post(url, json=chunks, timeout=30)
    print(f"Szerver válasza: {response.status_code}")

if __name__ == "__main__":
    main()