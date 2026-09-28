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
  const res = await apiFetchRaw(endpoints.logout, {
    method: "POST",
    redirect: "follow",
  });
  if (res.redirected) {
    window.location.href = res.url;
  } else {
    window.location.href = "/login";
  }
}
