"""YAML-subset parser (flat keys, scalar lists, inline lists) + registry.

ponytail: stdlib-only subset parser, not full YAML. Manifests stay flat by
design; switch to PyYAML if nested manifests are ever needed.
"""
from __future__ import annotations
import glob, os
from .models import AgentManifest

def _scalar(v: str):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        return [x.strip().strip("'\"") for x in v[1:-1].split(",") if x.strip()]
    return v.strip("'\"")

def parse_manifest(text: str) -> AgentManifest:
    data: dict = {}
    key = None
    for raw in text.splitlines():
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        if raw.startswith((" ", "\t")) and raw.strip().startswith("- ") and key:
            data.setdefault(key, []).append(_scalar(raw.strip()[2:]))
        elif ":" in raw:
            key, _, val = raw.partition(":")
            key = key.strip()
            data[key] = _scalar(val) if val.strip() else []
    m = AgentManifest(
        id=data["id"], name=data.get("name", ""), team=data.get("team", ""),
        owners=data.get("owners", []), model=data.get("model", ""), prompt=data.get("prompt", ""),
        tools=data.get("tools", []), retrieval_sources=data.get("retrieval_sources", []),
        keywords=data.get("keywords", []), examples=data.get("examples", []),
        fallback_models=data.get("fallback_models", []))
    m.validate()
    return m

class Registry:
    def __init__(self): self._agents: dict[str, AgentManifest] = {}
    def register(self, m: AgentManifest) -> AgentManifest:
        m.validate(); self._agents[m.id] = m; return m
    def onboard(self, path: str) -> AgentManifest:
        with open(path) as f: return self.register(parse_manifest(f.read()))
    def load_dir(self, directory: str) -> list[AgentManifest]:
        return [self.onboard(p) for p in sorted(glob.glob(os.path.join(directory, "*.yaml")))]
    def get(self, agent_id: str) -> AgentManifest: return self._agents[agent_id]
    def all(self) -> list[AgentManifest]: return list(self._agents.values())
    def __len__(self): return len(self._agents)
