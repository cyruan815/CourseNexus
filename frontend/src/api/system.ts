import { apiRequest } from "./client";

export interface RuntimeStatus {
  status: "ok";
  environment: "development" | "test" | "production";
  mock_model_provider_enabled: boolean;
}

export function getRuntimeStatus(): Promise<RuntimeStatus> {
  return apiRequest<RuntimeStatus>("/api/v1/health");
}
