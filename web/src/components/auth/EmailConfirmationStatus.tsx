"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { supabase } from "@/lib/supabase-client";

interface EmailConfirmationStatusProps {
  email: string;
  onConfirmed?: () => void;
}

export function EmailConfirmationStatus({ email, onConfirmed }: EmailConfirmationStatusProps) {
  const [resending, setResending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const handleResendConfirmation = async () => {
    setResending(true);
    setMessage(null);

    try {
      const { error } = await supabase.auth.resend({
        type: 'signup',
        email: email,
      });

      if (error) {
        setMessage(`エラー: ${error.message}`);
      } else {
        setMessage("確認メールを再送信しました。受信トレイをご確認ください。");
      }
    } catch (error) {
      setMessage("メール送信に失敗しました。");
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
      <h3 className="text-sm font-medium text-yellow-900 dark:text-yellow-300 mb-2">
        メール確認が必要です
      </h3>

      <p className="text-sm text-yellow-700 dark:text-yellow-400 mb-4">
        <strong>{email}</strong> 宛に確認メールを送信しました。
        <br />
        メール内のリンクをクリックしてアカウントを有効化してください。
      </p>

      <div className="space-y-2">
        <Button
          onClick={handleResendConfirmation}
          disabled={resending}
          size="sm"
          variant="outline"
          className="w-full"
        >
          {resending ? "送信中..." : "確認メールを再送信"}
        </Button>

        {message && (
          <p className={`text-xs ${
            message.includes("エラー")
              ? "text-red-600 dark:text-red-400"
              : "text-green-600 dark:text-green-400"
          }`}>
            {message}
          </p>
        )}
      </div>

      <div className="mt-3 text-xs text-yellow-600 dark:text-yellow-400">
        <p><strong>確認事項:</strong></p>
        <ul className="list-disc ml-4 space-y-1">
          <li>受信トレイ（メインフォルダ）を確認</li>
          <li>迷惑メールフォルダを確認</li>
          <li>送信者: noreply@mail.app.supabase.io</li>
          <li>件名: "Confirm your signup"</li>
        </ul>
      </div>
    </div>
  );
}