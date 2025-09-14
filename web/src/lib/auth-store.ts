import { create } from "zustand";
import { persist } from "zustand/middleware";
import { supabase } from "./supabase-client";
import type { User as SupabaseUser } from "@supabase/supabase-js";

export type UserRole = "BASIC" | "PREMIUM" | "ADMIN";

export interface User {
  id: string;
  email: string;
  username: string;
  role: UserRole;
  createdAt: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, username: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => void;
}

// Supabase認証関数
const performLogin = async (email: string, password: string): Promise<User> => {
  console.log("Login attempt for:", email);

  // パスワードの特殊文字をサニタイズ（必要に応じて）
  const sanitizedPassword = password.trim();

  const { data, error } = await supabase.auth.signInWithPassword({
    email: email.trim().toLowerCase(),
    password: sanitizedPassword,
  });

  console.log("Supabase login response:", { data, error });

  if (error) {
    console.error("Supabase login error:", error);

    // 具体的なエラーメッセージを提供
    if (error.message.includes("Invalid login credentials")) {
      throw new Error("メールアドレスまたはパスワードが正しくありません。メール確認が完了していない可能性があります。");
    } else if (error.message.includes("Email not confirmed")) {
      throw new Error("メールアドレスの確認が完了していません。受信トレイを確認してください。");
    } else if (error.message.includes("Too many requests")) {
      throw new Error("ログイン試行回数が上限に達しました。しばらく待ってから再試行してください。");
    }

    throw new Error(error.message);
  }

  if (!data.user) {
    throw new Error("認証に失敗しました");
  }

  console.log("Login successful for user:", data.user.email);

  // ユーザー情報を構築
  return {
    id: data.user.id,
    email: data.user.email!,
    username: data.user.user_metadata?.username || data.user.email!.split('@')[0],
    role: (data.user.user_metadata?.role as UserRole) || "BASIC",
    createdAt: data.user.created_at,
  };
};

const performSignup = async (
  email: string,
  password: string,
  username: string,
): Promise<User> => {
  console.log("Signup attempt for:", email);

  const { data, error } = await supabase.auth.signUp({
    email: email.trim().toLowerCase(),
    password: password.trim(),
    options: {
      data: {
        username,
        role: "BASIC" as UserRole,
      },
      // 開発環境では自動的にメール確認を無効化
      emailRedirectTo: undefined,
    },
  });

  console.log("Supabase signup response:", { data, error });

  if (error) {
    console.error("Supabase signup error:", error);
    throw new Error(error.message);
  }

  if (!data.user) {
    throw new Error("アカウント作成に失敗しました");
  }

  console.log("Signup successful for user:", data.user.email);
  console.log("Email confirmation required:", !data.session);
  console.log("User profile will be created automatically via database trigger");

  // メール確認が必要な場合の通知
  if (!data.session) {
    console.log("Email confirmation required - user created but not confirmed");
  }

  return {
    id: data.user.id,
    email: data.user.email!,
    username,
    role: "BASIC",
    createdAt: data.user.created_at,
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
          const user = await performLogin(email, password);
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
          const user = await performSignup(email, password, username);

          // メール確認が必要な場合は認証状態をfalseにする
          const { data: { session } } = await supabase.auth.getSession();
          const isEmailConfirmed = !!session;

          if (isEmailConfirmed) {
            const authData = { user, isAuthenticated: true };
            setCookie("auth-storage", JSON.stringify(authData));
            setCookie("kb-auth", "true");

            set({
              user,
              isAuthenticated: true,
              loading: false,
            });
          } else {
            // メール確認が必要な場合は認証状態をfalseのままにする
            set({
              user: null,
              isAuthenticated: false,
              loading: false,
            });
          }
        } catch (error) {
          set({ loading: false });
          throw error;
        }
      },

      logout: async () => {
        // Supabaseからログアウト
        await supabase.auth.signOut();

        // クッキーを削除
        deleteCookie("auth-storage");
        deleteCookie("kb-auth");

        set({
          user: null,
          isAuthenticated: false,
          loading: false,
        });

        // ログイン画面にリダイレクト
        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }
      },

      checkAuth: async () => {
        // Supabaseセッションをチェック
        const { data: { session } } = await supabase.auth.getSession();

        if (session?.user) {
          const user: User = {
            id: session.user.id,
            email: session.user.email!,
            username: session.user.user_metadata?.username || session.user.email!.split('@')[0],
            role: (session.user.user_metadata?.role as UserRole) || "BASIC",
            createdAt: session.user.created_at,
          };

          const authData = { user, isAuthenticated: true };
          setCookie("auth-storage", JSON.stringify(authData));
          setCookie("kb-auth", "true");

          set({
            user,
            isAuthenticated: true,
          });
        } else {
          // セッションがない場合はログアウト状態に
          deleteCookie("auth-storage");
          deleteCookie("kb-auth");
          set({ isAuthenticated: false, user: null });
        }
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
