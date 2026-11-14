from __future__ import annotations
from .embeddings import embed, cosine, tokens
from .models import Route
from .registry import Registry

ESCALATION = "escalation"

class Router:
    def __init__(self, registry: Registry, threshold: float = 0.12):
        self.registry, self.threshold = registry, threshold
        self._centroids = {}
        for a in registry.all():
            vecs = [embed(e) for e in a.examples] or [embed(a.name + " " + a.prompt)]
            self._centroids[a.id] = [sum(v[i] for v in vecs) / len(vecs) for i in range(len(vecs[0]))]

    def route(self, text: str) -> Route:
        q, qtok = embed(text), set(tokens(text))
        scores = {}
        for a in self.registry.all():
            s = cosine(q, self._centroids[a.id])
            hits = sum(1 for k in a.keywords if k.lower() in qtok or k.lower() in text.lower())
            scores[a.id] = s + 0.08 * hits  # rules boost embedding similarity
        ranked = sorted(scores.items(), key=lambda kv: -kv[1])
        best, conf = ranked[0]
        if conf < self.threshold:
            return Route(ESCALATION, conf, f"below threshold {self.threshold:.2f}; human escalation", scores)
        return Route(best, conf, "embedding+rules", scores)
