from __future__ import annotations
import time, uuid
from .gateway import Gateway
from .memory import InMemoryStore
from .models import Answer
from .router import Router, ESCALATION
from .tracing import Tracer

class Platform:
    def __init__(self, registry, store=None, gateway=None, tracer=None):
        self.registry = registry
        self.router = Router(registry)
        self.store = store or InMemoryStore()
        self.gateway = gateway or Gateway()
        self.tracer = tracer or Tracer()

    def handle(self, text: str, conv_id: str = "default") -> Answer:
        t0, trace = time.time(), Tracer.new_trace()
        rid = uuid.uuid4().hex[:12]
        s = self.tracer.span("route", trace, request=text[:120])
        route = self.router.route(text); self.tracer.end(s, agent=route.agent_id, confidence=route.confidence)
        agent = self.registry.get(route.agent_id)
        s = self.tracer.span("retrieve", trace, agent=agent.id)
        docs = self.store.search(text, agent.retrieval_sources)
        self.store.recall(conv_id, text)
        self.tracer.end(s, hits=len(docs))
        s = self.tracer.span("generate", trace, agent=agent.id, model=agent.model)
        ctx = [d["text"] for d in docs]
        out = self.gateway.generate(agent, f"{agent.prompt}\nClient request: {text}", ctx) \
            if route.agent_id != ESCALATION else "Escalated to a human specialist for review."
        self.tracer.end(s)
        self.store.add_turn(conv_id, "user", text); self.store.add_turn(conv_id, "assistant", out)
        return Answer(rid, agent.id, out, route.confidence, [d["id"] for d in docs],
                      round((time.time() - t0) * 1000, 3), escalated=route.agent_id == ESCALATION)
