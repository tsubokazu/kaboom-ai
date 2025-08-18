"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AuthForm } from "@/components/AuthForm";
import { useAuthStore } from "@/lib/auth-store";

export default function LoginPage() {
  const router = useRouter();
  const { login, loading, isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) {
      router.push("/");
    }
  }, [isAuthenticated, router]);

  const handleLogin = async (email: string, password: string) => {
    try {
      await login(email, password);
      router.push("/");
    } catch {
      alert("ログインに失敗しました");
    }
  };

  return (
    <div>
      <AuthForm mode="login" onSubmit={handleLogin} loading={loading} />
      <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
        <h3 className="text-sm font-medium text-blue-900 dark:text-blue-300 mb-2">
          デモアカウント
        </h3>
        <p className="text-xs text-blue-700 dark:text-blue-400">
          Email: demo@kaboom.ai
          <br />
          Password: demo123
        </p>
      </div>
    </div>
  );
}
