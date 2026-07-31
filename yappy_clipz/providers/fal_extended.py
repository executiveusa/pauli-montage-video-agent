"""Extended fal adapter for verified image/video manifests."""
from __future__ import annotations

import ipaddress
from typing import Any
from urllib.parse import urlparse

from .fal import FalProviderAdapter, FalProviderValidationError


class ExtendedFalProviderAdapter(FalProviderAdapter):
    @staticmethod
    def _public_https(value: Any, field: str) -> str:
        if not isinstance(value, str) or len(value) > 4096:
            raise FalProviderValidationError(f"{field} must contain a public HTTPS URL")
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise FalProviderValidationError(f"{field} must contain a public HTTPS URL without credentials")
        host = parsed.hostname or ""
        if host.lower() == "localhost" or host.endswith(".local"):
            raise FalProviderValidationError(f"{field} cannot use local hosts")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and (address.is_private or address.is_loopback or address.is_link_local or address.is_reserved):
            raise FalProviderValidationError(f"{field} cannot use private or reserved addresses")
        return value

    @staticmethod
    def _validate_input(model: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        validated = FalProviderAdapter._validate_input(model, payload)
        for field, value in validated.items():
            if field.endswith("_url") and value is not None:
                ExtendedFalProviderAdapter._public_https(value, field)
            elif field.endswith("_urls") and value is not None:
                if not isinstance(value, list):
                    raise FalProviderValidationError(f"{field} must be an array")
                for item in value:
                    ExtendedFalProviderAdapter._public_https(item, field)
        num_images = validated.get("num_images")
        maximum = int((model.get("limits") or {}).get("maxImages", 4))
        if num_images is not None and (not isinstance(num_images, int) or not 1 <= num_images <= maximum):
            raise FalProviderValidationError(f"num_images must be between 1 and {maximum}")
        return validated

    @staticmethod
    def _estimate_cost(model: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        pricing = model.get("pricing", {})
        unit = pricing.get("unit")
        amount = None
        details: dict[str, Any] = {}
        if unit == "image":
            count = int(payload.get("num_images", model.get("defaults", {}).get("num_images", 1)))
            rate = pricing.get("perImageUsd")
            amount = round(float(rate) * count, 6) if rate is not None else None
            details = {"count": count, "ratePerImage": rate}
        elif unit == "megapixel":
            megapixels = payload.get("_estimate_megapixels")
            rate = pricing.get("perMegapixelUsd")
            amount = round(float(rate) * float(megapixels), 6) if rate is not None and megapixels is not None else None
            details = {"estimatedMegapixels": megapixels, "ratePerMegapixel": rate}
        elif unit == "compute_second":
            seconds = payload.get("_estimate_compute_seconds")
            rate = pricing.get("ratePerComputeSecondUsd")
            amount = round(float(rate) * float(seconds), 6) if rate is not None and seconds is not None else None
            details = {"estimatedComputeSeconds": seconds, "ratePerComputeSecond": rate}
        else:
            return FalProviderAdapter._estimate_cost(model, payload)
        return {
            "currency": pricing.get("currency", "USD"),
            "amount": amount,
            "unit": unit,
            "estimateOnly": True,
            "pricingVerifiedAt": pricing.get("verifiedAt"),
            "pricingSource": pricing.get("source"),
            "note": "Provider pricing can change; recheck before paid submission.",
            **details,
        }

    def plan(self, *, model_id: str, input_payload: dict[str, Any], webhook_url: str | None = None) -> dict[str, Any]:
        internal = {key: value for key, value in input_payload.items() if key.startswith("_estimate_")}
        provider_input = {key: value for key, value in input_payload.items() if not key.startswith("_estimate_")}
        model = self._model(model_id)
        payload = self._validate_input(model, provider_input)
        webhook = self._validate_webhook(webhook_url)
        estimate_payload = dict(payload)
        estimate_payload.update(internal)
        return {
            "providerId": self.provider_id,
            "modelId": model_id,
            "endpoint": f"{self.settings.queue_base_url.rstrip('/')}/{model_id}",
            "input": payload,
            "webhookUrl": webhook,
            "headers": {"Authorization":"Key [REDACTED]","Content-Type":"application/json","X-Fal-Store-IO":"1" if self.settings.store_io else "0"},
            "configured": self.configured(),
            "executionEnabled": self.settings.execution_enabled,
            "approvalRequired": True,
            "estimatedCost": self._estimate_cost(model, estimate_payload),
            "model": {"title":model.get("title",model_id),"capabilities":list(model.get("capabilities",[])),"limits":self._copy(model.get("limits",{}))},
        }
