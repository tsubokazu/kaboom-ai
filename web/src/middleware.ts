import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  // 認証が必要なルート
  const protectedRoutes = ["/"];

  // 認証済みユーザーがアクセスできないルート
  const authRoutes = ["/login", "/signup"];

  const { pathname } = request.nextUrl;

  // 認証状態を確認（モック認証用のクッキーチェック）
  const authCookie = request.cookies.get("kb-auth");
  const isAuthenticated = authCookie?.value === "true";

  // 保護されたルートへの未認証アクセス
  if (
    protectedRoutes.some((route) => pathname.startsWith(route)) &&
    pathname !== "/login" &&
    pathname !== "/signup" &&
    !isAuthenticated
  ) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // 認証済みユーザーの認証ページアクセス
  if (
    authRoutes.some((route) => pathname.startsWith(route)) &&
    isAuthenticated
  ) {
    return NextResponse.redirect(new URL("/", request.url));
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
