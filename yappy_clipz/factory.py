"""Application-service composition root shared by all transports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .actions import ActionDispatcher
from .capabilities import CapabilityRegistry, default_registry
from .prompt_locker import PromptLocker
from .icm_runtime import IcmRuntime
from .providers import FalProviderAdapter, FalSettings, ProviderCatalog
from .repository import FileProjectRepository
from .service import StudioService
from .settings import Settings


@dataclass(frozen=True, slots=True)
class ApplicationRuntime:
    """Fully composed owner-controlled runtime shared by every transport."""

    settings: Settings
    service: StudioService
    capabilities: CapabilityRegistry
    prompt_locker: PromptLocker
    provider_catalog: ProviderCatalog
    icm: IcmRuntime
    fal: FalProviderAdapter
    dispatcher: ActionDispatcher


def create_service(settings: Settings | None = None) -> StudioService:
    """Construct the default owner-controlled StudioService."""
    resolved = settings or Settings.from_env()
    return StudioService(FileProjectRepository(resolved.project_root))


def create_runtime(
    settings: Settings | None = None,
    *,
    service: StudioService | None = None,
    http_client: Any | None = None,
) -> ApplicationRuntime:
    """Create one registry/dispatcher composition shared by CLI, API, and MCP."""
    resolved = settings or Settings.from_env()
    active_service = service or create_service(resolved)
    capabilities = default_registry()
    prompt_locker = PromptLocker(resolved.resolved_prompt_root)
    provider_catalog = ProviderCatalog(resolved.resolved_provider_root)
    icm = IcmRuntime(resolved.resolved_icm_runtime_root)
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
    dispatcher = ActionDispatcher(
        service=active_service,
        registry=capabilities,
        prompt_locker=prompt_locker,
        provider_catalog=provider_catalog,
        fal=fal,
        icm=icm,
    )
    return ApplicationRuntime(
        settings=resolved,
        service=active_service,
        capabilities=capabilities,
        prompt_locker=prompt_locker,
        provider_catalog=provider_catalog,
        fal=fal,
        icm=icm,
        dispatcher=dispatcher,
    )
