# markets-agent-platform

Federated platform where teams onboard their own LLM agents to answer inbound
client requests — with an agent registry, intent routing, memory/retrieval, a
model gateway, a training-ground replay, and an evaluation framework with a
regression gate.

## Design

```
                 inbound client request
                           |
                    +------v-------+
                    | Intent Router|  embedding similarity (hashing vectors)
                    | + rules boost|  + keyword rules, confidence threshold
                    +------+-------+
              below threshold |  best agent
                    +------v---------------------------+
                    |  human escalation (ticket)       |
                    +----------------------------------+
                           | routed
              +------------v-------------+      +-------------------+
              | Agent runner             |----->| Model Gateway     |
              | (manifest prompt/tools)|      | Bedrock + fallback|
              +--+-------+---------------+      | (mock for tests)  |
                 |       |                      +-------------------+
        retrieve v       v recall
          +-----------+ +----------------+     +-------------------+
          | Retrieval | | Memory         |     | Tracing           |
          | OpenSearch| | Postgres+      |---->| spans -> JSONL    |
          | (in-mem   | | pgvector       |     | route/retrieve/   |
          |  fallback)| | (in-mem fallback|    | generate          |
          +-----------+ +----------------+     +-------------------+

  Training ground: 2,000 synthetic requests --replay--> routing accuracy / p95
  Eval framework:  golden sets --eval--> groundedness, judge, p95 --gate--> CI fail on drop
```

| Component | Implementation | Production adapter |
|---|---|---|
| Registry / manifests | YAML-subset manifests in `agents/`, validated on onboard | same files, loaded from any dir |
| Router | hashing-embedding centroid similarity + keyword rules, threshold → escalation | swap `embeddings.embed` for a real embedding model |
| Memory / retrieval | `InMemoryStore` (docs + conversation turns) | Postgres + pgvector (`PostgresMemory`, `data/schema.sql`), OpenSearch kNN (`OpenSearchRetrieval`) |
| Model gateway | `Gateway` tries manifest model → `fallback_models`; deterministic `MockProvider` | `BedrockProvider` (boto3, optional extra) |
| Training ground | `synthetic(2000)` seeded templates per agent, `replay()` | point replay at logged real requests |
| Eval framework | golden set per agent, `MockJudge` (LLM-as-judge interface), routing accuracy, groundedness, p95 latency | implement `score()` with a real judge model |
| Tracing | OTel-style spans (`trace_id`/`span_id`/duration) → JSONL | export JSONL to any OTel collector |
| Service / UI | FastAPI (`map_platform.api`), stdlib fallback, `ui/index.html` | ECS Fargate (`infra/terraform/`) |

## Quickstart

```bash
python3 -m venv .venv
.venv/bin/pip install -e .          # zero required dependencies (core is stdlib-only)
.venv/bin/map onboard agents/pricing-faq.yaml
.venv/bin/map replay --n 2000
.venv/bin/map eval
.venv/bin/map eval --out baseline.json
.venv/bin/map gate --baseline baseline.json   # exits 1 if routing accuracy drops
```

Or without installing: `PYTHONPATH=src .venv/bin/python -m map_platform.cli eval`

## Tests

```bash
.venv/bin/python tests/run_tests.py   # plain assert-based runner, no services needed
# or, with pytest installed:  .venv/bin/pip install -e ".[dev]" && .venv/bin/python -m pytest tests/
```

Output:

```
PASS test_gateway_fallback
PASS test_manifest_validation
PASS test_memory_retrieval
PASS test_registry_loads_six_agents
PASS test_replay_small
PASS test_router_and_escalation
PASS test_synthetic_size_and_eval_gate
7 tests passed
```

## Sanity runs (real output, captured locally)

Training-ground replay of the full 2,000 synthetic requests (mock provider, in-memory store):

```
$ map replay --n 2000
{
  "n": 2000,
  "routing_accuracy": 0.997,
  "p95_latency_ms": 0.16,
  "mean_latency_ms": 0.123,
  "escalations": 333
}
```

Golden-set eval (12 cases, 2 per agent):

```
$ map eval
{
  "n": 12,
  "routing_accuracy": 1.0,
  "groundedness": 0.75,
  "judge_score": 0.6061,
  "p95_latency_ms": 0.16
}
```

`escalations` counts requests routed to the escalation agent (the synthetic
complaint class is ~1/6 of traffic, plus low-confidence fallbacks). Latencies
are in-process mock latencies — they measure routing/retrieval overhead, not
real model latency.

## Example agents

`pricing-faq`, `research-summary`, `product-eligibility`, `trade-status`,
`onboarding-docs`, `escalation` — see `agents/*.yaml` (tools, prompt, model,
fallback models, retrieval sources, owners, keywords, routing examples).

## Service, Docker, AWS

```bash
.venv/bin/pip install -e ".[service]" && .venv/bin/python -m map_platform.api  # http://localhost:8000
docker compose up --build   # app + Postgres(pgvector) + OpenSearch
terraform -chdir=infra/terraform init && terraform -chdir=infra/terraform plan  # ECS Fargate skeleton
```

## Limitations (honest)

- **Embeddings are hashing vectors**, not a semantic model — good enough for
  templated intents, not for paraphrase-heavy real traffic. Swap one function.
- **Mock LLM and mock judge** are deterministic keyword scorers; no real model
  is called without Bedrock credentials and the `bedrock`/`psycopg` extras.
- **Postgres/OpenSearch adapters are not integration-tested here** (no services
  in CI); the in-memory fallback is what the tests exercise.
- Manifest parser is a **flat YAML subset** by design (see `registry.py`).
- Groundedness (0.75 on the golden set) is keyword coverage, not entailment.
- No auth, rate limiting, or multi-tenancy isolation — out of scope for this skeleton.

## License

MIT — see `LICENSE`. Copyright (c) 2026 Ayush Gawai.
