"use client";

import { useEffect } from "react";
import { useAuthStore } from "@/lib/auth-store";

export function ClientProvider({ children }: { children: React.ReactNode }) {
  const { checkAuth } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return <>{children}</>;
}
