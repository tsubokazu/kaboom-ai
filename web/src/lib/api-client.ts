import { supabase } from "./supabase-client";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiClient {
  private async getAuthHeaders(): Promise<HeadersInit> {
    const { data: { session } } = await supabase.auth.getSession();

    if (session?.access_token) {
      return {
        "Authorization": `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
      };
    }

    return {
      "Content-Type": "application/json",
    };
  }

  async get(endpoint: string): Promise<any> {
    const headers = await this.getAuthHeaders();

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "GET",
      headers,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  async post(endpoint: string, data: any): Promise<any> {
    const headers = await this.getAuthHeaders();

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "POST",
      headers,
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  async put(endpoint: string, data: any): Promise<any> {
    const headers = await this.getAuthHeaders();

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "PUT",
      headers,
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  async delete(endpoint: string): Promise<any> {
    const headers = await this.getAuthHeaders();

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "DELETE",
      headers,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  // 特定のAPI endpoints
  async healthCheck(): Promise<any> {
    return this.get("/health");
  }

  async authVerify(): Promise<any> {
    return this.post("/api/v1/auth/verify", {});
  }

  async getProfile(): Promise<any> {
    return this.get("/api/v1/auth/me");
  }
}

export const apiClient = new ApiClient();