"""Hosted-auth extensions over the universal action dispatcher."""
from __future__ import annotations

import time
from typing import Any

from .actions import ActionContext, ActionDispatcher
from .auth import AuthConfigurationError, AuthError, AuthenticationRequired, AuthorizationDenied, AuthService, Principal
from .capabilities import CapabilityRegistry
from .errors import ActionProblem


_EXTRA_CAPABILITIES = {
    "session.inspect": {
        "actionId":"session.inspect","version":"1.0.0","title":"Inspect session","description":"Inspect the authenticated principal without exposing credentials.",
        "execution":"sync","risk":"low","approvalPolicy":"none","requiredScopes":[],"icmStages":[],"lifecycle":"stable","idempotency":"none",
        "cli":{"command":"yappy-clipz action run session.inspect"},"api":{"method":"GET","path":"/api/v1/session"},"mcp":{"tool":"action_run"},
    },
    "token.create": {
        "actionId":"token.create","version":"1.0.0","title":"Create service token","description":"Create a least-privilege service token whose scopes are a subset of the caller.",
        "execution":"sync","risk":"high","approvalPolicy":"explicit","requiredScopes":[],"icmStages":[],"lifecycle":"stable","idempotency":"required",
        "cli":{"command":"yappy-clipz action run token.create"},"api":{"method":"POST","path":"/api/v1/tokens"},"mcp":{"tool":"action_run"},
    },
    "token.revoke": {
        "actionId":"token.revoke","version":"1.0.0","title":"Revoke token","description":"Persistently revoke a signed session or service token.",
        "execution":"sync","risk":"high","approvalPolicy":"explicit","requiredScopes":[],"icmStages":[],"lifecycle":"stable","idempotency":"supported",
        "cli":{"command":"yappy-clipz action run token.revoke"},"api":{"method":"DELETE","path":"/api/v1/tokens"},"mcp":{"tool":"action_run"},
    },
}


class HostedCapabilityRegistry:
    def __init__(self, base: CapabilityRegistry) -> None:
        self.base = base

    def list(self, *, lifecycle: str | None = None) -> list[dict[str, Any]]:
        rows = self.base.list(lifecycle=lifecycle)
        rows.extend(value for value in _EXTRA_CAPABILITIES.values() if lifecycle is None or value["lifecycle"] == lifecycle)
        return sorted(rows, key=lambda item: item["actionId"])

    def describe(self, action_id: str) -> dict[str, Any]:
        if action_id in _EXTRA_CAPABILITIES:
            return dict(_EXTRA_CAPABILITIES[action_id])
        return self.base.describe(action_id)

    def contains(self, action_id: str) -> bool:
        return action_id in _EXTRA_CAPABILITIES or self.base.contains(action_id)

    def action_ids(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.base.action_ids()) | set(_EXTRA_CAPABILITIES)))


class HostedActionDispatcher(ActionDispatcher):
    def __init__(self, *, auth: AuthService, **kwargs: Any) -> None:
        self.auth = auth
        super().__init__(**kwargs)
        self._handlers.update({
            "session.inspect": self._session_inspect,
            "token.create": self._token_create,
            "token.revoke": self._token_revoke,
        })

    def dispatch(self, action_id: str, input_payload: dict[str, Any] | None = None, *, context: ActionContext | None = None) -> dict[str, Any]:
        try:
            return super().dispatch(action_id, input_payload, context=context)
        except ActionProblem:
            raise
        except AuthenticationRequired as exc:
            raise ActionProblem("authentication_required", str(exc), 401) from exc
        except AuthorizationDenied as exc:
            raise ActionProblem("authorization_denied", str(exc), 403) from exc
        except AuthConfigurationError as exc:
            raise ActionProblem("service_not_configured", str(exc), 503) from exc
        except AuthError as exc:
            raise ActionProblem("authentication_required", str(exc), 401) from exc

    @staticmethod
    def _principal(context: ActionContext) -> Principal:
        if not context.tenant_id or not context.actor_id or context.scopes is None:
            raise ActionProblem("authentication_required", "authenticated principal is required", 401)
        now = int(time.time())
        return Principal(context.tenant_id, context.actor_id, tuple(context.scopes), "context", "session", now, now + 3600)

    def _session_inspect(self, payload: dict[str, Any], context: ActionContext) -> dict[str, Any]:
        principal = self._principal(context)
        return {"tenantId":principal.tenant_id,"actorId":principal.actor_id,"scopes":list(principal.scopes),"tokenType":principal.token_type}

    def _token_create(self, payload: dict[str, Any], context: ActionContext) -> dict[str, Any]:
        principal = self._principal(context)
        name = self.req(payload, "name")
        scopes = self.req(payload, "scopes")
        if not isinstance(scopes, list):
            raise ActionProblem("invalid_request", "scopes must be an array", 400)
        return self.auth.issue_service_token(principal, name=name, scopes=scopes, ttl_seconds=payload.get("ttlSeconds"))

    def _token_revoke(self, payload: dict[str, Any], context: ActionContext) -> dict[str, Any]:
        self._principal(context)
        token_id = self.auth.revoke(self.req(payload, "token"))
        return {"revoked": True, "tokenId": token_id}
