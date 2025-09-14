"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/Button";

export function BackendStatus() {
  const { isAuthenticated, verifyBackendAuth, checkBackendHealth } = useAuth();
  const [backendHealth, setBackendHealth] = useState<boolean | null>(null);
  const [authVerified, setAuthVerified] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);

  // Backend ヘルスチェック
  const handleHealthCheck = async () => {
    setLoading(true);
    try {
      const health = await checkBackendHealth();
      setBackendHealth(health);
    } catch (error) {
      setBackendHealth(false);
    } finally {
      setLoading(false);
    }
  };

  // Backend 認証確認
  const handleAuthVerify = async () => {
    setLoading(true);
    try {
      const verified = await verifyBackendAuth();
      setAuthVerified(verified);
    } catch (error) {
      setAuthVerified(false);
    } finally {
      setLoading(false);
    }
  };

  // 初回ロード時にヘルスチェック実行
  useEffect(() => {
    handleHealthCheck();
  }, []);

  return (
    <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg space-y-4">
      <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">
        Backend API 統合状況
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Backend ヘルス状況 */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600 dark:text-gray-400">
              Backend ヘルス:
            </span>
            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  backendHealth === null
                    ? "bg-gray-400"
                    : backendHealth
                    ? "bg-green-500"
                    : "bg-red-500"
                }`}
              />
              <span className="text-xs">
                {backendHealth === null
                  ? "Unknown"
                  : backendHealth
                  ? "OK"
                  : "Error"}
              </span>
            </div>
          </div>
          <Button
            onClick={handleHealthCheck}
            disabled={loading}
            size="sm"
            className="w-full"
          >
            ヘルスチェック
          </Button>
        </div>

        {/* 認証状況 */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600 dark:text-gray-400">
              認証状況:
            </span>
            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  !isAuthenticated
                    ? "bg-gray-400"
                    : authVerified === null
                    ? "bg-yellow-400"
                    : authVerified
                    ? "bg-green-500"
                    : "bg-red-500"
                }`}
              />
              <span className="text-xs">
                {!isAuthenticated
                  ? "未認証"
                  : authVerified === null
                  ? "未確認"
                  : authVerified
                  ? "認証済"
                  : "認証失敗"}
              </span>
            </div>
          </div>
          <Button
            onClick={handleAuthVerify}
            disabled={loading || !isAuthenticated}
            size="sm"
            className="w-full"
          >
            認証確認
          </Button>
        </div>
      </div>

      {!backendHealth && (
        <p className="text-xs text-red-600 dark:text-red-400">
          Backend APIに接続できません。サーバーが起動していることを確認してください。
        </p>
      )}
    </div>
  );
}