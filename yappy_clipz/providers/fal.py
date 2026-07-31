"""Server-side fal queue adapter with explicit paid-execution gates."""

from __future__ import annotations

import json
import os
import re
import ipaddress
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import quote, urlencode, urlparse

import httpx

from .catalog import MODEL_ID, ProviderCatalog, ProviderCatalogError


REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{5,127}$")


class FalProviderError(RuntimeError):
    """Raised when a fal request cannot be safely planned or executed."""


class FalProviderValidationError(FalProviderError):
    """Raised when a provider request is structurally invalid."""


class FalApprovalRequired(FalProviderError):
    """Raised when a paid or state-changing action lacks approval."""


class FalExecutionDisabled(FalProviderError):
    """Raised when paid execution is intentionally disabled."""


class FalUpstreamError(FalProviderError):
    """Raised for retryable provider/network failures."""


class HttpClient(Protocol):
    def request(self, method: str, url: str, **kwargs: Any) -> Any: ...


@dataclass(frozen=True, slots=True)
class FalSettings:
    queue_base_url: str = "https://queue.fal.run"
    key_env: str = "FAL_KEY"
    execution_enabled: bool = False
    store_io: bool = False
    timeout_seconds: float = 30.0


class FalProviderAdapter:
    provider_id = "fal"

    def __init__(
        self,
        catalog: ProviderCatalog,
        settings: FalSettings | None = None,
        http_client: HttpClient | None = None,
    ) -> None:
        self.catalog = catalog
        self.settings = settings or FalSettings()
        self.http_client = http_client or httpx.Client(timeout=self.settings.timeout_seconds)

    @staticmethod
    def _copy(value: Any) -> Any:
        return json.loads(json.dumps(value))

    def configured(self) -> bool:
        return bool(os.environ.get(self.settings.key_env))

    def describe(self) -> dict[str, Any]:
        provider = self.catalog.get(self.provider_id)
        provider["configured"] = self.configured()
        provider["executionEnabled"] = self.settings.execution_enabled
        provider["credential"] = {
            "mode": "server_env",
            "env": self.settings.key_env,
            "present": self.configured(),
            "value": None,
        }
        return provider

    @staticmethod
    def _validate_webhook(url: str | None) -> str | None:
        if url is None:
            return None
        if not isinstance(url, str) or len(url) > 2048:
            raise FalProviderValidationError("webhook_url must be a valid HTTPS URL")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise FalProviderValidationError("webhook_url must be a public HTTPS URL without embedded credentials")
        return url

    @staticmethod
    def _validate_request_id(request_id: str) -> str:
        if not isinstance(request_id, str) or not REQUEST_ID.fullmatch(request_id):
            raise FalProviderValidationError("invalid provider request id")
        return request_id

    def _model(self, model_id: str) -> dict[str, Any]:
        if not isinstance(model_id, str) or not MODEL_ID.fullmatch(model_id):
            raise FalProviderValidationError("invalid fal model id")
        try:
            return self.catalog.get_model(self.provider_id, model_id)
        except ProviderCatalogError as exc:
            raise FalProviderValidationError(str(exc)) from exc

    @staticmethod
    def _validate_input(model: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise FalProviderValidationError("provider input must be an object")
        allowed = set(model.get("allowedInputFields", []))
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise FalProviderValidationError(f"unsupported input fields for model: {', '.join(unknown)}")
        missing = [name for name in model.get("requiredInputFields", []) if payload.get(name) in (None, "")]
        if missing:
            raise FalProviderValidationError(f"missing required input fields: {', '.join(missing)}")
        enums = model.get("enumFields", {})
        for name, accepted in enums.items():
            if name in payload and payload[name] not in accepted:
                raise FalProviderValidationError(f"unsupported {name}: {payload[name]}")
        prompt = payload.get("prompt")
        if prompt is not None and (not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 20_000):
            raise FalProviderValidationError("prompt must be a non-empty string under 20000 characters")
        duration = payload.get("duration")
        if duration is not None and str(duration) != "auto":
            try:
                numeric = int(duration)
            except (TypeError, ValueError) as exc:
                raise FalProviderValidationError("duration must be auto or an integer from 4 to 15") from exc
            if not 4 <= numeric <= 15:
                raise FalProviderValidationError("duration must be auto or an integer from 4 to 15")

        def validate_url(value: Any, field: str) -> str:
            if not isinstance(value, str) or len(value) > 4096:
                raise FalProviderValidationError(f"{field} must contain HTTPS URLs")
            parsed = urlparse(value)
            if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
                raise FalProviderValidationError(f"{field} must contain public HTTPS URLs without credentials")
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

        for field in ("image_url", "end_image_url"):
            if payload.get(field) is not None:
                validate_url(payload[field], field)
        limits = model.get("limits", {})
        list_limits = {"image_urls": int(limits.get("maxImages", 9)), "video_urls": int(limits.get("maxVideos", 3)), "audio_urls": int(limits.get("maxAudio", 3))}
        total_references = 0
        for field, maximum in list_limits.items():
            if field not in payload:
                continue
            values = payload[field]
            if not isinstance(values, list) or len(values) > maximum:
                raise FalProviderValidationError(f"{field} must be a list with at most {maximum} entries")
            for value in values:
                validate_url(value, field)
            total_references += len(values)
        if total_references > int(limits.get("maxTotalReferences", 12)):
            raise FalProviderValidationError("total reference files cannot exceed 12")
        if payload.get("audio_urls") and not (payload.get("image_urls") or payload.get("video_urls")):
            raise FalProviderValidationError("audio references require at least one image or video reference")
        return json.loads(json.dumps(payload))

    @staticmethod
    def _estimate_cost(model: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        pricing = model.get("pricing", {})
        resolution = payload.get("resolution", model.get("defaults", {}).get("resolution"))
        duration = payload.get("duration", model.get("defaults", {}).get("duration"))
        try:
            seconds = int(duration)
        except (TypeError, ValueError):
            seconds = None
        rate = pricing.get("ratesPerSecondUsd", {}).get(str(resolution))
        amount = round(float(rate) * seconds, 4) if rate is not None and seconds is not None else None
        return {
            "currency": "USD",
            "amount": amount,
            "ratePerSecond": rate,
            "seconds": seconds,
            "resolution": resolution,
            "estimateOnly": True,
            "pricingVerifiedAt": pricing.get("verifiedAt"),
            "pricingSource": pricing.get("source"),
            "note": "Provider pricing can change; recheck before paid submission.",
        }

    def plan(
        self,
        *,
        model_id: str,
        input_payload: dict[str, Any],
        webhook_url: str | None = None,
    ) -> dict[str, Any]:
        model = self._model(model_id)
        payload = self._validate_input(model, input_payload)
        webhook = self._validate_webhook(webhook_url)
        return {
            "providerId": self.provider_id,
            "modelId": model_id,
            "endpoint": f"{self.settings.queue_base_url.rstrip('/')}/{model_id}",
            "input": payload,
            "webhookUrl": webhook,
            "headers": {
                "Authorization": "Key [REDACTED]",
                "Content-Type": "application/json",
                "X-Fal-Store-IO": "1" if self.settings.store_io else "0",
            },
            "configured": self.configured(),
            "executionEnabled": self.settings.execution_enabled,
            "approvalRequired": True,
            "estimatedCost": self._estimate_cost(model, payload),
            "model": {
                "title": model.get("title", model_id),
                "capabilities": list(model.get("capabilities", [])),
                "limits": self._copy(model.get("limits", {})),
            },
        }

    def _auth_headers(self) -> dict[str, str]:
        key = os.environ.get(self.settings.key_env)
        if not key:
            raise FalExecutionDisabled(f"fal is not configured; set server-side {self.settings.key_env}")
        return {
            "Authorization": f"Key {key}",
            "Content-Type": "application/json",
            "X-Fal-Store-IO": "1" if self.settings.store_io else "0",
        }

    def _execute(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        response = self.http_client.request(method, url, timeout=self.settings.timeout_seconds, **kwargs)
        status_code = int(getattr(response, "status_code", 500))
        try:
            body = response.json()
        except Exception as exc:
            raise FalUpstreamError("fal returned a non-JSON response") from exc
        if status_code >= 400:
            message = body.get("detail") or body.get("error") or body.get("message") or "fal request failed"
            raise FalUpstreamError(f"fal request failed ({status_code}): {message}")
        if not isinstance(body, dict):
            raise FalUpstreamError("fal returned an invalid response document")
        return body

    def submit(
        self,
        *,
        model_id: str,
        input_payload: dict[str, Any],
        approved: bool,
        idempotency_key: str,
        webhook_url: str | None = None,
    ) -> dict[str, Any]:
        plan = self.plan(model_id=model_id, input_payload=input_payload, webhook_url=webhook_url)
        if not approved:
            raise FalApprovalRequired("explicit approval is required before paid provider submission")
        if not self.settings.execution_enabled:
            raise FalExecutionDisabled("paid fal execution is disabled; set YAPPY_ENABLE_PAID_PROVIDERS=1 server-side")
        if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 200:
            raise FalProviderValidationError("idempotency_key is required for provider submission")
        url = plan["endpoint"]
        if plan["webhookUrl"]:
            url = f"{url}?{urlencode({'fal_webhook': plan['webhookUrl']})}"
        body = self._execute("POST", url, headers=self._auth_headers(), json=plan["input"])
        request_id = body.get("request_id")
        if not isinstance(request_id, str):
            raise FalUpstreamError("fal queue response did not include request_id")
        return {
            "providerId": self.provider_id,
            "modelId": model_id,
            "requestId": request_id,
            "state": "queued",
            "queuePosition": body.get("queue_position"),
            "statusUrl": body.get("status_url"),
            "responseUrl": body.get("response_url"),
            "cancelUrl": body.get("cancel_url"),
            "idempotencyKey": idempotency_key,
            "estimatedCost": plan["estimatedCost"],
            "warning": "Provider-side duplicate suppression is not guaranteed; YAPPY durable jobs must own idempotency.",
        }

    def status(self, *, model_id: str, request_id: str, logs: bool = True) -> dict[str, Any]:
        self._model(model_id)
        request_id = self._validate_request_id(request_id)
        suffix = "?logs=1" if logs else ""
        url = f"{self.settings.queue_base_url.rstrip('/')}/{model_id}/requests/{quote(request_id)}/status{suffix}"
        body = self._execute("GET", url, headers=self._auth_headers())
        return {"providerId": self.provider_id, "modelId": model_id, **body}

    def result(self, *, model_id: str, request_id: str) -> dict[str, Any]:
        self._model(model_id)
        request_id = self._validate_request_id(request_id)
        url = f"{self.settings.queue_base_url.rstrip('/')}/{model_id}/requests/{quote(request_id)}"
        body = self._execute("GET", url, headers=self._auth_headers())
        return {"providerId": self.provider_id, "modelId": model_id, "requestId": request_id, "result": body}

    def cancel(self, *, model_id: str, request_id: str, approved: bool) -> dict[str, Any]:
        self._model(model_id)
        request_id = self._validate_request_id(request_id)
        if not approved:
            raise FalApprovalRequired("explicit approval is required before provider cancellation")
        url = f"{self.settings.queue_base_url.rstrip('/')}/{model_id}/requests/{quote(request_id)}/cancel"
        body = self._execute("PUT", url, headers=self._auth_headers())
        return {"providerId": self.provider_id, "modelId": model_id, "requestId": request_id, **body}
