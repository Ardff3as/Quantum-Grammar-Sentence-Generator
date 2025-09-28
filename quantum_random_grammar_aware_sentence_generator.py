import random
import requests
import time
import os

# === SETTINGS ===
CACHE_SIZE = 1024  # bytes fetched per QRNG request
RETRIES = 3
DELAY = 2
PUNCTUATION = [".", "!", "?"]  # possible sentence endings
CLUSTER_MIN = 4
CLUSTER_MAX = 20

# Paths to offline word lists
WORDLIST_FILES = {
    "nouns": "nouns.txt",
    "verbs": "verbs.txt",
    "adjectives": "adjectives.txt",
    "adverbs": "adverbs.txt"
}

# Global QRNG cache
qrng_cache = bytearray()

# === Fetch QRNG bytes ===
def fetch_qrng_bytes(n_bytes, retries=RETRIES, delay=DELAY):
    url = f"https://qrng.anu.edu.au/API/jsonI.php?length={n_bytes}&type=uint8"
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("success"):
                raise RuntimeError("Failed to fetch QRNG data")
            return bytes(data["data"])
        except (requests.exceptions.RequestException, RuntimeError) as e:
            print(f"⚠ Attempt {attempt} failed: {e}")
            if attempt < retries:
                print(f"⏳ Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("❌ Falling back to local random bytes.")
                return bytes([random.randint(0, 255) for _ in range(n_bytes)])

def fetch_qrng_bytes_cached(n_bytes):
    global qrng_cache
    while len(qrng_cache) < n_bytes:
        qrng_cache += fetch_qrng_bytes(CACHE_SIZE)
    result = qrng_cache[:n_bytes]
    qrng_cache = qrng_cache[n_bytes:]
    return result

# === Load offline word lists ===
def load_word_lists(files_dict):
    data = {}
    for key, filename in files_dict.items():
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Wordlist not found: {filename}")
        with open(filename, "r", encoding="utf-8") as f:
            words = [line.strip() for line in f if line.strip()]
            if not words:
                raise ValueError(f"{filename} is empty!")
            data[key] = words
    return data["nouns"], data["verbs"], data["adjectives"], data["adverbs"]

# === Grammar templates ===
TEMPLATES = [
    ["Determiner", "Adjective", "Noun", "Verb", "Adverb"],
    ["Noun", "Verb", "Determiner", "Noun"],
    ["Adjective", "Noun", "Verb"],
    ["Determiner", "Noun", "Verb", "Adverb"]
]

# === Optional mid-sentence commas ===
def insert_commas(sentence_words, rand_bytes_for_commas):
    result = []
    for i, word in enumerate(sentence_words):
        result.append(word)
        if i < len(sentence_words) - 1 and i < len(rand_bytes_for_commas):
            if rand_bytes_for_commas[i] % 2 == 0:
                result[-1] += ","
    return result

# === Sentence generation ===
def generate_sentence(nouns, verbs, adjectives, adverbs, templates=TEMPLATES):
    max_slots = max(len(t) for t in templates)
    rand_bytes = fetch_qrng_bytes_cached(max_slots + 10)  # extra for determiners, punctuation, commas, shuffling

    # Template choice via QRNG
    template_index = rand_bytes[0] % len(templates)
    template = templates[template_index]

    sentence = []
    for i, slot in enumerate(template):
        byte = rand_bytes[i+1]
        if slot == "Noun":
            sentence.append(nouns[byte % len(nouns)])
        elif slot == "Verb":
            sentence.append(verbs[byte % len(verbs)])
        elif slot == "Adjective":
            sentence.append(adjectives[byte % len(adjectives)])
        elif slot == "Adverb":
            sentence.append(adverbs[byte % len(adverbs)])
        elif slot == "Determiner":
            det_index = fetch_qrng_bytes_cached(1)[0] % 3
            sentence.append(["The", "A", "One"][det_index])

    # Optional shuffling of adjectives/adverbs
    adj_adv_indices = [i for i, s in enumerate(template) if s in {"Adjective", "Adverb"}]
    if len(adj_adv_indices) > 1:
        shuffle_bytes = fetch_qrng_bytes_cached(len(adj_adv_indices))
        shuffled = sorted(adj_adv_indices, key=lambda x: shuffle_bytes[x % len(shuffle_bytes)])
        sentence_adj_adv = [sentence[i] for i in shuffled]
        for idx, val in zip(shuffled, sentence_adj_adv):
            sentence[idx] = val

    # Mid-sentence commas via QRNG
    comma_bytes = fetch_qrng_bytes_cached(len(sentence))
    sentence = insert_commas(sentence, comma_bytes)

    # End punctuation via QRNG
    punct_byte = fetch_qrng_bytes_cached(1)[0]
    punctuation_mark = PUNCTUATION[punct_byte % len(PUNCTUATION)]

    return " ".join(sentence) + punctuation_mark

# === Main loop ===
def main():
    nouns, verbs, adjectives, adverbs = load_word_lists(WORDLIST_FILES)
    print(f"Loaded {len(nouns)} nouns, {len(verbs)} verbs, {len(adjectives)} adjectives, {len(adverbs)} adverbs.\n")
    print("Quantum-random grammar-aware sentence generator.")
    print("Type 'yes' to generate a cluster, 'q' to quit.\n")

    while True:
        user_input = input("Generate next cluster? (yes/q): ").strip().lower()
        if user_input in {"q", "quit"}:
            print("Goodbye! 👋")
            break
        elif user_input == "yes":
            # Quantum-random cluster size
            cluster_byte = fetch_qrng_bytes_cached(1)[0]
            num_sentences = CLUSTER_MIN + (cluster_byte % (CLUSTER_MAX - CLUSTER_MIN + 1))
            print(f"🎲 Cluster size decided by QRNG: {num_sentences} sentences\n")

            for _ in range(num_sentences):
                sentence = generate_sentence(nouns, verbs, adjectives, adverbs)
                print("🎲", sentence)
            print()
        else:
            print("Please type 'yes' to generate or 'q' to quit.")

if __name__ == "__main__":
    main()
