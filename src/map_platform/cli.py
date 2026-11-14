from __future__ import annotations
import argparse, json, os, sys
from .evals import evaluate, gate, load_jsonl, replay, synthetic
from .memory import InMemoryStore
from .platform import Platform
from .registry import Registry
from .tracing import Tracer

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")

def build(agents_dir=None, traces=None) -> Platform:
    reg = Registry(); reg.load_dir(agents_dir or os.path.join(ROOT, "agents"))
    store = InMemoryStore()
    for d in load_jsonl(os.path.join(ROOT, "data/docs.jsonl")): store.add_doc(d["id"], d["source"], d["text"])
    return Platform(reg, store=store, tracer=Tracer(traces))

def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="map"); sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("onboard"); s.add_argument("manifest")
    s = sub.add_parser("replay"); s.add_argument("--n", type=int, default=2000); s.add_argument("--out", default="")
    s = sub.add_parser("eval"); s.add_argument("--golden", default=os.path.join(ROOT, "data/golden.jsonl")); s.add_argument("--out", default="")
    s = sub.add_parser("gate"); s.add_argument("--baseline", required=True); s.add_argument("--golden", default=os.path.join(ROOT, "data/golden.jsonl")); s.add_argument("--max-drop", type=float, default=0.0)
    a = p.parse_args(argv)
    if a.cmd == "onboard":
        m = Registry().onboard(a.manifest); print(f"onboarded {m.id} team={m.team} owners={','.join(m.owners)} tools={','.join(m.tools)}"); return 0
    plat = build(traces=os.environ.get("MAP_TRACES"))
    if a.cmd == "replay":
        r = replay(plat, synthetic(a.n)); print(json.dumps(r, indent=2))
        if a.out: open(a.out, "w").write(json.dumps(r, indent=2))
        return 0
    if a.cmd == "eval":
        r = evaluate(plat, load_jsonl(a.golden)); print(json.dumps(r, indent=2))
        if a.out: open(a.out, "w").write(json.dumps(r, indent=2))
        return 0
    if a.cmd == "gate":
        cur = evaluate(plat, load_jsonl(a.golden)); ok, msg = gate(cur, json.load(open(a.baseline)), a.max_drop)
        print(json.dumps(cur, indent=2)); print(msg); return 0 if ok else 1
    return 2

if __name__ == "__main__": sys.exit(main())
