from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class AgentManifest:
    id: str
    name: str
    team: str
    owners: list[str]
    model: str
    prompt: str
    tools: list[str] = field(default_factory=list)
    retrieval_sources: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    fallback_models: list[str] = field(default_factory=list)

    def validate(self) -> None:
        for f in ("id", "name", "team", "model", "prompt"):
            if not getattr(self, f):
                raise ValueError(f"manifest missing {f}")
        if not self.owners:
            raise ValueError("manifest needs at least one owner")

@dataclass
class Route:
    agent_id: str
    confidence: float
    reason: str
    scores: dict[str, float] = field(default_factory=dict)

@dataclass
class Answer:
    request_id: str
    agent_id: str
    text: str
    confidence: float
    citations: list[str]
    latency_ms: float
    escalated: bool = False
