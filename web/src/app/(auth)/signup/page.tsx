"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AuthForm } from "@/components/AuthForm";
import { useAuthStore } from "@/lib/auth-store";

export default function SignupPage() {
  const router = useRouter();
  const { signup, loading, isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) {
      router.push("/");
    }
  }, [isAuthenticated, router]);

  const handleSignup = async (
    email: string,
    password: string,
    username?: string,
  ) => {
    if (!username) {
      alert("ユーザー名は必須です");
      return;
    }

    try {
      await signup(email, password, username);
      router.push("/");
    } catch {
      alert("アカウント作成に失敗しました");
    }
  };

  return <AuthForm mode="signup" onSubmit={handleSignup} loading={loading} />;
}
