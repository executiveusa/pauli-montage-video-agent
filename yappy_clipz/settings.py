"""Runtime settings for YAPPY-CLIPZ application services."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try: value = int(os.environ.get(name, str(default)))
    except ValueError: value = default
    return max(minimum, min(value, maximum))


@dataclass(frozen=True, slots=True)
class Settings:
    project_root: Path
    prompt_root: Path | None = None
    provider_root: Path | None = None
    icm_runtime_root: Path | None = None
    fal_execution_enabled: bool = False
    fal_store_io: bool = False
    fal_queue_base_url: str = "https://queue.fal.run"
    fal_key_env: str = "FAL_KEY"
    fal_timeout_seconds: float = 30.0
    repository_backend: str = "file"
    database_url: str | None = None
    auth_mode: str = "local"
    auth_signing_secret_env: str = "YAPPY_AUTH_SIGNING_SECRET"
    auth_owner_username: str = "owner"
    auth_owner_password_env: str = "YAPPY_OWNER_PASSWORD"
    auth_owner_tenant_id: str = "tenant_owner"
    auth_session_ttl_seconds: int = 28_800
    auth_service_ttl_seconds: int = 2_592_000
    cors_origins: tuple[str, ...] = ()
    storage_backend: str = "local"
    storage_root: Path | None = None
    storage_bucket: str | None = None
    storage_region: str = "us-east-1"
    storage_endpoint_url: str | None = None
    storage_signing_secret_env: str = "YAPPY_STORAGE_SIGNING_SECRET"
    storage_transfer_ttl_seconds: int = 900
    max_upload_bytes: int = 2_147_483_648
    account_store_path: Path | None = None
    recovery_delivery: str = "disabled"
    recovery_outbox_path: Path | None = None
    recovery_reset_base_url: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_sender: str | None = None
    smtp_username: str | None = None
    smtp_password_env: str = "YAPPY_SMTP_PASSWORD"
    smtp_tls: bool = True

    @property
    def resolved_prompt_root(self) -> Path:
        return (self.prompt_root or Path(__file__).resolve().parents[1] / "prompt_locker").expanduser().resolve()
    @property
    def resolved_icm_runtime_root(self) -> Path:
        return (self.icm_runtime_root or self.project_root.parent / "icm-runtime").expanduser().resolve()
    @property
    def resolved_provider_root(self) -> Path:
        return (self.provider_root or Path(__file__).resolve().parents[1] / "providers").expanduser().resolve()
    @property
    def resolved_storage_root(self) -> Path:
        return (self.storage_root or self.project_root.parent / "objects").expanduser().resolve()
    @property
    def resolved_account_store_path(self) -> Path:
        return (self.account_store_path or self.project_root.parent / "accounts.json").expanduser().resolve()
    @property
    def resolved_recovery_outbox_path(self) -> Path:
        return (self.recovery_outbox_path or self.project_root.parent / "recovery-outbox").expanduser().resolve()

    @classmethod
    def from_env(cls) -> "Settings":
        configured = os.environ.get("YAPPY_PROJECT_ROOT", ".yappy-clipz/data")
        prompt_root = os.environ.get("YAPPY_PROMPT_ROOT"); provider_root = os.environ.get("YAPPY_PROVIDER_ROOT"); icm_runtime_root = os.environ.get("YAPPY_ICM_RUNTIME_ROOT")
        try: timeout_seconds = float(os.environ.get("YAPPY_FAL_TIMEOUT_SECONDS", "30"))
        except ValueError: timeout_seconds = 30.0
        backend = os.environ.get("YAPPY_REPOSITORY_BACKEND", "file").strip().lower()
        if backend not in {"file", "postgres"}: backend = "file"
        auth_mode = os.environ.get("YAPPY_AUTH_MODE", "local").strip().lower()
        if auth_mode not in {"local", "hosted"}: auth_mode = "local"
        storage_backend = os.environ.get("YAPPY_STORAGE_BACKEND", "local").strip().lower()
        if storage_backend not in {"local", "s3"}: storage_backend = "local"
        storage_root = os.environ.get("YAPPY_STORAGE_ROOT")
        account_store_path = os.environ.get("YAPPY_ACCOUNT_STORE_PATH")
        recovery_delivery = os.environ.get("YAPPY_RECOVERY_DELIVERY", "disabled").strip().lower()
        if recovery_delivery not in {"disabled", "file", "smtp"}: recovery_delivery = "disabled"
        origins = tuple(value.strip() for value in os.environ.get("YAPPY_CORS_ORIGINS", "").split(",") if value.strip())
        return cls(
            project_root=Path(configured).expanduser().resolve(),
            prompt_root=Path(prompt_root).expanduser().resolve() if prompt_root else None,
            provider_root=Path(provider_root).expanduser().resolve() if provider_root else None,
            icm_runtime_root=Path(icm_runtime_root).expanduser().resolve() if icm_runtime_root else None,
            fal_execution_enabled=_env_bool("YAPPY_ENABLE_PAID_PROVIDERS", False),fal_store_io=_env_bool("YAPPY_FAL_STORE_IO", False),
            fal_queue_base_url=os.environ.get("YAPPY_FAL_QUEUE_BASE_URL", "https://queue.fal.run"),fal_key_env=os.environ.get("YAPPY_FAL_KEY_ENV", "FAL_KEY"),fal_timeout_seconds=max(1.0,min(timeout_seconds,300.0)),
            repository_backend=backend,database_url=os.environ.get("YAPPY_DATABASE_URL"),auth_mode=auth_mode,
            auth_signing_secret_env=os.environ.get("YAPPY_AUTH_SIGNING_SECRET_ENV", "YAPPY_AUTH_SIGNING_SECRET"),auth_owner_username=os.environ.get("YAPPY_OWNER_USERNAME", "owner"),
            auth_owner_password_env=os.environ.get("YAPPY_OWNER_PASSWORD_ENV", "YAPPY_OWNER_PASSWORD"),auth_owner_tenant_id=os.environ.get("YAPPY_OWNER_TENANT_ID", "tenant_owner"),
            auth_session_ttl_seconds=_env_int("YAPPY_SESSION_TTL_SECONDS",28_800,300,2_592_000),auth_service_ttl_seconds=_env_int("YAPPY_SERVICE_TOKEN_TTL_SECONDS",2_592_000,300,2_592_000),cors_origins=origins,
            storage_backend=storage_backend,storage_root=Path(storage_root).expanduser().resolve() if storage_root else None,storage_bucket=os.environ.get("YAPPY_STORAGE_BUCKET"),
            storage_region=os.environ.get("YAPPY_STORAGE_REGION","us-east-1"),storage_endpoint_url=os.environ.get("YAPPY_STORAGE_ENDPOINT_URL"),
            storage_signing_secret_env=os.environ.get("YAPPY_STORAGE_SIGNING_SECRET_ENV","YAPPY_STORAGE_SIGNING_SECRET"),storage_transfer_ttl_seconds=_env_int("YAPPY_STORAGE_TRANSFER_TTL_SECONDS",900,60,3600),
            max_upload_bytes=_env_int("YAPPY_MAX_UPLOAD_BYTES",2_147_483_648,1,10_737_418_240),
            account_store_path=Path(account_store_path).expanduser().resolve() if account_store_path else None,
            recovery_delivery=recovery_delivery,recovery_outbox_path=Path(os.environ["YAPPY_RECOVERY_OUTBOX_PATH"]).expanduser().resolve() if os.environ.get("YAPPY_RECOVERY_OUTBOX_PATH") else None,
            recovery_reset_base_url=os.environ.get("YAPPY_RECOVERY_RESET_BASE_URL"),smtp_host=os.environ.get("YAPPY_SMTP_HOST"),smtp_port=_env_int("YAPPY_SMTP_PORT",587,1,65535),
            smtp_sender=os.environ.get("YAPPY_SMTP_SENDER"),smtp_username=os.environ.get("YAPPY_SMTP_USERNAME"),smtp_password_env=os.environ.get("YAPPY_SMTP_PASSWORD_ENV","YAPPY_SMTP_PASSWORD"),smtp_tls=_env_bool("YAPPY_SMTP_TLS",True),
        )
