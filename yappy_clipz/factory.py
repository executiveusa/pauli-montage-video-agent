"""Application-service composition root shared by all transports."""
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Any
from .assets import AssetService
from .auth import AuthService,MemoryRevocationStore
from .capabilities import CapabilityRegistry,default_registry
from .costing import BudgetedOperationsService
from .hosted_actions import HostedCapabilityRegistry
from .icm_runtime import IcmRuntime
from .operations import JsonOperationStore,PostgresOperationStore
from .operations_actions import OperationsActionDispatcher,OperationsCapabilityRegistry
from .postgres_auth import PostgresRevocationStore
from .postgres_repository import PostgresProjectRepository
from .prompt_locker import PromptLocker
from .providers import FalProviderAdapter,FalSettings,ProviderCatalog
from .repository import FileProjectRepository,ProjectRepository
from .router import OmniRouter
from .service import StudioService
from .settings import Settings
from .storage import LocalObjectStorage,ObjectStorage,S3ObjectStorage,StorageNotConfigured,TransferSigner

@dataclass(frozen=True,slots=True)
class ApplicationRuntime:
 settings:Settings;service:StudioService;capabilities:CapabilityRegistry;prompt_locker:PromptLocker;provider_catalog:ProviderCatalog;icm:IcmRuntime;fal:FalProviderAdapter;auth:AuthService;storage:ObjectStorage;assets:AssetService;operations:BudgetedOperationsService;router:OmniRouter;dispatcher:OperationsActionDispatcher

def create_repository(settings:Settings)->ProjectRepository:return PostgresProjectRepository(settings.database_url or "") if settings.repository_backend=="postgres" else FileProjectRepository(settings.project_root)
def create_storage(settings:Settings)->ObjectStorage:return S3ObjectStorage(bucket=settings.storage_bucket or "",region=settings.storage_region,endpoint_url=settings.storage_endpoint_url) if settings.storage_backend=="s3" else LocalObjectStorage(settings.resolved_storage_root)
def create_service(settings:Settings|None=None)->StudioService:
 resolved=settings or Settings.from_env();return StudioService(create_repository(resolved))
def create_runtime(settings:Settings|None=None,*,service:StudioService|None=None,http_client:Any|None=None)->ApplicationRuntime:
 resolved=settings or Settings.from_env();active_service=service or create_service(resolved);capabilities=OperationsCapabilityRegistry(HostedCapabilityRegistry(default_registry()));prompt_locker=PromptLocker(resolved.resolved_prompt_root);provider_catalog=ProviderCatalog(resolved.resolved_provider_root);icm=IcmRuntime(resolved.resolved_icm_runtime_root)
 revocations=PostgresRevocationStore(resolved.database_url) if resolved.repository_backend=="postgres" and resolved.database_url else MemoryRevocationStore();auth=AuthService(mode=resolved.auth_mode,signing_secret_env=resolved.auth_signing_secret_env,owner_username=resolved.auth_owner_username,owner_password_env=resolved.auth_owner_password_env,owner_tenant_id=resolved.auth_owner_tenant_id,session_ttl_seconds=resolved.auth_session_ttl_seconds,service_ttl_seconds=resolved.auth_service_ttl_seconds,revocations=revocations)
 fal=FalProviderAdapter(provider_catalog,FalSettings(queue_base_url=resolved.fal_queue_base_url,key_env=resolved.fal_key_env,execution_enabled=resolved.fal_execution_enabled,store_io=resolved.fal_store_io,timeout_seconds=resolved.fal_timeout_seconds),http_client=http_client);storage=create_storage(resolved)
 signing_secret=os.environ.get(resolved.storage_signing_secret_env) or os.environ.get(resolved.auth_signing_secret_env)
 if not signing_secret:
  if resolved.auth_mode=="hosted":raise StorageNotConfigured("hosted storage signing secret is not configured")
  signing_secret="local-owner-development-storage-signing-secret-0001"
 assets=AssetService(active_service.repository,storage,TransferSigner(signing_secret,ttl_seconds=resolved.storage_transfer_ttl_seconds),max_upload_bytes=resolved.max_upload_bytes)
 operation_store=PostgresOperationStore(resolved.database_url) if resolved.repository_backend=="postgres" and resolved.database_url else JsonOperationStore(resolved.project_root.parent/"operations.json");operations=BudgetedOperationsService(operation_store);router=OmniRouter(provider_catalog)
 dispatcher=OperationsActionDispatcher(service=active_service,registry=capabilities,prompt_locker=prompt_locker,provider_catalog=provider_catalog,fal=fal,icm=icm,auth=auth,assets=assets,operations=operations,router=router)
 return ApplicationRuntime(settings=resolved,service=active_service,capabilities=capabilities,prompt_locker=prompt_locker,provider_catalog=provider_catalog,fal=fal,icm=icm,auth=auth,storage=storage,assets=assets,operations=operations,router=router,dispatcher=dispatcher)
