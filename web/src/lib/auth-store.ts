import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface User {
  id: string;
  email: string;
  username: string;
  createdAt: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, username: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => void;
}

// モック認証関数
const mockLogin = async (email: string, password: string): Promise<User> => {
  // 実際のAPIコールをシミュレート
  await new Promise((resolve) => setTimeout(resolve, 1000));

  // デモ用の固定認証
  if (email === "demo@kaboom.ai" && password === "demo123") {
    return {
      id: "1",
      email: "demo@kaboom.ai",
      username: "Demo User",
      createdAt: new Date().toISOString(),
    };
  }

  throw new Error("認証に失敗しました");
};

const mockSignup = async (
  email: string,
  password: string,
  username: string,
): Promise<User> => {
  // 実際のAPIコールをシミュレート
  await new Promise((resolve) => setTimeout(resolve, 1000));

  return {
    id: Math.random().toString(),
    email,
    username,
    createdAt: new Date().toISOString(),
  };
};

// クッキー設定関数
const setCookie = (name: string, value: string, days = 7) => {
  if (typeof document !== "undefined") {
    const expires = new Date();
    expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
    document.cookie = `${name}=${value}; expires=${expires.toUTCString()}; path=/`;
  }
};

const getCookie = (name: string): string | null => {
  if (typeof document === "undefined") return null;
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()?.split(";").shift() || null;
  return null;
};

const deleteCookie = (name: string) => {
  if (typeof document !== "undefined") {
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/`;
  }
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      loading: false,

      login: async (email: string, password: string) => {
        set({ loading: true });
        try {
          const user = await mockLogin(email, password);
          const authData = { user, isAuthenticated: true };

          // クッキーに認証状態を保存
          setCookie("auth-storage", JSON.stringify(authData));
          setCookie("kb-auth", "true");

          set({
            user,
            isAuthenticated: true,
            loading: false,
          });
        } catch (error) {
          set({ loading: false });
          throw error;
        }
      },

      signup: async (email: string, password: string, username: string) => {
        set({ loading: true });
        try {
          const user = await mockSignup(email, password, username);
          const authData = { user, isAuthenticated: true };

          // クッキーに認証状態を保存
          setCookie("auth-storage", JSON.stringify(authData));
          setCookie("kb-auth", "true");

          set({
            user,
            isAuthenticated: true,
            loading: false,
          });
        } catch (error) {
          set({ loading: false });
          throw error;
        }
      },

      logout: () => {
        // クッキーを削除
        deleteCookie("auth-storage");
        deleteCookie("kb-auth");

        set({
          user: null,
          isAuthenticated: false,
          loading: false,
        });
      },

      checkAuth: () => {
        // ページロード時に認証状態をチェック
        const authCookie = getCookie("auth-storage");
        if (authCookie) {
          try {
            const authData = JSON.parse(authCookie);
            if (authData.user && authData.isAuthenticated) {
              set({
                user: authData.user,
                isAuthenticated: true,
              });
              return;
            }
          } catch (error) {
            console.error("Auth cookie parse error:", error);
          }
        }
        set({ isAuthenticated: false, user: null });
      },
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
);
