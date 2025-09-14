import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 認証不要のルート（パブリック）
  const publicRoutes = ["/login", "/signup", "/forgot-password"];

  // パスワードリセット関連のルート（auth callback用）
  const authCallbackRoutes = ["/auth/reset-password", "/auth/confirm"];

  // 認証状態を確認（Supabase認証用のクッキーチェック）
  const authCookie = request.cookies.get("kb-auth");
  const isAuthenticated = authCookie?.value === "true";

  // パブリックルートまたは認証コールバック関連の場合はそのまま通す
  if (
    publicRoutes.includes(pathname) ||
    authCallbackRoutes.some((route) => pathname.startsWith(route))
  ) {
    // 認証済みユーザーがログイン・新規登録ページにアクセスした場合はダッシュボードへ
    if (publicRoutes.includes(pathname) && isAuthenticated) {
      return NextResponse.redirect(new URL("/", request.url));
    }
    return NextResponse.next();
  }

  // 上記以外の全てのルートは認証が必要
  // 未認証の場合はログイン画面にリダイレクト
  if (!isAuthenticated) {
    // 現在のURLを保存してログイン後にリダイレクトできるようにする
    const loginUrl = new URL("/login", request.url);
    if (pathname !== "/") {
      loginUrl.searchParams.set("redirect", pathname);
    }
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * 以下のパスを除くすべてのリクエストに適用:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
};
