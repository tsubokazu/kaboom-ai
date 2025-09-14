"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AuthForm } from "@/components/AuthForm";
import { useAuthStore } from "@/lib/auth-store";
import { EmailConfirmationStatus } from "@/components/auth/EmailConfirmationStatus";
import { QuickPasswordReset } from "@/components/auth/QuickPasswordReset";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, loading, isAuthenticated, checkAuth } = useAuthStore();
  const [error, setError] = useState<string | null>(null);
  const [showEmailConfirmation, setShowEmailConfirmation] = useState<string | null>(null);
  const [showPasswordReset, setShowPasswordReset] = useState<string | null>(null);

  // リダイレクト先を取得
  const redirectTo = searchParams.get("redirect") || "/";

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  useEffect(() => {
    if (isAuthenticated) {
      router.push(redirectTo);
    }
  }, [isAuthenticated, router, redirectTo]);

  const handleLogin = async (email: string, password: string) => {
    setError(null);
    setShowEmailConfirmation(null);
    setShowPasswordReset(null);

    try {
      await login(email, password);
      router.push(redirectTo);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "ログインに失敗しました";
      setError(errorMessage);

      // パスワードに特殊文字が含まれている場合の特別処理
      if (email === "tsubokazu.dev@gmail.com" && password.includes("@")) {
        setShowPasswordReset(email);
      }
      // メール確認が必要な場合の処理
      else if (errorMessage.includes("メール確認が完了していない") ||
               errorMessage.includes("Invalid login credentials")) {
        setShowEmailConfirmation(email);
      }
    }
  };

  return (
    <div className="space-y-6">
      <AuthForm mode="login" onSubmit={handleLogin} loading={loading} error={error} />

      {/* パスワード特殊文字問題の解決 */}
      {showPasswordReset && (
        <QuickPasswordReset email={showPasswordReset} />
      )}

      {/* メール確認が必要な場合の表示 */}
      {showEmailConfirmation && (
        <EmailConfirmationStatus
          email={showEmailConfirmation}
          onConfirmed={() => {
            setShowEmailConfirmation(null);
            setError(null);
          }}
        />
      )}

      <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
        <h3 className="text-sm font-medium text-blue-900 dark:text-blue-300 mb-2">
          ログイン方法
        </h3>
        <p className="text-xs text-blue-700 dark:text-blue-400">
          新規登録後、メール確認が必要です。受信トレイをご確認ください。
        </p>
      </div>

      <div className="mt-4 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
        <h3 className="text-sm font-medium text-green-900 dark:text-green-300 mb-2">
          権限レベル
        </h3>
        <div className="text-xs text-green-700 dark:text-green-400 space-y-1">
          <div><strong>BASIC:</strong> 基本的な取引・分析機能</div>
          <div><strong>PREMIUM:</strong> 高度なAI分析・バックテスト機能</div>
          <div><strong>ADMIN:</strong> システム管理機能</div>
        </div>
      </div>
    </div>
  );
}
