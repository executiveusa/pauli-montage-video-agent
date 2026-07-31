"""Signed sessions and scoped service tokens for hosted YAPPY-CLIPZ."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import uuid4


class AuthError(RuntimeError):
    """Base authentication error."""


class AuthenticationRequired(AuthError):
    pass


class AuthorizationDenied(AuthError):
    pass


class AuthConfigurationError(AuthError):
    pass


@dataclass(frozen=True, slots=True)
class Principal:
    tenant_id: str
    actor_id: str
    scopes: tuple[str, ...]
    token_id: str
    token_type: str
    issued_at: int
    expires_at: int

    def allows(self, required: set[str]) -> bool:
        return required.issubset(self.scopes)


class RevocationStore(Protocol):
    def revoke(self, token_id: str, expires_at: int) -> None: ...
    def is_revoked(self, token_id: str) -> bool: ...


class MemoryRevocationStore:
    def __init__(self) -> None:
        self._revoked: dict[str, int] = {}

    def revoke(self, token_id: str, expires_at: int) -> None:
        self._revoked[token_id] = expires_at

    def is_revoked(self, token_id: str) -> bool:
        now = int(time.time())
        self._revoked = {key: expiry for key, expiry in self._revoked.items() if expiry > now}
        return token_id in self._revoked


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class SignedTokenService:
    """Small auditable HMAC token service with explicit claim validation."""

    def __init__(
        self,
        *,
        secret: str,
        issuer: str = "yappy-clipz",
        audience: str = "yappy-studio",
        revocations: RevocationStore | None = None,
        clock_skew_seconds: int = 30,
    ) -> None:
        if len(secret.encode("utf-8")) < 32:
            raise AuthConfigurationError("token signing secret must contain at least 32 bytes")
        self._secret = secret.encode("utf-8")
        self.issuer = issuer
        self.audience = audience
        self.revocations = revocations or MemoryRevocationStore()
        self.clock_skew_seconds = max(0, clock_skew_seconds)

    def issue(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        scopes: list[str] | tuple[str, ...],
        token_type: str,
        ttl_seconds: int,
    ) -> dict[str, Any]:
        now = int(time.time())
        ttl = max(60, min(int(ttl_seconds), 60 * 60 * 24 * 30))
        claims = {
            "iss": self.issuer,
            "aud": self.audience,
            "sub": actor_id,
            "tenantId": tenant_id,
            "scopes": sorted(set(scopes)),
            "type": token_type,
            "jti": f"tok_{uuid4().hex}",
            "iat": now,
            "nbf": now,
            "exp": now + ttl,
        }
        header = {"alg": "HS256", "typ": "JWT"}
        encoded_header = _b64encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode())
        encoded_claims = _b64encode(json.dumps(claims, separators=(",", ":"), sort_keys=True).encode())
        signing_input = f"{encoded_header}.{encoded_claims}".encode("ascii")
        signature = _b64encode(hmac.new(self._secret, signing_input, hashlib.sha256).digest())
        return {"accessToken": f"{encoded_header}.{encoded_claims}.{signature}", "tokenType": "Bearer", "expiresAt": claims["exp"], "tokenId": claims["jti"], "scopes": claims["scopes"]}

    def verify(self, token: str) -> Principal:
        try:
            encoded_header, encoded_claims, encoded_signature = token.split(".")
            signing_input = f"{encoded_header}.{encoded_claims}".encode("ascii")
            expected = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
            provided = _b64decode(encoded_signature)
            if not hmac.compare_digest(expected, provided):
                raise AuthenticationRequired("invalid token signature")
            header = json.loads(_b64decode(encoded_header))
            claims = json.loads(_b64decode(encoded_claims))
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise AuthenticationRequired("invalid bearer token") from exc
        if header != {"alg": "HS256", "typ": "JWT"}:
            raise AuthenticationRequired("unsupported token header")
        now = int(time.time())
        if claims.get("iss") != self.issuer or claims.get("aud") != self.audience:
            raise AuthenticationRequired("token issuer or audience is invalid")
        if int(claims.get("nbf", 0)) > now + self.clock_skew_seconds:
            raise AuthenticationRequired("token is not active")
        if int(claims.get("exp", 0)) <= now - self.clock_skew_seconds:
            raise AuthenticationRequired("token has expired")
        token_id = str(claims.get("jti", ""))
        if not token_id or self.revocations.is_revoked(token_id):
            raise AuthenticationRequired("token has been revoked")
        tenant_id = str(claims.get("tenantId", ""))
        actor_id = str(claims.get("sub", ""))
        scopes = claims.get("scopes", [])
        if not tenant_id or not actor_id or not isinstance(scopes, list):
            raise AuthenticationRequired("token claims are incomplete")
        return Principal(
            tenant_id=tenant_id,
            actor_id=actor_id,
            scopes=tuple(str(scope) for scope in scopes),
            token_id=token_id,
            token_type=str(claims.get("type", "service")),
            issued_at=int(claims.get("iat", 0)),
            expires_at=int(claims["exp"]),
        )

    def revoke(self, token: str) -> str:
        principal = self.verify(token)
        self.revocations.revoke(principal.token_id, principal.expires_at)
        return principal.token_id


class AuthService:
    """Owner login, session issuance, service-token issuance, and verification."""

    DEFAULT_SCOPES = (
        "project:read", "project:write", "timeline:read", "timeline:write",
        "icm:read", "icm:write", "prompt:compile", "provider:read",
        "provider:execute", "budget:spend", "asset:read", "asset:write",
        "job:read", "job:write", "render:read", "render:write",
    )

    def __init__(
        self,
        *,
        mode: str,
        signing_secret_env: str,
        owner_username: str,
        owner_password_env: str,
        owner_tenant_id: str,
        session_ttl_seconds: int,
        service_ttl_seconds: int,
        revocations: RevocationStore | None = None,
    ) -> None:
        self.mode = mode
        self.owner_username = owner_username
        self.owner_password_env = owner_password_env
        self.owner_tenant_id = owner_tenant_id
        self.session_ttl_seconds = session_ttl_seconds
        self.service_ttl_seconds = service_ttl_seconds
        secret = os.environ.get(signing_secret_env)
        self.tokens = SignedTokenService(secret=secret, revocations=revocations) if secret else None

    @property
    def configured(self) -> bool:
        if self.mode == "local":
            return True
        return self.tokens is not None and bool(os.environ.get(self.owner_password_env))

    def login(self, username: str, password: str) -> dict[str, Any]:
        if self.mode != "hosted" or not self.tokens:
            raise AuthConfigurationError("hosted authentication is not configured")
        expected = os.environ.get(self.owner_password_env)
        if not expected or not hmac.compare_digest(username, self.owner_username) or not hmac.compare_digest(password, expected):
            raise AuthenticationRequired("invalid credentials")
        return self.tokens.issue(
            tenant_id=self.owner_tenant_id,
            actor_id=f"user:{self.owner_username}",
            scopes=self.DEFAULT_SCOPES,
            token_type="session",
            ttl_seconds=self.session_ttl_seconds,
        )

    def verify_bearer(self, authorization: str | None) -> Principal:
        if not authorization or not authorization.startswith("Bearer "):
            raise AuthenticationRequired("bearer token is required")
        if not self.tokens:
            raise AuthConfigurationError("hosted authentication is not configured")
        return self.tokens.verify(authorization[7:].strip())

    def issue_service_token(self, principal: Principal, *, name: str, scopes: list[str], ttl_seconds: int | None = None) -> dict[str, Any]:
        if principal.token_type not in {"session", "service"}:
            raise AuthorizationDenied("principal cannot create service tokens")
        requested = set(scopes)
        if not requested or not requested.issubset(principal.scopes):
            raise AuthorizationDenied("service-token scopes must be a non-empty subset of caller scopes")
        if not self.tokens:
            raise AuthConfigurationError("hosted authentication is not configured")
        return self.tokens.issue(
            tenant_id=principal.tenant_id,
            actor_id=f"service:{name}",
            scopes=sorted(requested),
            token_type="service",
            ttl_seconds=ttl_seconds or self.service_ttl_seconds,
        )

    def revoke(self, token: str) -> str:
        if not self.tokens:
            raise AuthConfigurationError("hosted authentication is not configured")
        return self.tokens.revoke(token)
