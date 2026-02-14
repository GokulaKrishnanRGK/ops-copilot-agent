type WebEnv = ImportMetaEnv & {
  readonly WEB_API_BASE_URL?: string;
  readonly WEB_STREAMING_ENDPOINT?: string;
};

const env = import.meta.env as WebEnv;

function normalizeBaseUrl(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) {
    return "/api";
  }
  return trimmed.endsWith("/") ? trimmed.slice(0, -1) : trimmed;
}

function normalizePath(value: string, fallback: string): string {
  const trimmed = value.trim();
  if (!trimmed) {
    return fallback;
  }
  return trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
}

export const webConfig = {
  apiBaseUrl: normalizeBaseUrl(env.WEB_API_BASE_URL ?? "/api"),
  streamingEndpoint: normalizePath(env.WEB_STREAMING_ENDPOINT ?? "/chat/stream", "/chat/stream"),
};

export function buildApiUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${webConfig.apiBaseUrl}${normalizedPath}`;
}
