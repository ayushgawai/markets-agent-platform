"""Memory + retrieval. In-memory is the test/default backend; Postgres
(pgvector) and OpenSearch are adapters with the same two-method surface.
"""
from __future__ import annotations
import json, urllib.request
from .embeddings import embed, cosine

class InMemoryStore:
    """Conversation + long-term memory and document retrieval, one class."""
    def __init__(self): self._docs: list[dict] = []; self._turns: list[dict] = []
    def add_doc(self, doc_id: str, source: str, text: str):
        self._docs.append({"id": doc_id, "source": source, "text": text, "vec": embed(text)})
    def search(self, query: str, sources: list[str] | None = None, k: int = 3) -> list[dict]:
        q = embed(query)
        pool = [d for d in self._docs if not sources or d["source"] in sources]
        return sorted(pool, key=lambda d: -cosine(q, d["vec"]))[:k]
    def add_turn(self, conv_id: str, role: str, text: str):
        self._turns.append({"conv": conv_id, "role": role, "text": text, "vec": embed(text)})
    def recall(self, conv_id: str, query: str, k: int = 3) -> list[dict]:
        q = embed(query)
        pool = [t for t in self._turns if t["conv"] == conv_id]
        return sorted(pool, key=lambda t: -cosine(q, t["vec"]))[:k]

class PostgresMemory:
    """pgvector backend (needs psycopg; not exercised in unit tests).

    Schema: docs(id, source, text, embedding vector(128)),
            turns(conv, role, text, embedding vector(128)).
    """
    def __init__(self, dsn: str):
        import psycopg  # optional dependency, imported lazily
        self.conn = psycopg.connect(dsn)
    def search(self, query: str, sources=None, k: int = 3):
        with self.conn.cursor() as c:
            c.execute("SELECT id, source, text FROM docs WHERE (%s IS NULL OR source = ANY(%s)) "
                      "ORDER BY embedding <=> %s::vector LIMIT %s",
                      (sources, sources, embed(query), k))
            return [{"id": r[0], "source": r[1], "text": r[2]} for r in c.fetchall()]
    def add_turn(self, conv_id, role, text):
        with self.conn.cursor() as c:
            c.execute("INSERT INTO turns VALUES (%s,%s,%s,%s::vector)", (conv_id, role, text, embed(text)))
        self.conn.commit()
    def recall(self, conv_id, query, k: int = 3):
        with self.conn.cursor() as c:
            c.execute("SELECT role, text FROM turns WHERE conv=%s ORDER BY embedding <=> %s::vector LIMIT %s",
                      (conv_id, embed(query), k))
            return [{"role": r[0], "text": r[1]} for r in c.fetchall()]

class OpenSearchRetrieval:
    """OpenSearch-compatible kNN search over HTTP (no client lib needed)."""
    def __init__(self, base: str = "http://localhost:9200", index: str = "map-docs"):
        self.base, self.index = base, index
    def search(self, query: str, sources=None, k: int = 3):
        body = {"size": k, "query": {"knn": {"embedding": {"vector": embed(query), "k": k}}}}
        if sources:
            body["query"] = {"bool": {"must": body["query"], "filter": {"terms": {"source": sources}}}}
        req = urllib.request.Request(f"{self.base}/{self.index}/_search",
            data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            hits = json.load(r)["hits"]["hits"]
        return [{"id": h["_id"], "source": h["_source"].get("source", ""), "text": h["_source"]["text"]} for h in hits]
