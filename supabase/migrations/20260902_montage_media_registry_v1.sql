-- Canonical registry for protected Google Drive / OneDrive / local media.
create extension if not exists pgcrypto;

create table if not exists public.montage_media_assets (
  id uuid primary key default gen_random_uuid(), canonical_key text not null unique,
  filename text not null, extension text, mime_type text, size_bytes bigint, sha256 text,
  duration_seconds numeric, width integer, height integer, fps numeric, video_codec text, audio_codec text,
  capture_at timestamptz, people text[] not null default '{}', locations text[] not null default '{}', tags text[] not null default '{}',
  visual_description text,
  verification_status text not null default 'discovered' check (verification_status in ('discovered','metadata_verified','download_verified','proxy_verified','missing','orphan_reference')),
  master_protected boolean not null default true,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);

create table if not exists public.montage_media_locations (
  id uuid primary key default gen_random_uuid(), asset_id uuid not null references public.montage_media_assets(id) on delete cascade,
  provider text not null check (provider in ('google_drive','onedrive','local')), provider_file_id text not null,
  provider_drive_id text, provider_path text, web_url text, etag text, provider_modified_at timestamptz, downloadable boolean,
  metadata jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique(provider,provider_file_id)
);

create table if not exists public.montage_media_derivatives (
  id uuid primary key default gen_random_uuid(), asset_id uuid not null references public.montage_media_assets(id) on delete cascade,
  kind text not null check (kind in ('protected_copy','proxy','thumbnail','audio_extract','render','export')),
  local_path text, storage_url text, sha256 text, metadata jsonb not null default '{}'::jsonb, created_at timestamptz not null default now()
);

create table if not exists public.montage_media_transcripts (
  id uuid primary key default gen_random_uuid(), asset_id uuid not null references public.montage_media_assets(id) on delete cascade,
  language text, model text, transcript text, segments jsonb not null default '[]'::jsonb, created_at timestamptz not null default now()
);

create table if not exists public.montage_media_project_refs (
  id uuid primary key default gen_random_uuid(), asset_id uuid references public.montage_media_assets(id) on delete set null,
  project_type text not null, project_name text, project_provider text, project_file_id text,
  referenced_filename text, referenced_sha256 text, referenced_size_bytes bigint, metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.montage_media_ingest_runs (
  id uuid primary key default gen_random_uuid(), provider text not null check (provider in ('google_drive','onedrive','local')),
  status text not null default 'running' check (status in ('running','completed','failed','partial')),
  scanned_items integer not null default 0, assets_upserted integer not null default 0, error_count integer not null default 0,
  cursor text, summary jsonb not null default '{}'::jsonb, started_at timestamptz not null default now(), completed_at timestamptz
);

create index if not exists montage_media_assets_sha256_idx on public.montage_media_assets(sha256) where sha256 is not null;
create index if not exists montage_media_assets_filename_idx on public.montage_media_assets(lower(filename));
create index if not exists montage_media_locations_asset_idx on public.montage_media_locations(asset_id);
create index if not exists montage_media_locations_provider_idx on public.montage_media_locations(provider,provider_file_id);

alter table public.montage_media_assets enable row level security;
alter table public.montage_media_locations enable row level security;
alter table public.montage_media_derivatives enable row level security;
alter table public.montage_media_transcripts enable row level security;
alter table public.montage_media_project_refs enable row level security;
alter table public.montage_media_ingest_runs enable row level security;

revoke all on public.montage_media_assets, public.montage_media_locations, public.montage_media_derivatives,
  public.montage_media_transcripts, public.montage_media_project_refs, public.montage_media_ingest_runs from anon, authenticated;
grant select,insert,update,delete on public.montage_media_assets, public.montage_media_locations, public.montage_media_derivatives,
  public.montage_media_transcripts, public.montage_media_project_refs, public.montage_media_ingest_runs to service_role;
