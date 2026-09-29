"use client";

import { useState, useEffect, useCallback } from "react";
import { login as loginApi, register as registerApi, logout as logoutApi } from "@/lib/auth";
import { LoginRequest, RegisterRequest } from "@/lib/types";

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    isAuthenticated: false,
    isLoading: true,
  });

  // Probe session by hitting an authenticated endpoint
  const probeSession = useCallback(async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/projects", {
        credentials: "include",
      });
      setState({ isAuthenticated: res.ok, isLoading: false });
    } catch {
      setState({ isAuthenticated: false, isLoading: false });
    }
  }, []);

  useEffect(() => {
    probeSession();
  }, [probeSession]);

  const login = useCallback(async (data: LoginRequest) => {
    await loginApi(data);
    setState({ isAuthenticated: true, isLoading: false });
  }, []);

  const register = useCallback(async (data: RegisterRequest) => {
    await registerApi(data);
    setState({ isAuthenticated: true, isLoading: false });
  }, []);

  const logout = useCallback(async () => {
    await logoutApi();
    setState({ isAuthenticated: false, isLoading: false });
  }, []);

  return {
    isAuthenticated: state.isAuthenticated,
    isLoading: state.isLoading,
    login,
    register,
    logout,
    probeSession,
  };
}
