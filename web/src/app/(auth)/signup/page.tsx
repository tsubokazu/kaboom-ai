"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AuthForm } from "@/components/AuthForm";
import { useAuthStore } from "@/lib/auth-store";
import { EmailConfirmationStatus } from "@/components/auth/EmailConfirmationStatus";

export default function SignupPage() {
  const router = useRouter();
  const { signup, loading, isAuthenticated, checkAuth } = useAuthStore();
  const [error, setError] = useState<string | null>(null);
  const [signupSuccess, setSignupSuccess] = useState(false);
  const [pendingEmail, setPendingEmail] = useState<string | null>(null);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

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
      setError("ユーザー名は必須です");
      return;
    }

    setError(null);
    setSignupSuccess(false);
    setPendingEmail(null);

    try {
      await signup(email, password, username);

      // 認証済みの場合は即座にダッシュボードへ
      if (isAuthenticated) {
        router.push("/");
      } else {
        // メール確認が必要な場合は確認画面を表示
        setSignupSuccess(true);
        setPendingEmail(email);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "アカウント作成に失敗しました";
      setError(errorMessage);
    }
  };

  return (
    <div className="space-y-6">
      {!signupSuccess ? (
        <>
          <AuthForm mode="signup" onSubmit={handleSignup} loading={loading} error={error} />

          <div className="mt-4 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
            <h3 className="text-sm font-medium text-green-900 dark:text-green-300 mb-2">
              新規登録について
            </h3>
            <div className="text-xs text-green-700 dark:text-green-400 space-y-1">
              <div>• 新規登録したアカウントはBASIC権限から開始されます</div>
              <div>• メールアドレス確認が必要な場合があります</div>
              <div>• パスワードは8文字以上を推奨します</div>
              <div>• 特殊文字を含むパスワードは問題が発生する場合があります</div>
            </div>
          </div>
        </>
      ) : (
        <>
          <div className="p-6 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg text-center">
            <h2 className="text-lg font-semibold text-green-900 dark:text-green-300 mb-2">
              🎉 アカウント作成完了
            </h2>
            <p className="text-sm text-green-700 dark:text-green-400 mb-4">
              アカウントが正常に作成されました！
            </p>
            {pendingEmail && (
              <p className="text-xs text-green-600 dark:text-green-400">
                メール確認が必要です。以下の手順に従ってください。
              </p>
            )}
          </div>

          {pendingEmail && (
            <EmailConfirmationStatus
              email={pendingEmail}
              onConfirmed={() => {
                setSignupSuccess(false);
                setPendingEmail(null);
                router.push("/login");
              }}
            />
          )}

          <div className="text-center">
            <button
              onClick={() => router.push("/login")}
              className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 underline"
            >
              ログインページに戻る
            </button>
          </div>
        </>
      )}
    </div>
  );
}
