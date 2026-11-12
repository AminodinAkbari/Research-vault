import { apiFetch, apiFetchRaw } from "./api";
import { endpoints } from "./endpoints";
import { LoginRequest, LoginResponse, RegisterRequest, RegisterResponse } from "./types";

export async function login(data: LoginRequest): Promise<LoginResponse> {
  return apiFetch(endpoints.login, LoginResponse, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function register(data: RegisterRequest): Promise<RegisterResponse> {
  return apiFetch(endpoints.register, RegisterResponse, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function logout(): Promise<void> {
  await apiFetchRaw(endpoints.logout, {
    method: "POST",
  });
  window.location.href = "/login";
}
