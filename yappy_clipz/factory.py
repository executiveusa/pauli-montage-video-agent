"""Application-service composition root shared by all transports."""
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Any
from .assets import AssetService
from .accounts import AccountService,FileRecoveryDelivery,JsonAccountStore,PostgresAccountStore,SmtpRecoveryDelivery
from .auth import AuthService,MemoryRevocationStore
from .capabilities import CapabilityRegistry,default_registry
from .costing import BudgetedOperationsService
from .generation import GenerationService
from .generation_actions import GenerationCapabilityRegistry
from .hosted_actions import HostedCapabilityRegistry
from .icm_runtime import IcmRuntime
from .onedrive import JsonSourceConnectionStore,OneDriveService,PostgresSourceConnectionStore,SecretCipher
from .operations import JsonOperationStore,PostgresOperationStore
from .operations_actions import OperationsCapabilityRegistry
from .postgres_auth import PostgresRevocationStore
from .postgres_repository import PostgresProjectRepository
from .prompt_locker import PromptLocker
from .providers import FalSettings,ProviderCatalog
from .providers.fal_extended import ExtendedFalProviderAdapter
from .render_actions import RenderActionDispatcher,RenderCapabilityRegistry
from .rendering import RenderService
from .repository import FileProjectRepository,ProjectRepository
from .router import OmniRouter
from .service import StudioService
from .settings import Settings
from .storage import LocalObjectStorage,ObjectStorage,S3ObjectStorage,StorageNotConfigured,TransferSigner

@dataclass(frozen=True,slots=True)
class ApplicationRuntime:
 settings:Settings;service:StudioService;capabilities:CapabilityRegistry;prompt_locker:PromptLocker;provider_catalog:ProviderCatalog;icm:IcmRuntime;fal:ExtendedFalProviderAdapter;auth:AuthService;accounts:AccountService;storage:ObjectStorage;assets:AssetService;sources:OneDriveService;operations:BudgetedOperationsService;router:OmniRouter;generation:GenerationService;rendering:RenderService;dispatcher:RenderActionDispatcher

def create_repository(settings:Settings)->ProjectRepository:return PostgresProjectRepository(settings.database_url or "") if settings.repository_backend=="postgres" else FileProjectRepository(settings.project_root)
def create_storage(settings:Settings)->ObjectStorage:return S3ObjectStorage(bucket=settings.storage_bucket or "",region=settings.storage_region,endpoint_url=settings.storage_endpoint_url) if settings.storage_backend=="s3" else LocalObjectStorage(settings.resolved_storage_root)
def create_service(settings:Settings|None=None)->StudioService:
 resolved=settings or Settings.from_env();return StudioService(create_repository(resolved))
def create_runtime(settings:Settings|None=None,*,service:StudioService|None=None,http_client:Any|None=None,render_runner:Any|None=None)->ApplicationRuntime:
 resolved=settings or Settings.from_env();active_service=service or create_service(resolved);capabilities=RenderCapabilityRegistry(GenerationCapabilityRegistry(OperationsCapabilityRegistry(HostedCapabilityRegistry(default_registry()))));prompt_locker=PromptLocker(resolved.resolved_prompt_root);provider_catalog=ProviderCatalog(resolved.resolved_provider_root);icm=IcmRuntime(resolved.resolved_icm_runtime_root)
 revocations=PostgresRevocationStore(resolved.database_url) if resolved.repository_backend=="postgres" and resolved.database_url else MemoryRevocationStore();auth=AuthService(mode=resolved.auth_mode,signing_secret_env=resolved.auth_signing_secret_env,owner_username=resolved.auth_owner_username,owner_password_env=resolved.auth_owner_password_env,owner_tenant_id=resolved.auth_owner_tenant_id,session_ttl_seconds=resolved.auth_session_ttl_seconds,service_ttl_seconds=resolved.auth_service_ttl_seconds,revocations=revocations)
 account_store=PostgresAccountStore(resolved.database_url or "") if resolved.repository_backend=="postgres" else JsonAccountStore(resolved.resolved_account_store_path)
 recovery_delivery=None
 if resolved.recovery_delivery=="file": recovery_delivery=FileRecoveryDelivery(resolved.resolved_recovery_outbox_path)
 elif resolved.recovery_delivery=="smtp": recovery_delivery=SmtpRecoveryDelivery(host=resolved.smtp_host or "",port=resolved.smtp_port,sender=resolved.smtp_sender or "",reset_base_url=resolved.recovery_reset_base_url or "",username=resolved.smtp_username,password=os.environ.get(resolved.smtp_password_env),use_tls=resolved.smtp_tls)
 accounts=AccountService(account_store,auth.tokens,session_ttl_seconds=resolved.auth_session_ttl_seconds,recovery_delivery=recovery_delivery);auth.configure_accounts(accounts)
 fal=ExtendedFalProviderAdapter(provider_catalog,FalSettings(queue_base_url=resolved.fal_queue_base_url,key_env=resolved.fal_key_env,execution_enabled=resolved.fal_execution_enabled,store_io=resolved.fal_store_io,timeout_seconds=resolved.fal_timeout_seconds),http_client=http_client);storage=create_storage(resolved)
 signing_secret=os.environ.get(resolved.storage_signing_secret_env) or os.environ.get(resolved.auth_signing_secret_env)
 if not signing_secret:
  if resolved.auth_mode=="hosted":raise StorageNotConfigured("hosted storage signing secret is not configured")
  signing_secret="local-owner-development-storage-signing-secret-0001"
 assets=AssetService(active_service.repository,storage,TransferSigner(signing_secret,ttl_seconds=resolved.storage_transfer_ttl_seconds),max_upload_bytes=resolved.max_upload_bytes)
 source_store=PostgresSourceConnectionStore(resolved.database_url or "") if resolved.repository_backend=="postgres" else JsonSourceConnectionStore(resolved.resolved_source_store_path)
 source_cipher=SecretCipher(os.environ.get(resolved.source_token_encryption_secret_env))
 sources=OneDriveService(store=source_store,cipher=source_cipher,client_id=resolved.microsoft_client_id,client_secret=os.environ.get(resolved.microsoft_client_secret_env),redirect_uri=resolved.microsoft_redirect_uri,oauth_tenant=resolved.microsoft_oauth_tenant,http_client=http_client)
 operation_store=PostgresOperationStore(resolved.database_url) if resolved.repository_backend=="postgres" and resolved.database_url else JsonOperationStore(resolved.project_root.parent/"operations.json");operations=BudgetedOperationsService(operation_store);router=OmniRouter(provider_catalog);generation=GenerationService(repository=active_service.repository,catalog=provider_catalog,router=router,operations=operations,prompts=prompt_locker,fal=fal)
 rendering=RenderService(repository=active_service.repository,storage=storage,assets=assets,operations=operations,runner=render_runner,ffmpeg_binary=os.environ.get("YAPPY_FFMPEG_BINARY","ffmpeg"),ffprobe_binary=os.environ.get("YAPPY_FFPROBE_BINARY","ffprobe"),workspace_root=resolved.project_root.parent/"renders")
 dispatcher=RenderActionDispatcher(service=active_service,registry=capabilities,prompt_locker=prompt_locker,provider_catalog=provider_catalog,fal=fal,icm=icm,auth=auth,assets=assets,sources=sources,operations=operations,router=router,generation=generation,rendering=rendering)
 return ApplicationRuntime(settings=resolved,service=active_service,capabilities=capabilities,prompt_locker=prompt_locker,provider_catalog=provider_catalog,fal=fal,icm=icm,auth=auth,accounts=accounts,storage=storage,assets=assets,sources=sources,operations=operations,router=router,generation=generation,rendering=rendering,dispatcher=dispatcher)
