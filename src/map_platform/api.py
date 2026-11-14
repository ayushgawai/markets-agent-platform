"""FastAPI service. FastAPI is optional; falls back to stdlib http.server so
`python -m map_platform.api` runs anywhere. Both expose the same routes:
POST /ask {text} , GET /agents , GET /metrics (last eval if MAP_EVAL set).
"""
from __future__ import annotations
import json, os
from .cli import build

plat = build(traces=os.environ.get("MAP_TRACES", "traces/spans.jsonl"))
UI = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "index.html")

try:
    from fastapi import FastAPI
    from pydantic import BaseModel
    app = FastAPI(title="markets-agent-platform")
    class Ask(BaseModel): text: str
    @app.get("/agents")
    def agents(): return [{"id": a.id, "name": a.name, "team": a.team} for a in plat.registry.all()]
    @app.post("/ask")
    def ask(a: Ask):
        r = plat.handle(a.text); return {"agent": r.agent_id, "answer": r.text, "confidence": r.confidence, "citations": r.citations, "latency_ms": r.latency_ms, "escalated": r.escalated}
    @app.get("/")
    def index():
        from fastapi.responses import HTMLResponse
        return HTMLResponse(open(UI).read())
except ImportError:  # stdlib fallback
    app = None
    from http.server import BaseHTTPRequestHandler, HTTPServer
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            body = open(UI, "rb").read() if self.path == "/" else json.dumps(
                [{"id": a.id, "name": a.name, "team": a.team} for a in plat.registry.all()]).encode()
            self.send_response(200); self.send_header("Content-Type", "text/html" if self.path == "/" else "application/json"); self.end_headers(); self.wfile.write(body)
        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0)); text = json.loads(self.rfile.read(n) or b"{}").get("text", "")
            r = plat.handle(text); body = json.dumps({"agent": r.agent_id, "answer": r.text, "confidence": r.confidence, "citations": r.citations}).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(body)
        def log_message(self, *a): pass
    def run(): HTTPServer(("0.0.0.0", 8000), H).serve_forever()
else:
    def run():
        import uvicorn; uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__": run()
