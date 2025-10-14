import { z } from "zod";

export type ApiClientConfig = {
  baseUrl: string;
  getToken: () => Promise<string | undefined>;
};

export class ApiClient {
  constructor(private readonly config: ApiClientConfig) {}

  async request<TData>(path: string, init: RequestInit = {}): Promise<TData> {
    const token = await this.config.getToken();
    const response = await fetch(`${this.config.baseUrl}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init.headers
      }
    });

    if (!response.ok) {
      const body = await response.text();
      throw new Error(`Request failed ${response.status}: ${body}`);
    }

    return (await response.json()) as TData;
  }
}

export const createApiClient = (config: ApiClientConfig) => new ApiClient(config);

export const PaginationSchema = z.object({
  page: z.number().int().min(1).default(1),
  pageSize: z.number().int().min(1).max(100).default(20)
});
