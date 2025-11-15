import re
import sys
import time
from typing import Dict, Any, Optional

try:
    import ollama  # type: ignore[import-not-found]
except ImportError:
    ollama = None

# === CHANGE ME ===
CONFIG = {
    "model": "gemma3:4b",                  # ← set your Ollama model name
    "host": None,                         # ← or "http://localhost:11434" if custom
    "prompt": "Can you tell me who are the sidemen",   # ← validation query sent to the model
    "stream": True,                       # ← False to wait for the full response
    "options": {
        # --- GPU tuning ---
        # num_gpu>0 tells llama.cpp (and therefore Ollama) to offload layers to GPU.
        # Keep <= actual GPU count; if this stays 0 Ollama will fall back to CPU.
        "num_gpu": 1,
        # num_batch can stay modest on smaller GPUs; raise it if you have headroom.
        "num_batch": 512,
        # Force as many layers as possible onto the GPU (=-1 means "all available").
        "gpu_layers": -1,
    },
    "metrics": {
        "enabled": True,                  # ← switch off if you don't need live TPS
        "interval_seconds": 0.5,          # ← how often to print the rolling rate
    },
}
# =================


_TOKEN_PATTERN = re.compile(r"\w+|[^\s\w]", re.UNICODE)


def _estimate_tokens(text: str) -> int:
    text = text.strip()
    if not text:
        return 0
    return len(_TOKEN_PATTERN.findall(text))


class OllamaInferenceService:
    """Callable wrapper so LangGraph (or any orchestrator) can invoke Ollama."""

    def __init__(self, model: str, host: Optional[str] = None):
        if ollama is None:
            raise RuntimeError(
                "Missing dependency: install with `pip install ollama`."
            )
        self.model = model
        self.client = ollama.Client(host=host) if host else ollama.Client()

    def __call__(
        self,
        query: str,
        stream: bool = False,
        *,
        options: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not query or not query.strip():
            raise ValueError("Query must be a non-empty string.")
        metrics_cfg = metrics or {}
        metrics_enabled = metrics_cfg.get("enabled", False)
        metrics_interval = metrics_cfg.get("interval_seconds", 0.5)

        start_time = time.perf_counter()

        response = self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": query}],
            stream=stream,
            options=options,
        )
        if stream:
            response_text = ""
            last_report = start_time
            for chunk in response:
                message = chunk.message if hasattr(chunk, "message") else None
                content = getattr(message, "content", "") or ""
                if content:
                    print(content, end="", flush=True)
                    response_text += content

                now = time.perf_counter()
                if metrics_enabled:
                    total_tokens = chunk.eval_count or _estimate_tokens(response_text)
                    elapsed = max(now - start_time, 1e-9)
                    should_report = (now - last_report) >= metrics_interval or bool(
                        getattr(chunk, "done", False)
                    )
                    if should_report:
                        rate = total_tokens / elapsed if elapsed else 0.0
                        source = (
                            "eval_count"
                            if chunk.eval_count is not None
                            else "estimate"
                        )
                        print(
                            f"\n[metrics] elapsed={elapsed:.2f}s tokens={total_tokens} rate={rate:.2f} tok/s ({source})",
                            file=sys.stderr,
                            flush=True,
                        )
                        last_report = now
            print()
            return {"content": response_text, "streamed": True}
        content = response["message"]["content"]
        print(content)
        if metrics_enabled:
            total_tokens = response.get("eval_count") or _estimate_tokens(content)
            elapsed = max(time.perf_counter() - start_time, 1e-9)
            infer_duration = response.get("eval_duration")
            duration_seconds = (
                infer_duration / 1e9 if infer_duration is not None else elapsed
            )
            rate = total_tokens / duration_seconds if duration_seconds else 0.0
            source = (
                "eval_count"
                if response.get("eval_count") is not None
                else "estimate"
            )
            print(
                f"[metrics] elapsed={elapsed:.2f}s tokens={total_tokens} rate={rate:.2f} tok/s ({source})",
                file=sys.stderr,
            )
        return {"content": content, "streamed": False}


def main() -> None:
    try:
        service = OllamaInferenceService(
            model=CONFIG["model"],
            host=CONFIG["host"],
        )
        service(
            query=CONFIG["prompt"],
            stream=CONFIG["stream"],
            options=CONFIG.get("options"),
            metrics=CONFIG.get("metrics"),
        )
    except Exception as exc:
        print(f"[inference.py] Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()