"""Application-service composition root shared by all transports."""

from __future__ import annotations

from .repository import FileProjectRepository
from .service import StudioService
from .settings import Settings


def create_service(settings: Settings | None = None) -> StudioService:
    """Construct the default owner-controlled StudioService."""
    resolved = settings or Settings.from_env()
    return StudioService(FileProjectRepository(resolved.project_root))
