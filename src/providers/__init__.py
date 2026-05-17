from .base import ChatProvider
from .ollama import OllamaProvider
from .zhipu import ZhipuProvider

_REGISTRY: dict[str, ChatProvider] = {
    "ollama": OllamaProvider(),
    "zhipu": ZhipuProvider(),
}


def get_provider(name: str) -> ChatProvider:
    key = (name or "").strip().lower()
    provider = _REGISTRY.get(key)
    if provider is None:
        supported = ", ".join(sorted(_REGISTRY))
        raise ValueError(f"不支持的 LLM_PROVIDER={name!r}，可选：{supported}")
    return provider


def registered_names() -> list[str]:
    return sorted(_REGISTRY)
