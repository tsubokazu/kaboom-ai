"use client";

import { useCallback, useEffect } from "react";
import { useAuthStore } from "@/lib/auth-store";
import { apiClient } from "@/lib/api-client";

export function useAuth() {
  const {
    user,
    isAuthenticated,
    loading,
    login,
    signup,
    logout,
    checkAuth,
  } = useAuthStore();

  // Backend API との認証確認
  const verifyBackendAuth = useCallback(async (): Promise<boolean> => {
    if (!isAuthenticated) return false;

    try {
      await apiClient.authVerify();
      return true;
    } catch (error) {
      console.warn("Backend authentication failed:", error);
      return false;
    }
  }, [isAuthenticated]);

  // ユーザープロフィール情報をBackendから取得
  const getBackendProfile = useCallback(async () => {
    if (!isAuthenticated) return null;

    try {
      const profile = await apiClient.getProfile();
      return profile;
    } catch (error) {
      console.warn("Failed to get backend profile:", error);
      return null;
    }
  }, [isAuthenticated]);

  // Backend APIヘルスチェック
  const checkBackendHealth = useCallback(async (): Promise<boolean> => {
    try {
      await apiClient.healthCheck();
      return true;
    } catch (error) {
      console.warn("Backend health check failed:", error);
      return false;
    }
  }, []);

  // ページロード時の初期化
  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return {
    // Auth store state
    user,
    isAuthenticated,
    loading,

    // Auth actions
    login,
    signup,
    logout,
    checkAuth,

    // Backend integration
    verifyBackendAuth,
    getBackendProfile,
    checkBackendHealth,
  };
}