"""Explicit semantic-provider configuration for v0.2.10.

The recovered v0.2.9 provider remains immutable. This module ensures new
runtime code never relies on its historical model default.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import os
from typing import Any, Mapping, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class SemanticProviderConfig:
    provider: str
    model_id: str
    request_parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.provider, str) or not self.provider.strip():
            raise ValueError("semantic_provider_required")
        if not isinstance(self.model_id, str) or not self.model_id.strip():
            raise ValueError("semantic_model_required")
        if not isinstance(self.request_parameters, Mapping):
            raise TypeError("request_parameters_invalid")
        object.__setattr__(self, "provider", self.provider.strip())
        object.__setattr__(self, "model_id", self.model_id.strip())
        object.__setattr__(
            self, "request_parameters", dict(self.request_parameters)
        )

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
        *,
        request_parameters: Mapping[str, Any] | None = None,
    ) -> "SemanticProviderConfig":
        source = os.environ if env is None else env
        model_id = source.get("PAC_SEMANTIC_MODEL", "")
        provider = source.get("PAC_SEMANTIC_PROVIDER", "openai-responses")
        return cls(
            provider=provider,
            model_id=model_id,
            request_parameters=dict(request_parameters or {}),
        )


def build_configured_provider(
    config: SemanticProviderConfig,
    provider_cls: type[T],
    *,
    client=None,
    prompt: str | None = None,
) -> T:
    """Instantiate a provider with an explicit model id.

    The provider class may be the recovered v0.2.9 implementation or a future
    v0.2.10 provider. This adapter never calls a provider constructor without
    the model argument.
    """
    if not isinstance(config, SemanticProviderConfig):
        raise TypeError("semantic_provider_config_invalid")
    return provider_cls(
        client=client,
        model=config.model_id,
        prompt=prompt,
    )
