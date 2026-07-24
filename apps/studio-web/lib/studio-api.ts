export type ProjectSummary = {
  schemaVersion: string;
  id: string;
  tenantId: string;
  slug: string;
  title: string;
  status: string;
  updatedAt: string;
};

export type CreateProjectInput = {
  slug: string;
  title: string;
  objective: string;
  deliverables: string[];
  audience?: string[];
  constraints?: string[];
  quality_lane?: "economy" | "premium" | "sovereign" | "owner_private";
};

export type ServiceError = {
  error: string;
  message: string;
  configured: boolean;
};

export function studioApiBaseUrl(): string | null {
  const value = process.env.YAPPY_STUDIO_API_URL?.trim();
  return value ? value.replace(/\/$/, "") : null;
}

export function defaultTenant(): string {
  return process.env.YAPPY_DEFAULT_TENANT?.trim() || "owner-studio";
}
