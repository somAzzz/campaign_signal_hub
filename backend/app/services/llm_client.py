import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from time import perf_counter
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.core.config import settings


@dataclass
class LLMCompletionResult:
    parsed_json: dict
    raw_response: dict = field(default_factory=dict)
    request_metadata: dict = field(default_factory=dict)
    response_metadata: dict = field(default_factory=dict)
    endpoint: str | None = None


class LLMClient(ABC):
    provider: str
    model: str | None
    endpoint: str | None = None

    @abstractmethod
    def complete_json(self, prompt: str) -> LLMCompletionResult:
        """Return structured JSON from an LLM prompt."""


class StubLLMClient(LLMClient):
    provider = "stub"
    model = None
    endpoint = None

    def complete_json(self, prompt: str) -> LLMCompletionResult:
        payload = {"provider": "stub", "prompt_preview": prompt[:240]}
        return LLMCompletionResult(
            parsed_json=payload,
            raw_response=payload,
            request_metadata={"prompt_chars": len(prompt)},
        )


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
        self.provider = "sglang"
        self.endpoint = f"{self.base_url.rstrip('/')}/v1/chat/completions"
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens

    def complete_json(self, prompt: str) -> LLMCompletionResult:
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
        return _post_chat_completion(
            endpoint=self.endpoint,
            payload=payload,
            timeout_seconds=self.timeout_seconds,
            provider=self.provider,
            model=self.model,
        )


class OpenAICompatibleClient(LLMClient):
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None,
        timeout_seconds: int,
        max_tokens: int,
        provider: str = "openai_compatible",
    ) -> None:
        self.base_url = base_url
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens
        self.provider = provider
        self.endpoint = f"{self.base_url.rstrip('/')}/v1/chat/completions"

    def complete_json(self, prompt: str) -> LLMCompletionResult:
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
        }
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return _post_chat_completion(
            endpoint=self.endpoint,
            payload=payload,
            timeout_seconds=self.timeout_seconds,
            provider=self.provider,
            model=self.model,
            extra_headers=headers,
        )


def get_llm_client() -> LLMClient:
    if settings.llm_provider == "sglang":
        return SGLangClient(
            base_url=settings.sglang_base_url,
            model=settings.sglang_model,
            timeout_seconds=settings.llm_timeout_seconds,
            max_tokens=settings.llm_max_tokens,
        )
    if settings.llm_provider in {"openai", "cloud", "openai_compatible"}:
        return OpenAICompatibleClient(
            base_url=settings.cloud_llm_base_url,
            model=settings.cloud_llm_model,
            api_key=settings.cloud_llm_api_key,
            timeout_seconds=settings.llm_timeout_seconds,
            max_tokens=settings.llm_max_tokens,
            provider=settings.llm_provider,
        )
    return StubLLMClient()


def _post_chat_completion(
    endpoint: str,
    payload: dict,
    timeout_seconds: int,
    provider: str,
    model: str,
    extra_headers: dict[str, str] | None = None,
) -> LLMCompletionResult:
    headers = {"Content-Type": "application/json", **(extra_headers or {})}
    started = perf_counter()
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
            status_code = response.status
    except URLError as exc:
        raise RuntimeError(f"{provider} request failed: {exc}") from exc

    duration_ms = int((perf_counter() - started) * 1000)
    content = body["choices"][0]["message"]["content"]
    safe_headers = {
        key: ("<redacted>" if key.lower() == "authorization" else value)
        for key, value in headers.items()
    }
    return LLMCompletionResult(
        parsed_json=_extract_json_object(content),
        raw_response=body,
        request_metadata={
            "provider": provider,
            "model": model,
            "endpoint": endpoint,
            "prompt_chars": sum(
                len(message.get("content", "")) for message in payload["messages"]
            ),
            "message_count": len(payload["messages"]),
            "max_tokens": payload.get("max_tokens"),
            "temperature": payload.get("temperature"),
            "headers": safe_headers,
        },
        response_metadata={
            "status_code": status_code,
            "duration_ms": duration_ms,
            "response_id": body.get("id"),
            "usage": body.get("usage", {}),
            "finish_reason": body.get("choices", [{}])[0].get("finish_reason"),
            "content_chars": len(content),
        },
        endpoint=endpoint,
    )


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
