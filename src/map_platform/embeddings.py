from __future__ import annotations
import hashlib, math, re
TOK = re.compile(r"[a-z0-9]+")
def tokens(text: str) -> list[str]:
    return TOK.findall(text.lower())
def embed(text: str, dim: int = 128) -> list[float]:
    v = [0.0] * dim
    for t in tokens(text):
        h = int(hashlib.md5(t.encode()).hexdigest(), 16)
        v[h % dim] += 1.0
        v[(h >> 7) % dim] += 0.5  # second hash spreads collisions a little
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]
def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
