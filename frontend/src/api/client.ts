import { ApiError } from "./errors";
import type { ApiErrorResponse, ApiSuccess } from "./types";
import { normalizeApiBaseUrl, resolveTrustedApiUrl } from "./trusted-url";
import { clearSessionToken, getSessionToken } from "../features/auth/session";

type JsonBody = object;

export interface ApiRequestInit extends Omit<RequestInit, "body"> {
  body?: BodyInit | JsonBody | null;
}

export interface ApiFileRequestInit extends Omit<RequestInit, "body"> {
  fallbackFilename?: string;
}

export interface ApiFileResponse {
  blob: Blob;
  filename: string | null;
}

const apiBaseUrl = normalizeApiBaseUrl(import.meta.env.VITE_API_BASE_URL);

function buildUrl(path: string): string {
  return resolveTrustedApiUrl(path, apiBaseUrl);
}

function toHeaderRecord(headers?: HeadersInit): Record<string, string> {
  if (!headers) {
    return {};
  }

  if (headers instanceof Headers) {
    const record: Record<string, string> = {};
    headers.forEach((value, key) => {
      record[key] = value;
    });
    return record;
  }

  if (Array.isArray(headers)) {
    return Object.fromEntries(headers);
  }

  return { ...headers };
}

function isJsonBody(body: ApiRequestInit["body"]): body is JsonBody {
  if (body === null || body === undefined || typeof body !== "object") {
    return false;
  }

  return !(
    body instanceof FormData ||
    body instanceof Blob ||
    body instanceof ArrayBuffer ||
    body instanceof URLSearchParams
  );
}

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text();

  if (!text) {
    return undefined;
  }

  return JSON.parse(text) as unknown;
}

function isApiErrorResponse(payload: unknown): payload is ApiErrorResponse {
  return (
    typeof payload === "object" &&
    payload !== null &&
    "error" in payload &&
    typeof (payload as ApiErrorResponse).error?.code === "string"
  );
}

function isApiSuccess<T>(payload: unknown): payload is ApiSuccess<T> {
  return typeof payload === "object" && payload !== null && "data" in payload;
}

function filenameFromDisposition(disposition: string | null, fallback: string | undefined): string | null {
  if (!disposition) {
    return fallback ?? null;
  }

  const utf8Match = /filename\*=UTF-8''([^;]+)/i.exec(disposition);
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1].trim().replace(/^"|"$/g, ""));
  }

  const asciiMatch = /filename="?([^";]+)"?/i.exec(disposition);
  return asciiMatch?.[1]?.trim() || fallback || null;
}

async function throwApiResponseError(response: Response): Promise<never> {
  if (response.status === 401) {
    clearSessionToken();
  }

  const payload = await readJson(response).catch(() => undefined);
  if (isApiErrorResponse(payload)) {
    throw new ApiError(payload.error, response.status);
  }

  throw new ApiError(
    {
      code: "HTTP_ERROR",
      message: `Request failed with status ${response.status}`,
    },
    response.status,
  );
}

export async function apiRequest<T = unknown>(
  path: string,
  init: ApiRequestInit = {},
): Promise<T> {
  const { body, headers: initHeaders, ...requestInit } = init;
  const headers = toHeaderRecord(initHeaders);
  const token = getSessionToken();
  let requestBody = body as BodyInit | null | undefined;

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  if (isJsonBody(body)) {
    headers["Content-Type"] = headers["Content-Type"] ?? "application/json";
    requestBody = JSON.stringify(body);
  }

  const response = await fetch(buildUrl(path), {
    ...requestInit,
    headers,
    body: requestBody,
  });
  const payload = await readJson(response);

  if (!response.ok) {
    if (response.status === 401) {
      clearSessionToken();
    }

    if (isApiErrorResponse(payload)) {
      throw new ApiError(payload.error, response.status);
    }

    throw new ApiError(
      {
        code: "HTTP_ERROR",
        message: `Request failed with status ${response.status}`,
      },
      response.status,
    );
  }

  if (isApiSuccess<T>(payload)) {
    return payload.data;
  }

  return undefined as T;
}

export async function apiFileRequest(
  path: string,
  init: ApiFileRequestInit = {},
): Promise<ApiFileResponse> {
  const { fallbackFilename, headers: initHeaders, ...requestInit } = init;
  const headers = toHeaderRecord(initHeaders);
  const token = getSessionToken();

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(buildUrl(path), {
    method: "GET",
    ...requestInit,
    headers,
  });
  if (!response.ok) {
    return throwApiResponseError(response);
  }

  return {
    blob: await response.blob(),
    filename: filenameFromDisposition(
      response.headers.get("Content-Disposition"),
      fallbackFilename,
    ),
  };
}
