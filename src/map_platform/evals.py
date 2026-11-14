"""Training ground: 2,000 deterministic synthetic requests + replay, and evals."""
from __future__ import annotations
import json, random, statistics
from .embeddings import tokens
from .platform import Platform

TEMPLATES = {
    "pricing-faq": ["What is the fee for {thing}?", "How much does {thing} cost in pricing charges?",
                    "What are the subscription fees for {thing}?", "Tell me the pricing and billing cost of {thing}"],
    "research-summary": ["Summarise the research report on {thing}", "Give me a summary of the market outlook for {thing}",
                         "What does the research analysis say about {thing}?", "Summarise the latest report on {thing}"],
    "product-eligibility": ["Am I eligible for {thing}?", "Do I qualify for {thing} under the eligibility criteria?",
                            "What are the eligibility requirements for {thing}?", "Am I allowed to access {thing}?"],
    "trade-status": ["What is the status of my trade in {thing}?", "Has my order for {thing} been executed?",
                     "Check the settlement status of my order for {thing}", "Is my {thing} order pending or filled?"],
    "onboarding-docs": ["Which documents do I need for onboarding to {thing}?", "How do I complete account setup for {thing}?",
                        "What KYC documents are required to register for {thing}?", "List the onboarding documents for {thing}"],
    "escalation": ["I have a complaint about {thing}, this is urgent", "Escalate this issue with {thing} to a human",
                   "I suspect fraud related to {thing}", "I want to speak to a human about {thing}, I am angry"],
}
THINGS = ["alpha fund", "global equity plan", "premium account", "sector note", "retirement product",
          "trading account", "advisory service", "new listing", "bond product", "client portal"]

def synthetic(n: int = 2000, seed: int = 7) -> list[dict]:
    rng = random.Random(seed)
    agents = list(TEMPLATES)
    out = []
    for i in range(n):
        a = agents[i % len(agents)]
        out.append({"id": f"req-{i:04d}", "text": rng.choice(TEMPLATES[a]).format(thing=rng.choice(THINGS)), "agent": a})
    rng.shuffle(out)
    return out

def replay(platform: Platform, items: list[dict]) -> dict:
    lat, correct, esc = [], 0, 0
    for it in items:
        ans = platform.handle(it["text"], conv_id=it["id"])
        lat.append(ans.latency_ms); correct += ans.agent_id == it["agent"]; esc += ans.escalated
    lat.sort()
    p95 = lat[int(0.95 * len(lat)) - 1] if lat else 0.0
    return {"n": len(items), "routing_accuracy": round(correct / max(len(items), 1), 4),
            "p95_latency_ms": round(p95, 3), "mean_latency_ms": round(statistics.mean(lat), 3) if lat else 0,
            "escalations": esc}

def groundedness(answer: str, docs: list[str], keywords: list[str]) -> float:
    if not keywords: return 1.0
    at = set(tokens(answer))
    return sum(1 for k in keywords if k.lower() in at or any(k.lower() in tokens(d) and k.lower() in at for d in docs)) / len(keywords)

class MockJudge:
    """LLM-as-judge interface; mock scores grounded keyword coverage deterministically."""
    def score(self, question: str, answer: str, docs: list[str]) -> float:
        qt = set(tokens(question)) - {"what", "is", "the", "for", "my", "do", "i", "a", "to"}
        if not qt: return 1.0
        return round(sum(1 for t in qt if t in set(tokens(answer)) or any(t in tokens(d) for d in docs)) / len(qt), 4)

def evaluate(platform: Platform, golden: list[dict], judge=None) -> dict:
    judge = judge or MockJudge()
    lat, rc, gr, js = [], 0, [], []
    for g in golden:
        ans = platform.handle(g["text"])
        docs = [d["text"] for d in platform.store.search(g["text"])]
        lat.append(ans.latency_ms); rc += ans.agent_id == g["agent"]
        gr.append(groundedness(ans.text, docs, g.get("keywords", []))); js.append(judge.score(g["text"], ans.text, docs))
    lat.sort()
    return {"n": len(golden), "routing_accuracy": round(rc / len(golden), 4),
            "groundedness": round(statistics.mean(gr), 4), "judge_score": round(statistics.mean(js), 4),
            "p95_latency_ms": round(lat[int(0.95 * len(lat)) - 1], 3)}

def gate(current: dict, baseline: dict, max_drop: float = 0.0) -> tuple[bool, str]:
    drop = baseline["routing_accuracy"] - current["routing_accuracy"]
    if drop > max_drop:
        return False, f"FAIL routing_accuracy dropped {drop:.4f} ({baseline['routing_accuracy']} -> {current['routing_accuracy']})"
    return True, f"PASS routing_accuracy {current['routing_accuracy']} vs baseline {baseline['routing_accuracy']}"

def load_jsonl(path: str) -> list[dict]:
    with open(path) as f: return [json.loads(l) for l in f if l.strip()]
