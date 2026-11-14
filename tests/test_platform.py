import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from map_platform.cli import build
from map_platform.evals import evaluate, gate, load_jsonl, synthetic, replay
from map_platform.registry import Registry, parse_manifest

ROOT = os.path.join(os.path.dirname(__file__), "..")

def test_registry_loads_six_agents():
    r = Registry(); r.load_dir(os.path.join(ROOT, "agents")); assert len(r) == 6, len(r)

def test_manifest_validation():
    try:
        parse_manifest("id: x\nname: y\n"); assert False
    except Exception: pass

def test_router_and_escalation():
    p = build()
    assert p.handle("What is the pricing fee and cost?").agent_id == "pricing-faq"
    assert p.handle("zxqv unrelated gibberish blorp").escalated

def test_memory_retrieval():
    p = build(); docs = p.store.search("pricing fees", ["pricing"]); assert docs and docs[0]["source"] == "pricing"

def test_gateway_fallback():
    from map_platform.gateway import Gateway
    from map_platform.models import AgentManifest
    class Flaky:
        def generate(self, model, prompt, ctx):
            if model == "bad": raise RuntimeError("down")
            return "ok"
    m = AgentManifest("a", "A", "t", ["o@x"], "bad", "p", fallback_models=["good"])
    assert Gateway(Flaky()).generate(m, "hi", []) == "ok"

def test_synthetic_size_and_eval_gate():
    assert len(synthetic(2000)) == 2000
    p = build(); golden = load_jsonl(os.path.join(ROOT, "data/golden.jsonl"))
    r = evaluate(p, golden); assert r["routing_accuracy"] >= 0.8, r
    ok, _ = gate(r, r); assert ok
    bad = dict(r, routing_accuracy=r["routing_accuracy"] - 0.5)
    ok, _ = gate(bad, r); assert not ok

def test_replay_small():
    r = replay(build(), synthetic(60)); assert r["n"] == 60 and r["routing_accuracy"] > 0.5, r

if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for f in fns: f(); print(f"PASS {f.__name__}")
    print(f"{len(fns)} tests passed")
