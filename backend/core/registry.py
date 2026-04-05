from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class ModelConfig:
    provider: str
    base_url: str
    model: str
    api_key_env: str

    @property
    def api_key(self) -> str:
        return os.environ.get(self.api_key_env, "")


_REGISTRY: dict[str, ModelConfig] = {
    "grok-3": ModelConfig(
        provider="xai",
        base_url="https://api.x.ai/v1",
        model="grok-3",
        api_key_env="XAI_API_KEY",
    ),
    "grok-3-fast": ModelConfig(
        provider="xai",
        base_url="https://api.x.ai/v1",
        model="grok-3-fast",
        api_key_env="XAI_API_KEY",
    ),
}


def get_model(model_id: str) -> ModelConfig:
    if model_id not in _REGISTRY:
        raise KeyError(f"Unknown model: {model_id!r}. Registered: {list(_REGISTRY)}")
    return _REGISTRY[model_id]


def default_model() -> ModelConfig:
    return _REGISTRY["grok-3"]
