"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { supabase } from "@/lib/supabase-client";

interface QuickPasswordResetProps {
  email: string;
}

export function QuickPasswordReset({ email }: QuickPasswordResetProps) {
  const [newPassword, setNewPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [step, setStep] = useState<"reset" | "verify">("reset");
  const [otp, setOtp] = useState("");

  const handlePasswordReset = async () => {
    setLoading(true);
    setMessage(null);

    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/auth/reset-password`,
      });

      if (error) {
        setMessage(`エラー: ${error.message}`);
      } else {
        setMessage("パスワードリセット用のリンクを送信しました。");
        setStep("verify");
      }
    } catch (error) {
      setMessage("パスワードリセットに失敗しました。");
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordUpdate = async () => {
    if (!otp || !newPassword) {
      setMessage("OTPと新しいパスワードを入力してください。");
      return;
    }

    setLoading(true);
    setMessage(null);

    try {
      const { error } = await supabase.auth.verifyOtp({
        email,
        token: otp,
        type: 'recovery',
      });

      if (error) {
        setMessage(`OTP確認エラー: ${error.message}`);
        return;
      }

      const { error: updateError } = await supabase.auth.updateUser({
        password: newPassword
      });

      if (updateError) {
        setMessage(`パスワード更新エラー: ${updateError.message}`);
      } else {
        setMessage("パスワードが正常に更新されました！ログインをお試しください。");
      }
    } catch (error) {
      setMessage("パスワード更新に失敗しました。");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg">
      <h3 className="text-sm font-medium text-orange-900 dark:text-orange-300 mb-2">
        パスワード問題解決
      </h3>

      {step === "reset" ? (
        <div className="space-y-3">
          <p className="text-sm text-orange-700 dark:text-orange-400">
            現在のパスワード（特殊文字含む）で問題が発生している可能性があります。
            新しいパスワードでリセットしてください。
          </p>

          <div>
            <label className="block text-xs font-medium text-orange-700 dark:text-orange-400 mb-1">
              新しいパスワード（英数字のみ推奨）
            </label>
            <Input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="KaboomTest123"
              className="text-sm"
            />
          </div>

          <Button
            onClick={handlePasswordReset}
            disabled={loading || !newPassword}
            size="sm"
            className="w-full"
          >
            {loading ? "送信中..." : "パスワードリセットメール送信"}
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-orange-700 dark:text-orange-400">
            メールに送信されたOTPコードを入力してください。
          </p>

          <div>
            <label className="block text-xs font-medium text-orange-700 dark:text-orange-400 mb-1">
              OTPコード（6桁）
            </label>
            <Input
              type="text"
              value={otp}
              onChange={(e) => setOtp(e.target.value)}
              placeholder="123456"
              className="text-sm"
              maxLength={6}
            />
          </div>

          <Button
            onClick={handlePasswordUpdate}
            disabled={loading || !otp || !newPassword}
            size="sm"
            className="w-full"
          >
            {loading ? "更新中..." : "パスワード更新"}
          </Button>

          <Button
            onClick={() => setStep("reset")}
            variant="outline"
            size="sm"
            className="w-full"
          >
            戻る
          </Button>
        </div>
      )}

      {message && (
        <p className={`text-xs mt-2 ${
          message.includes("エラー") || message.includes("失敗")
            ? "text-red-600 dark:text-red-400"
            : "text-green-600 dark:text-green-400"
        }`}>
          {message}
        </p>
      )}

      <div className="mt-3 text-xs text-orange-600 dark:text-orange-400">
        <p><strong>推奨パスワード形式:</strong></p>
        <ul className="list-disc ml-4">
          <li>8文字以上</li>
          <li>英数字のみ（特殊文字なし）</li>
          <li>例: KaboomTest123</li>
        </ul>
      </div>
    </div>
  );
}