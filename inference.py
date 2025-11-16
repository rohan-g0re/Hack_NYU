import json
import re
import sys
import time
from typing import Any, Dict, Optional

try:
    import requests
except ImportError as exc:  # pragma: no cover - makes error clearer for users
    raise RuntimeError("Install the `requests` package: pip install requests") from exc


# === CHANGE ME ===
CONFIG = {
    "api_base": "http://localhost:1234/v1",  # ← LM Studio server URL
    "model": "lmstudio-community/qwen3-1.7b",  # ← pick the model you started in LM Studio
    "prompt": "Can you tell me who are the sidemen?",  # ← validation query
    "stream": True,  # ← set False to wait for a single response payload
    "generation": {
        "temperature": 0.7,
        "top_p": 1.0,
        "max_tokens": 256,
        "presence_penalty": 0.0,
        "frequency_penalty": 0.0,
    },
    "metrics": {
        "enabled": True,  # ← switch off if you don't need live TPS estimates
        "interval_seconds": 0.5,
    },
}
# =================


_TOKEN_PATTERN = re.compile(r"\w+|[^\s\w]", re.UNICODE)


def _estimate_tokens(text: str) -> int:
    text = text.strip()
    if not text:
        return 0
    return len(_TOKEN_PATTERN.findall(text))


class LMStudioInferenceService:
    """Minimal helper that talks to LM Studio's OpenAI-compatible HTTP API."""

    def __init__(
        self,
        api_base: str,
        model: str,
        *,
        default_generation: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self.model = model
        self.default_generation = default_generation or {}
        self.session = requests.Session()

    def __call__(
        self,
        query: str,
        stream: bool = False,
        *,
        generation: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not query or not query.strip():
            raise ValueError("Query must be a non-empty string.")

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": query}],
            "stream": stream,
        }
        payload.update(self.default_generation)
        if generation:
            payload.update(generation)

        endpoint = f"{self.api_base}/chat/completions"
        metrics_cfg = metrics or {}
        metrics_enabled = metrics_cfg.get("enabled", False)
        metrics_interval = metrics_cfg.get("interval_seconds", 0.5)
        start_time = time.perf_counter()

        with self.session.post(endpoint, json=payload, stream=stream, timeout=120) as resp:
            resp.raise_for_status()
            if stream:
                return self._consume_stream(resp, start_time, metrics_enabled, metrics_interval)
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            print(content)
            if metrics_enabled:
                usage = data.get("usage") or {}
                total_tokens = usage.get("completion_tokens") or _estimate_tokens(content)
                elapsed = max(time.perf_counter() - start_time, 1e-9)
                rate = total_tokens / elapsed if elapsed else 0.0
                source = "usage" if usage.get("completion_tokens") else "estimate"
                print(
                    f"[metrics] elapsed={elapsed:.2f}s tokens={total_tokens} rate={rate:.2f} tok/s ({source})",
                    file=sys.stderr,
                )
            return {"content": content, "streamed": False, "raw": data}

    def _consume_stream(
        self,
        response: requests.Response,
        start_time: float,
        metrics_enabled: bool,
        metrics_interval: float,
    ) -> Dict[str, Any]:
        response_text = ""
        last_report = start_time
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            payload = line[len("data:") :].strip()
            if payload == "[DONE]":
                break
            chunk = json.loads(payload)
            delta = chunk["choices"][0]["delta"]
            content = delta.get("content", "")
            if content:
                print(content, end="", flush=True)
                response_text += content

            if metrics_enabled:
                now = time.perf_counter()
                elapsed = max(now - start_time, 1e-9)
                should_report = (now - last_report) >= metrics_interval
                if should_report:
                    total_tokens = _estimate_tokens(response_text)
                    rate = total_tokens / elapsed if elapsed else 0.0
                    print(
                        f"\n[metrics] elapsed={elapsed:.2f}s tokens={total_tokens} rate={rate:.2f} tok/s (estimate)",
                        file=sys.stderr,
                        flush=True,
                    )
                    last_report = now
        print()
        return {"content": response_text, "streamed": True}


def main() -> None:
    try:
        service = LMStudioInferenceService(
            api_base=CONFIG["api_base"],
            model=CONFIG["model"],
            default_generation=CONFIG.get("generation"),
        )
        service(
            query=CONFIG["prompt"],
            stream=CONFIG["stream"],
            generation=CONFIG.get("generation"),
            metrics=CONFIG.get("metrics"),
        )
    except Exception as exc:
        print(f"[inference.py] Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()