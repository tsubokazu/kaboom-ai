"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "./ui/Button";
import { Input } from "./ui/Input";
import { Card } from "./ui/Card";

interface AuthFormProps {
  mode: "login" | "signup";
  onSubmit: (email: string, password: string, username?: string) => void;
  loading?: boolean;
  error?: string | null;
}

export function AuthForm({ mode, onSubmit, loading = false, error }: AuthFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (mode === "signup" && password !== confirmPassword) {
      alert("パスワードが一致しません");
      return;
    }
    onSubmit(email, password, mode === "signup" ? username : undefined);
  };

  const isSignup = mode === "signup";

  return (
    <Card className="p-8 space-y-6">
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-bold" style={{ color: "var(--kb-text)" }}>
          Kaboom.ai
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          {isSignup ? "アカウントを作成" : "アカウントにログイン"}
        </p>
      </div>

      {error && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {isSignup && (
          <div>
            <label className="block text-sm font-medium mb-2" style={{ color: "var(--kb-text)" }}>
              ユーザー名
            </label>
            <Input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="ユーザー名を入力"
              required={isSignup}
            />
          </div>
        )}

        <div>
          <label className="block text-sm font-medium mb-2" style={{ color: "var(--kb-text)" }}>
            メールアドレス
          </label>
          <Input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="メールアドレスを入力"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2" style={{ color: "var(--kb-text)" }}>
            パスワード
          </label>
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="パスワードを入力"
            required
          />
        </div>

        {isSignup && (
          <div>
            <label className="block text-sm font-medium mb-2" style={{ color: "var(--kb-text)" }}>
              パスワード確認
            </label>
            <Input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="パスワードを再入力"
              required={isSignup}
            />
          </div>
        )}

        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? (
            <div className="flex items-center justify-center">
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
              処理中...
            </div>
          ) : isSignup ? (
            "アカウント作成"
          ) : (
            "ログイン"
          )}
        </Button>
      </form>

      <div className="text-center">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          {isSignup ? (
            <>
              すでにアカウントをお持ちですか？{" "}
              <Link
                href="/login"
                className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-medium"
              >
                ログイン
              </Link>
            </>
          ) : (
            <>
              アカウントをお持ちでない方は{" "}
              <Link
                href="/signup"
                className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-medium"
              >
                新規登録
              </Link>
            </>
          )}
        </p>
      </div>

      {!isSignup && (
        <div className="text-center">
          <Link
            href="/forgot-password"
            className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
          >
            パスワードを忘れた方
          </Link>
        </div>
      )}
    </Card>
  );
}
