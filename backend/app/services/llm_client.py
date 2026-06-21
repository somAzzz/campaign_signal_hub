import json
from abc import ABC, abstractmethod
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.core.config import settings


class LLMClient(ABC):
    @abstractmethod
    def complete_json(self, prompt: str) -> dict:
        """Return structured JSON from an LLM prompt."""


class StubLLMClient(LLMClient):
    def complete_json(self, prompt: str) -> dict:
        return {"provider": "stub", "prompt_preview": prompt[:240]}


class SGLangClient(LLMClient):
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: int,
        max_tokens: int,
    ) -> None:
        self.base_url = base_url
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens

    def complete_json(self, prompt: str) -> dict:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a campaign intelligence analyst. Return only "
                        "one valid JSON object. No markdown."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "max_tokens": self.max_tokens,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        request = Request(
            f"{self.base_url.rstrip('/')}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except URLError as exc:
            raise RuntimeError(f"sglang request failed: {exc}") from exc

        content = body["choices"][0]["message"]["content"]
        return _extract_json_object(content)


def get_llm_client() -> LLMClient:
    if settings.llm_provider == "sglang":
        return SGLangClient(
            base_url=settings.sglang_base_url,
            model=settings.sglang_model,
            timeout_seconds=settings.llm_timeout_seconds,
            max_tokens=settings.llm_max_tokens,
        )
    return StubLLMClient()


def _extract_json_object(content: str) -> dict:
    decoder = json.JSONDecoder()
    candidates: list[dict] = []

    for index, char in enumerate(content):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(content[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            candidates.append(value)

    if not candidates:
        raise ValueError("LLM response did not contain a valid JSON object.")

    for candidate in candidates:
        if "signals" in candidate:
            return candidate

    return candidates[-1]
