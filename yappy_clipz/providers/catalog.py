"""Provider and model manifest registry."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

PROVIDER_ID = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
MODEL_ID = re.compile(r"^[a-z0-9][a-z0-9._-]*(?:/[a-z0-9][a-z0-9._-]*)+$")


class ProviderCatalogError(ValueError):
    """Raised when provider metadata is invalid or unavailable."""


class ProviderCatalog:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).expanduser().resolve()

    @staticmethod
    def _copy(value: Any) -> Any:
        return json.loads(json.dumps(value))

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.root.is_dir():
            return {}
        indexed: dict[str, dict[str, Any]] = {}
        model_ids: dict[str, set[str]] = {}
        for path in sorted(self.root.rglob("manifest.json")):
            resolved = path.resolve()
            try:
                resolved.relative_to(self.root)
            except ValueError as exc:
                raise ProviderCatalogError("provider manifest escaped configured root") from exc
            try:
                data = json.loads(resolved.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ProviderCatalogError(f"unreadable provider manifest: {path}") from exc
            if data.get("schemaVersion") != "1.0.0":
                raise ProviderCatalogError(f"unsupported provider manifest: {path}")
            provider_id = data.get("providerId")
            if not isinstance(provider_id, str) or not PROVIDER_ID.fullmatch(provider_id):
                raise ProviderCatalogError(f"invalid provider id in {path}")
            models = data.get("models", [])
            if not isinstance(models, list):
                raise ProviderCatalogError(f"models must be a list for {provider_id}")
            if provider_id not in indexed:
                indexed[provider_id] = {key: self._copy(value) for key, value in data.items() if key != "models"}
                indexed[provider_id]["models"] = []
                model_ids[provider_id] = set()
            else:
                primary = indexed[provider_id]
                for stable_key in ("displayName", "credentialMode", "queueBaseUrl", "keyEnvironmentVariable"):
                    incoming = data.get(stable_key)
                    existing = primary.get(stable_key)
                    if incoming is not None and existing is not None and incoming != existing:
                        raise ProviderCatalogError(f"provider fragment conflicts on {stable_key}: {provider_id}")
                    if existing is None and incoming is not None:
                        primary[stable_key] = self._copy(incoming)
                verified = data.get("verifiedAt")
                if verified and verified > str(primary.get("verifiedAt", "")):
                    primary["verifiedAt"] = verified
            for model in models:
                model_id = model.get("modelId") if isinstance(model, dict) else None
                if not isinstance(model_id, str) or not MODEL_ID.fullmatch(model_id):
                    raise ProviderCatalogError(f"invalid model id for {provider_id}")
                if model_id in model_ids[provider_id]:
                    raise ProviderCatalogError(f"duplicate model id: {model_id}")
                model_ids[provider_id].add(model_id)
                indexed[provider_id]["models"].append(self._copy(model))
        for provider in indexed.values():
            provider["models"] = sorted(provider["models"], key=lambda item: item["modelId"])
        return indexed

    def list(self) -> list[dict[str, Any]]:
        summaries: list[dict[str, Any]] = []
        for provider in self._load().values():
            summaries.append({"providerId":provider["providerId"],"displayName":provider.get("displayName",provider["providerId"]),"credentialMode":provider.get("credentialMode","server_env"),"executionEnabledByDefault":bool(provider.get("executionEnabledByDefault",False)),"modelCount":len(provider.get("models",[])),"documentation":provider.get("documentation")})
        return sorted(summaries,key=lambda item:item["providerId"])

    def get(self, provider_id: str) -> dict[str, Any]:
        if not isinstance(provider_id, str) or not PROVIDER_ID.fullmatch(provider_id):
            raise ProviderCatalogError("invalid provider id")
        try:return self._copy(self._load()[provider_id])
        except KeyError as exc:raise ProviderCatalogError(f"provider not found: {provider_id}") from exc

    def get_model(self, provider_id: str, model_id: str) -> dict[str, Any]:
        provider=self.get(provider_id)
        for model in provider.get("models",[]):
            if model.get("modelId")==model_id:return self._copy(model)
        raise ProviderCatalogError(f"model not found for {provider_id}: {model_id}")
