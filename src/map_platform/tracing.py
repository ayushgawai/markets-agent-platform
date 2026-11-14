"""OpenTelemetry-style spans written as JSON lines (no OTel SDK needed)."""
from __future__ import annotations
import json, os, time, uuid

class Tracer:
    def __init__(self, path: str | None = None):
        self.path, self.spans = path, []
    def span(self, name: str, trace_id: str, **attrs):
        s = {"trace_id": trace_id, "span_id": uuid.uuid4().hex[:16], "name": name,
             "start": time.time(), "attrs": attrs}
        self.spans.append(s)
        return s
    def end(self, s: dict, **attrs):
        s["duration_ms"] = round((time.time() - s["start"]) * 1000, 3)
        s["attrs"].update(attrs)
        if self.path:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with open(self.path, "a") as f: f.write(json.dumps(s) + "\n")
    @staticmethod
    def new_trace() -> str: return uuid.uuid4().hex
