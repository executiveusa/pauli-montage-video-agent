"""Application-service composition root shared by all transports."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .auth import AuthService, MemoryRevocationStore
from .capabilities import CapabilityRegistry, default_registry
from .hosted_actions import HostedActionDispatcher, HostedCapabilityRegistry
from .icm_runtime import IcmRuntime
from .postgres_auth import PostgresRevocationStore
from .postgres_repository import PostgresProjectRepository
from .prompt_locker import PromptLocker
from .providers import FalProviderAdapter, FalSettings, ProviderCatalog
from .repository import FileProjectRepository, ProjectRepository
from .service import StudioService
from .settings import Settings


@dataclass(frozen=True, slots=True)
class ApplicationRuntime:
    settings: Settings
    service: StudioService
    capabilities: CapabilityRegistry
    prompt_locker: PromptLocker
    provider_catalog: ProviderCatalog
    icm: IcmRuntime
    fal: FalProviderAdapter
    auth: AuthService
    dispatcher: HostedActionDispatcher


def create_repository(settings: Settings) -> ProjectRepository:
    if settings.repository_backend == "postgres":
        return PostgresProjectRepository(settings.database_url or "")
    return FileProjectRepository(settings.project_root)


def create_service(settings: Settings | None = None) -> StudioService:
    resolved = settings or Settings.from_env()
    return StudioService(create_repository(resolved))


def create_runtime(
    settings: Settings | None = None,
    *,
    service: StudioService | None = None,
    http_client: Any | None = None,
) -> ApplicationRuntime:
    resolved = settings or Settings.from_env()
    active_service = service or create_service(resolved)
    base_capabilities = default_registry()
    capabilities = HostedCapabilityRegistry(base_capabilities)
    prompt_locker = PromptLocker(resolved.resolved_prompt_root)
    provider_catalog = ProviderCatalog(resolved.resolved_provider_root)
    icm = IcmRuntime(resolved.resolved_icm_runtime_root)
    revocations = (
        PostgresRevocationStore(resolved.database_url)
        if resolved.repository_backend == "postgres" and resolved.database_url
        else MemoryRevocationStore()
    )
    auth = AuthService(
        mode=resolved.auth_mode,
        signing_secret_env=resolved.auth_signing_secret_env,
        owner_username=resolved.auth_owner_username,
        owner_password_env=resolved.auth_owner_password_env,
        owner_tenant_id=resolved.auth_owner_tenant_id,
        session_ttl_seconds=resolved.auth_session_ttl_seconds,
        service_ttl_seconds=resolved.auth_service_ttl_seconds,
        revocations=revocations,
    )
    fal = FalProviderAdapter(
        provider_catalog,
        FalSettings(
            queue_base_url=resolved.fal_queue_base_url,
            key_env=resolved.fal_key_env,
            execution_enabled=resolved.fal_execution_enabled,
            store_io=resolved.fal_store_io,
            timeout_seconds=resolved.fal_timeout_seconds,
        ),
        http_client=http_client,
    )
    dispatcher = HostedActionDispatcher(
        service=active_service,
        registry=capabilities,
        prompt_locker=prompt_locker,
        provider_catalog=provider_catalog,
        fal=fal,
        icm=icm,
        auth=auth,
    )
    return ApplicationRuntime(
        settings=resolved,
        service=active_service,
        capabilities=capabilities,
        prompt_locker=prompt_locker,
        provider_catalog=provider_catalog,
        fal=fal,
        icm=icm,
        auth=auth,
        dispatcher=dispatcher,
    )
