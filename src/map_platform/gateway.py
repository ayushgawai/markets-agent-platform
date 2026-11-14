"""Model gateway: Bedrock with fallback chain, deterministic mock for tests."""
from __future__ import annotations
import hashlib, json

class MockProvider:
    name = "mock"
    def generate(self, model: str, prompt: str, context: list[str]) -> str:
        ctx = " ".join(context)[:400]
        return (f"Based on retrieved sources: {ctx} | Answering as {model}: "
                f"this addresses the request using the cited material above.")

class BedrockProvider:
    name = "bedrock"
    def __init__(self, region: str = "us-east-1"):
        import boto3  # optional dependency, imported lazily
        self.client = boto3.client("bedrock-runtime", region_name=region)
    def generate(self, model: str, prompt: str, context: list[str]) -> str:
        body = {"anthropic_version": "bedrock-2023-05-31", "max_tokens": 512,
                "messages": [{"role": "user", "content": f"Context:\n{chr(10).join(context)}\n\n{prompt}"}]}
        r = self.client.invoke_model(modelId=model, body=json.dumps(body))
        return json.loads(r["body"].read())["content"][0]["text"]

class Gateway:
    """Tries the agent's model, then fallback_models, in order."""
    def __init__(self, provider=None):
        self.provider = provider or MockProvider()
        self.calls: list[str] = []
    def generate(self, manifest, prompt: str, context: list[str]) -> str:
        last = None
        for model in [manifest.model, *manifest.fallback_models]:
            try:
                self.calls.append(model)
                return self.provider.generate(model, prompt, context)
            except Exception as e:  # provider/model failure -> next fallback
                last = e
        raise RuntimeError(f"all models failed: {last}")
