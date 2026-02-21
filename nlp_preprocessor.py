import re

FILLERS = {
    "actually", "by", "the", "way", "please", "can", "you", "tell", "me", "something",
    "i", "want", "to", "know", "about"
}

def preprocess_query(q: str) -> str:
    q = q.lower()
    q = re.sub(r"[^\w\s><=]", " ", q)
    q = re.sub(r"\s+", " ", q)

    words = q.split()
    words = [w for w in words if w not in FILLERS and len(w) > 2]

    return " ".join(words)
