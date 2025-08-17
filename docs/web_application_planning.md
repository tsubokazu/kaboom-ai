# 株式自動売買管理システム - フロントエンド開発指示書

## 1. プロジェクト概要

### 1.1 システム全体像

- **目的**: 株式の自動売買管理とバックテストを行う Web アプリケーション
- **役割**: ユーザーインターフェースの提供、リアルタイムデータ表示、バックエンド API との通信
- **ユーザー種別**: 一般ユーザー（トレーダー）、管理者

### 1.2 技術スタック

- **フレームワーク**: Next.js 15 (App Router)
- **UI ライブラリ**: React 19
- **言語**: TypeScript 5.x
- **スタイリング**: Tailwind CSS
- **状態管理**: Zustand / TanStack Query
- **リアルタイム通信**: WebSocket（ネイティブ）
- **チャート（フロント）**: Recharts（ポートフォリオ/推移系、必要時に dynamic import）
- **チャート（AI/バックテスト）**: matplotlib + mplfinance（バックエンドで画像生成しフロントで表示）
- **フォーム**: React Hook Form + Zod
- **認証**: Supabase Auth（SDK 利用、@supabase/ssr の Cookie 運用）
- **ホスティング**: フロント=Vercel / API・WebSocket=Cloud Run（FastAPI）

## 2. プロジェクト構造

### 2.1 ディレクトリ構成（最新版）

```
web/                                   # フロントエンド (Next.js 15)
├── src/
│   ├── app/                          # Next.js App Router
│   │   ├── (auth)/                   # 認証ルートグループ
│   │   │   ├── login/
│   │   │   │   ├── page.tsx
│   │   │   │   └── loading.tsx
│   │   │   ├── register/
│   │   │   │   ├── page.tsx
│   │   │   │   └── loading.tsx
│   │   │   └── layout.tsx            # 認証レイアウト
│   │   ├── (dashboard)/              # ダッシュボードルートグループ
│   │   │   ├── dashboard/
│   │   │   │   ├── page.tsx          # メインダッシュボード
│   │   │   │   └── loading.tsx
│   │   │   ├── portfolio/
│   │   │   │   ├── page.tsx          # ポートフォリオ画面
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx      # 個別ポートフォリオ
│   │   │   ├── ai-analysis/
│   │   │   │   ├── page.tsx          # AI分析画面
│   │   │   │   └── [symbol]/
│   │   │   │       └── page.tsx      # 銘柄別分析
│   │   │   ├── backtest/
│   │   │   │   ├── page.tsx          # バックテスト画面
│   │   │   │   └── results/
│   │   │   │       └── [id]/
│   │   │   │           └── page.tsx  # バックテスト結果
│   │   │   ├── settings/
│   │   │   │   ├── page.tsx          # 設定画面
│   │   │   │   ├── profile/
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── api-keys/
│   │   │   │   │   └── page.tsx
│   │   │   │   └── notifications/
│   │   │   │       └── page.tsx
│   │   │   └── layout.tsx            # ダッシュボードレイアウト
│   │   ├── (admin)/                  # 管理者ルートグループ
│   │   │   ├── admin/
│   │   │   │   ├── page.tsx          # 管理者ダッシュボード
│   │   │   │   ├── users/
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   └── [id]/
│   │   │   │   │       └── page.tsx
│   │   │   │   ├── metrics/
│   │   │   │   │   └── page.tsx
│   │   │   │   └── ai-settings/
│   │   │   │       └── page.tsx
│   │   │   └── layout.tsx            # 管理者レイアウト
│   │   ├── api/                      # Next.js API Routes（必要時）
│   │   │   └── auth/
│   │   │       └── callback/
│   │   │           └── route.ts      # Supabase認証コールバック
│   │   ├── layout.tsx                # ルートレイアウト（HTML、body）
│   │   ├── page.tsx                  # ランディングページ
│   │   ├── globals.css               # Tailwind CSS import
│   │   ├── loading.tsx               # グローバルローディング
│   │   ├── error.tsx                 # グローバルエラーハンドリング
│   │   └── not-found.tsx             # 404ページ
│   ├── components/
│   │   ├── ui/                       # 基本UIコンポーネント
│   │   ├── charts/                   # チャート関連（Recharts）
│   │   ├── dashboard/                # ダッシュボード専用
│   │   ├── trading/                  # 取引関連
│   │   ├── backtest/                 # バックテスト関連
│   │   ├── auth/                     # 認証関連
│   │   └── shared/                   # 共通コンポーネント
│   ├── hooks/                        # カスタムフック
│   │   ├── useWebSocket.ts           # WebSocket接続管理
│   │   ├── useRealtimePrice.ts       # リアルタイム価格データ
│   │   ├── useAuth.ts                # 認証状態管理
│   │   ├── useAPI.ts                 # API呼び出し
│   │   ├── useBacktest.ts            # バックテスト操作
│   │   ├── usePortfolio.ts           # ポートフォリオ操作
│   │   ├── useLocalStorage.ts        # ローカルストレージ
│   │   └── useDebounce.ts            # デバウンス処理
│   ├── lib/                          # ユーティリティライブラリ
│   │   ├── supabase/
│   │   │   ├── client.ts             # クライアントサイド用
│   │   │   ├── server.ts             # サーバーサイド用
│   │   │   ├── middleware.ts         # ミドルウェア用
│   │   │   └── types.ts              # Supabase型定義
│   │   ├── api/
│   │   │   ├── client.ts             # APIクライアント
│   │   │   ├── endpoints.ts          # エンドポイント定数
│   │   │   ├── types.ts              # APIレスポンス型
│   │   │   └── error-handler.ts      # エラーハンドリング
│   │   ├── websocket/
│   │   │   ├── manager.ts            # WebSocket接続管理
│   │   │   ├── events.ts             # イベント定義
│   │   │   └── reconnect.ts          # 再接続ロジック
│   │   └── utils/
│   │       ├── formatters.ts         # データフォーマット関数
│   │       ├── validators.ts         # バリデーション関数
│   │       ├── constants.ts          # アプリケーション定数
│   │       ├── date-utils.ts         # 日付操作
│   │       └── chart-utils.ts        # チャート関連ユーティリティ
│   ├── stores/                       # Zustand状態管理
│   │   ├── authStore.ts              # 認証状態
│   │   ├── portfolioStore.ts         # ポートフォリオ状態
│   │   ├── websocketStore.ts         # WebSocket接続状態
│   │   ├── backtestStore.ts          # バックテスト状態
│   │   ├── settingsStore.ts          # アプリケーション設定
│   │   └── notificationStore.ts      # 通知状態
│   ├── types/                        # TypeScript型定義
│   │   ├── api.ts                    # API関連型
│   │   ├── trading.ts                # 取引関連型
│   │   ├── portfolio.ts              # ポートフォリオ型
│   │   ├── websocket.ts              # WebSocket型
│   │   ├── auth.ts                   # 認証型
│   │   ├── backtest.ts               # バックテスト型
│   │   └── chart.ts                  # チャート型
│   └── config/                       # 設定
│       ├── constants.ts              # アプリケーション定数
│       ├── environment.ts            # 環境変数
│       └── routes.ts                 # ルート定数
├── public/                           # 静的ファイル
├── tests/                            # テスト
├── .env.local                        # 環境変数（ローカル）
├── .env.example                      # 環境変数サンプル
├── next.config.js                    # Next.js設定
├── tailwind.config.ts                # Tailwind CSS設定
├── tsconfig.json                     # TypeScript設定
├── package.json
├── playwright.config.ts              # E2Eテスト設定
└── README.md
```

## 3. 画面仕様

### 3.1 認証関連画面

#### ログイン画面 (/login)

- **要素**:
  - メールアドレス入力欄
  - パスワード入力欄
  - ログインボタン
  - 新規登録リンク
  - パスワードリセットリンク
- **バリデーション**:
  - メール形式チェック
  - パスワード最小文字数（8 文字）
- **認証後の遷移**: /dashboard

#### 新規登録画面 (/register)

- **要素**:
  - メールアドレス入力欄
  - パスワード入力欄
  - パスワード確認入力欄
  - 利用規約同意チェックボックス
  - 登録ボタン
- **バリデーション**:
  - メール重複チェック（API 経由）
  - パスワード強度チェック
  - パスワード一致確認

### 3.2 メインダッシュボード (/dashboard)

#### ヘッダー

- **固定ヘッダー**:
  - ロゴ
  - ナビゲーションメニュー
  - WebSocket 接続状態インジケーター
  - 通知アイコン（未読数バッジ付き）
  - ユーザーメニュー（アバター、ドロップダウン）

#### ポートフォリオサマリーセクション

- **表示項目**:
  - 総資産額（リアルタイム更新）
  - 本日の損益（金額・パーセンテージ）
  - 月間損益
  - 全体勝率
- **更新頻度**: WebSocket 経由で 1 秒ごと
- **アニメーション**: 数値変更時のカウントアップ/ダウン

#### リアルタイム AI 判断テーブル

- **カラム**:
  - 銘柄コード
  - 銘柄名
  - 現在価格（リアルタイム）
  - 前日比
  - AI 判断（買い/売り/保持）
  - 信頼度（パーセンテージ）
  - 最終更新時刻
- **機能**:
  - ソート（各カラム）
  - フィルター（AI 判断別）
  - ページネーション
  - 銘柄クリックで詳細モーダル表示

#### ポートフォリオ推移チャート

- **チャートタイプ**: エリアチャート
- **期間切り替え**: 1 日/1 週間/1 ヶ月/3 ヶ月/1 年/全期間
- **表示データ**:
  - 資産推移ライン
  - ベンチマーク比較（日経平均等）
- **インタラクション**:
  - ホバーでツールチップ表示
  - ピンチズーム対応（モバイル）

### 3.3 AI 分析画面 (/ai-analysis)

#### 銘柄選択セクション

- **検索機能**:
  - 銘柄コード/名前でのオートコンプリート
  - 最近の検索履歴
  - お気に入り銘柄リスト

#### チャート表示エリア

- **4 分割表示**:
  - 1 分足チャート
  - 5 分足チャート
  - 1 時間足チャート
  - 4 時間足チャート
- **チャート機能**:
  - ローソク足表示
  - 出来高表示
  - テクニカル指標オーバーレイ
  - 描画ツール
  - AI 分析用チャートはバックエンド（matplotlib + mplfinance）で画像生成し、フロントでは画像として表示

#### AI 判断結果パネル

- **表示内容**:
  - 総合判断（買い/売り/保持）
  - 信頼度スコア
  - 使用 AI モデル表示
  - 判断理由（箇条書き）
  - 推奨アクション
- **履歴表示**:
  - 過去の AI 判断タイムライン
  - 判断の的中率

#### テクニカル指標ダッシュボード

- **表示指標**:
  - RSI
  - MACD
  - ボリンジャーバンド
  - 移動平均線（5/25/75 日）
  - 出来高
- **視覚化**: ゲージ、グラフ、数値表示の組み合わせ

### 3.4 バックテスト画面 (/backtest)

#### 設定パネル

- **入力項目**:
  - 開始日・終了日（カレンダーピッカー）
  - 初期資金額
  - 銘柄選択（複数選択可能）
  - AI モデル選択（チェックボックス）
  - 取引戦略選択
  - 手数料設定
- **プリセット**: 保存済み設定の読み込み

#### 実行制御

- **ボタン**:
  - 実行開始
  - 一時停止
  - 停止
  - リセット
- **プログレスバー**: 処理進捗表示
- **推定残り時間表示**

#### 結果表示エリア

- **サマリーカード**:
  - 最終資産額
  - 総利益/損失
  - 勝率
  - 最大ドローダウン
  - シャープレシオ
  - 総取引回数
- **詳細チャート**:
  - 資産推移グラフ（バックエンド生成画像を表示: PNG/SVG）
  - ドローダウングラフ（バックエンド生成画像を表示）
  - 月別収益ヒートマップ（バックエンド生成画像を表示）
- **取引履歴テーブル**:
  - 全取引の詳細記録
  - CSV/PDF エクスポート機能

### 3.5 管理者画面 (/admin)

#### ユーザー管理

- **一覧表示**:
  - ユーザー ID
  - メールアドレス
  - 登録日
  - 最終ログイン
  - ステータス
- **アクション**:
  - アカウント有効/無効化
  - 権限変更
  - 詳細情報閲覧

#### システム監視ダッシュボード

- **メトリクス表示**:
  - アクティブユーザー数
  - WebSocket 接続数
  - API 使用率
  - エラー率
- **グラフ**: リアルタイムモニタリング

#### AI 設定管理

- **設定項目**:
  - AI プロバイダー有効/無効
  - API キー管理
  - レート制限設定
  - コスト監視

## 4. API 連携仕様

### 4.1 エンドポイント構成

```
Base URL: https://api.example.com/v1   （Cloud Run 上の FastAPI）

認証:
Supabase Auth をフロントエンド SDK（@supabase/supabase-js）で利用（専用の REST エンドポイントは不要）

ポートフォリオ:
GET    /portfolios
GET    /portfolios/{id}
POST   /portfolios
PUT    /portfolios/{id}
DELETE /portfolios/{id}

取引:
GET    /trades
GET    /trades/{id}
POST   /trades
GET    /trades/history

AI分析:
POST   /ai/analyze
GET    /ai/decisions
GET    /ai/decisions/{id}
GET    /ai/charts                      # AI 分析チャート画像（例: /ai/charts?symbol=7203&tf=1h）

バックテスト:
POST   /backtest/run
GET    /backtest/results
GET    /backtest/results/{id}
GET    /backtest/charts               # バックテストチャート画像（例: /backtest/charts?id=RESULT_ID&type=equity）

リアルタイムデータ:
GET    /market/prices
GET    /market/indicators

管理者:
GET    /admin/users
PUT    /admin/users/{id}
GET    /admin/metrics
```

### 4.2 認証フロー

```
1. ログイン/登録:
   - フロントで @supabase/supabase-js を利用してサインイン/サインアップ
   - Next.js では @supabase/ssr を用いてセッションを Cookie に保存（HttpOnly/SameSite=strict）

2. API 呼び出し（Cloud Run / FastAPI）:
   - サーバーコンポーネント（RSC）: Cookie のセッションからアクセストークンを取得しフェッチに付与
   - クライアントコンポーネント: supabase クライアントからアクセストークンを取得し Authorization: Bearer を付与

3. トークン更新:
   - supabase-js が自動リフレッシュを管理（Cookie ベースの場合は @supabase/ssr で同期）
```

### 4.3 WebSocket 仕様

```
接続URL: wss://api.example.com/ws   （Cloud Run 上の FastAPI）

プロトコル:
- ネイティブ WebSocket（Socket.io は使用しない）
- Ping/Pong によるハートビート（30s）
- 再接続は指数バックオフ（初回 500ms、最大 10s）
- タブ間共有（BroadcastChannel）で多重接続を回避

イベント:
- connect: 接続確立
- disconnect: 接続切断
- price_update: 価格更新
- portfolio_update: ポートフォリオ更新
- ai_decision: AI判断更新
- trade_executed: 取引実行通知

メッセージフォーマット:
{
  "event": "price_update",
  "data": {
    "symbol": "7203",
    "price": 2345.00,
    "change": 23.00,
    "change_percent": 1.02,
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

## 5. 状態管理設計

### 5.1 グローバル状態（Zustand）

```
authStore:
- user: User | null
- isAuthenticated: boolean
- login(email, password): Promise<void>
- logout(): void
- refreshToken(): Promise<void>

portfolioStore:
- portfolios: Portfolio[]
- selectedPortfolio: Portfolio | null
- totalAssets: number
- todayPnL: number
- fetchPortfolios(): Promise<void>
- selectPortfolio(id): void

websocketStore:
- isConnected: boolean
- reconnectAttempts: number
- connect(): void
- disconnect(): void
- subscribe(event, callback): void
- unsubscribe(event, callback): void
```

### 5.2 サーバー状態（TanStack Query）

```
キャッシュ戦略:
- ユーザー情報: 5分
- ポートフォリオ: 1分
- 価格データ: キャッシュなし（リアルタイム）
- AI判断: 30秒
- バックテスト結果: 無期限

無効化トリガー:
- 取引実行後: portfolios, trades
- 設定変更後: user, portfolios
```

## 6. UI/UX ガイドライン

### 6.1 デザイントークン

```
カラーパレット:
- Primary: #1976D2 (青)
- Secondary: #424242 (グレー)
- Success: #4CAF50 (緑)
- Error: #F44336 (赤)
- Warning: #FF9800 (オレンジ)
- Background: #F5F5F5
- Surface: #FFFFFF

タイポグラフィ:
- Font Family: 'Inter', 'Noto Sans JP'
- Heading1: 32px / Bold
- Heading2: 24px / SemiBold
- Body: 16px / Regular
- Caption: 14px / Regular

スペーシング:
- xs: 4px
- sm: 8px
- md: 16px
- lg: 24px
- xl: 32px

ブレークポイント:
- Mobile: < 640px
- Tablet: 640px - 1024px
- Desktop: > 1024px
```

### 6.2 インタラクション

```
アニメーション:
- Duration: 200ms (通常), 300ms (複雑)
- Easing: cubic-bezier(0.4, 0, 0.2, 1)
- 価格更新: フェード + 色変化
- ページ遷移: スライド
- モーダル: フェード + スケール

フィードバック:
- ローディング: スケルトンスクリーン
- エラー: トースト通知（右上）
- 成功: トースト通知（右上）
- 確認: モーダルダイアログ

リアルタイム更新:
- 価格変更: 背景色フラッシュ（緑/赤）
- 新規データ: スライドイン
- 接続状態: パルスアニメーション
```

### 6.3 レスポンシブ対応

```
モバイル最適化:
- タッチターゲット: 最小44x44px
- スワイプジェスチャー対応
- 縦画面/横画面対応
- ボトムナビゲーション採用

タブレット:
- 2カラムレイアウト
- サイドバー折りたたみ可能
- タッチ/マウス両対応

デスクトップ:
- 3カラムレイアウト
- キーボードショートカット
- ホバーエフェクト
- 右クリックメニュー
```

## 7. パフォーマンス要件

### 7.1 目標指標

```
Core Web Vitals:
- LCP (Largest Contentful Paint): < 2.5s
- INP (Interaction to Next Paint): < 200ms
- CLS (Cumulative Layout Shift): < 0.1
- TTFB (Time to First Byte): < 600ms

カスタム指標:
- 初回表示時間: < 3s
- ページ遷移: < 500ms
- WebSocket再接続: < 2s
- API応答時間: < 1s
```

### 7.2 最適化戦略

```
バンドルサイズ:
- 初期バンドル: < 200KB
- チャンクサイズ: < 100KB
- 画像最適化: WebP形式、遅延読み込み

キャッシュ:
- 静的アセット: 1年
- API応答: 状況に応じて設定
- Service Worker活用

レンダリング:
- SSG: 静的ページ
- SSR: 認証必須ページ
- CSR: ダッシュボード内部
- Suspense活用
- RSC: 初期データはサーバー側で取得しハイドレーションを軽量化

チャート最適化:
- Recharts は dynamic import でオンデマンド読込（チャート使用ページのみ）
- AI/バックテストのチャート画像は CDN/キャッシュヘッダで再利用
- WebSocket 更新は差分更新/スロットリング
```

## 8. セキュリティ要件

### 8.1 認証・認可

```
実装項目:
- Supabase セッション検証（@supabase/ssr）
- Cookie（HttpOnly / SameSite=strict）運用
- XSS対策（入力値サニタイズ）
- HTTPSの強制
- セキュアクッキー
- レート制限

権限管理:
- Supabase のユーザーメタデータ/カスタムクレームに基づく RBAC
- Next.js の middleware.ts でルート保護
```

### 8.2 データ保護

```
取り扱い:
- 個人情報の暗号化
- APIキーの環境変数管理
- 機密情報のマスキング
- ログからの個人情報除外
```

## 9. エラーハンドリング

### 9.1 エラー種別と対応

```
ネットワークエラー:
- 自動リトライ（3回まで）
- オフライン検知
- 代替UIの表示

認証エラー:
- トークン自動更新
- ログイン画面へリダイレクト
- セッション期限通知

バリデーションエラー:
- インラインエラー表示
- フォーカス移動
- 具体的なエラーメッセージ

システムエラー:
- エラーバウンダリー
- フォールバックUI
- エラー報告機能
```

## 10. テスト要件

### 10.1 テストカバレッジ目標

```
単体テスト: 80%以上
統合テスト: 主要フロー100%
E2Eテスト: クリティカルパス100%
```

### 10.2 テスト項目

```
コンポーネント:
- レンダリング
- ユーザーインタラクション
- 状態変更
- エラー状態

API連携:
- 正常系
- エラー系
- タイムアウト
- リトライ

WebSocket:
- 接続/切断
- 再接続
- メッセージ送受信
```

## 11. 開発環境セットアップ

### 11.1 必要ツール

```
Node.js: v20.x LTS
npm/yarn/pnpm: 最新版
VSCode推奨拡張機能:
- ESLint
- Prettier
- Tailwind CSS IntelliSense
- Playwright Test
- Testing Library
```

### 11.2 環境変数

```
NEXT_PUBLIC_API_URL=
NEXT_PUBLIC_WS_URL=
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```

## 12. デプロイメント

### 12.1 ビルド設定

```
本番ビルド:
- 環境変数の設定
- TypeScriptの型チェック
- ESLintチェック
- 最適化ビルド
```

### 12.2 Vercel 設定

```
Framework Preset: Next.js
Build Command: npm run build
Output Directory: .next
Environment Variables: 本番用設定
備考: WebSocket は Cloud Run（FastAPI）で提供。CORS / Allowed Origins / 認証ヘッダは Cloud Run 側で設定。
```

---

# 株式自動売買管理システム - バックエンド開発指示書

## 1. プロジェクト概要

### 1.1 システム全体像

- **目的**: 株式自動売買のビジネスロジック処理、AI 判断、データ管理
- **役割**: API 提供、リアルタイムデータ配信、外部 API 連携、AI 処理
- **クライアント**: フロントエンド（Next.js）、将来的にモバイルアプリ

### 1.2 技術スタック

- **フレームワーク**: FastAPI 0.100+
- **言語**: Python 3.12
- **AI 処理**: LangGraph + LangChain
- **非同期処理**: asyncio + aiohttp
- **WebSocket**: FastAPI WebSocket + Redis Pub/Sub
- **データベース**: Supabase (PostgreSQL)
- **ORM**: SQLAlchemy 2.0 (async)
- **キャッシュ**: Redis
- **タスクキュー**: Celery + Redis
- **監視**: Prometheus + Grafana
- **ログ**: structlog
- **コンテナ**: Docker

## 2. プロジェクト構造

### 2.1 ディレクトリ構成（最新版）

```
api/                                   # バックエンド (FastAPI)
├── app/
│   ├── __init__.py
│   ├── main.py                       # FastAPIアプリケーション
│   ├── config.py                     # 設定管理（環境変数）
│   ├── dependencies.py               # 共通依存性注入
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py                   # Supabase認証ミドルウェア
│   │   ├── cors.py                   # CORS設定
│   │   ├── logging.py                # 構造化ログ
│   │   ├── rate_limit.py             # レート制限
│   │   └── error_handler.py          # エラーハンドリング
│   ├── api/                          # APIエンドポイント
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py             # メインルーター
│   │       ├── auth.py               # 認証エンドポイント（オプション）
│   │       ├── portfolios.py         # ポートフォリオAPI
│   │       ├── trades.py             # 取引API
│   │       ├── ai_analysis.py        # AI分析API
│   │       ├── backtest.py           # バックテストAPI
│   │       ├── market.py             # 市場データAPI
│   │       ├── websocket.py          # WebSocket API
│   │       ├── admin.py              # 管理者API
│   │       └── charts.py             # チャート画像生成API
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py               # セキュリティ関連
│   │   ├── database.py               # データベース接続（Supabase）
│   │   ├── redis_client.py           # Redis接続（キャッシュ）
│   │   ├── exceptions.py             # カスタム例外
│   │   └── websocket_manager.py      # WebSocket接続管理
│   ├── models/                       # SQLAlchemyモデル
│   │   ├── __init__.py
│   │   ├── base.py                   # ベースモデル
│   │   ├── user.py                   # ユーザーモデル
│   │   ├── portfolio.py              # ポートフォリオモデル
│   │   ├── trade.py                  # 取引モデル
│   │   ├── ai_decision.py            # AI判断モデル
│   │   ├── backtest.py               # バックテストモデル
│   │   └── market_data.py            # 市場データモデル
│   ├── schemas/                      # Pydanticスキーマ
│   │   ├── __init__.py
│   │   ├── base.py                   # ベーススキーマ
│   │   ├── auth.py                   # 認証スキーマ
│   │   ├── portfolio.py              # ポートフォリオスキーマ
│   │   ├── trade.py                  # 取引スキーマ
│   │   ├── ai_decision.py            # AI判断スキーマ
│   │   ├── backtest.py               # バックテストスキーマ
│   │   ├── websocket.py              # WebSocketメッセージスキーマ
│   │   └── chart.py                  # チャート関連スキーマ
│   ├── services/                     # ビジネスロジック
│   │   ├── __init__.py
│   │   ├── auth_service.py           # 認証サービス
│   │   ├── portfolio_service.py      # ポートフォリオサービス
│   │   ├── trading_service.py        # 取引実行サービス
│   │   ├── market_data_service.py    # 市場データサービス
│   │   ├── ai_service.py             # AI処理サービス
│   │   ├── backtest_service.py       # バックテストサービス
│   │   ├── notification_service.py   # 通知サービス
│   │   └── websocket_service.py      # WebSocket配信サービス
│   ├── external/                     # 外部API連携
│   │   ├── __init__.py
│   │   ├── tachibana_api.py          # 立花証券API
│   │   ├── yfinance_api.py           # yfinance API
│   │   ├── openai_client.py          # OpenAI API
│   │   ├── gemini_client.py          # Gemini API
│   │   └── base_client.py            # 外部APIベースクライアント
│   ├── langgraph/                    # LangGraph AI処理
│   │   ├── __init__.py
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── market_analyzer.py    # 市場分析エージェント
│   │   │   ├── technical_analyzer.py # テクニカル分析エージェント
│   │   │   ├── chart_generator.py    # チャート生成エージェント
│   │   │   └── decision_maker.py     # 判断決定エージェント
│   │   ├── chains/
│   │   │   ├── __init__.py
│   │   │   └── trading_chain.py      # 取引判断チェーン
│   │   ├── workflows/
│   │   │   ├── __init__.py
│   │   │   └── analysis_workflow.py  # 分析ワークフロー
│   │   └── state.py                  # ワークフロー状態定義
│   ├── tasks/                        # Celeryタスク
│   │   ├── __init__.py
│   │   ├── celery_app.py             # Celery設定
│   │   ├── market_tasks.py           # 市場データ更新タスク
│   │   ├── analysis_tasks.py         # AI分析タスク
│   │   ├── notification_tasks.py     # 通知タスク
│   │   └── backtest_tasks.py         # バックテスト実行タスク
│   └── utils/                        # ユーティリティ
│       ├── __init__.py
│       ├── chart_generator.py        # matplotlib/mplfinanceチャート生成
│       ├── indicators.py             # テクニカル指標計算
│       ├── validators.py             # バリデーション関数
│       ├── formatters.py             # データフォーマット
│       ├── logger.py                 # ログ設定
│       └── cache.py                  # キャッシュユーティリティ
├── migrations/                       # データベースマイグレーション
│   ├── alembic.ini                   # Alembic設定
│   ├── env.py                        # マイグレーション環境
│   └── versions/                     # マイグレーションファイル
├── tests/                            # テスト
│   ├── __init__.py
│   ├── conftest.py                   # pytest設定
│   ├── unit/                         # 単体テスト
│   │   ├── test_services/
│   │   ├── test_models/
│   │   └── test_utils/
│   ├── integration/                  # 統合テスト
│   │   ├── test_api/
│   │   └── test_websocket/
│   └── e2e/                         # E2Eテスト
│       └── test_trading_flow.py
├── scripts/                         # スクリプト
│   ├── init_db.py                   # データベース初期化
│   ├── seed_data.py                 # テストデータ投入
│   └── start_services.py            # サービス開始
├── docker/
│   ├── Dockerfile                   # 本番用Docker
│   ├── Dockerfile.dev               # 開発用Docker
│   ├── docker-compose.yml           # 開発環境
│   └── docker-compose.prod.yml      # 本番環境
├── requirements/
│   ├── base.txt                     # 基本パッケージ
│   ├── dev.txt                      # 開発用パッケージ
│   └── prod.txt                     # 本番用パッケージ
├── .env.example                     # 環境変数サンプル
├── pyproject.toml                   # Python設定
└── README.md
```

## 3. API 仕様

### 3.1 エンドポイント詳細

#### 認証 API

```
POST /api/v1/auth/register
Request:
{
  "email": "string",
  "password": "string",
  "password_confirm": "string"
}
Response:
{
  "user_id": "uuid",
  "email": "string",
  "created_at": "datetime"
}

POST /api/v1/auth/login
Request:
{
  "email": "string",
  "password": "string"
}
Response:
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer",
  "expires_in": 3600
}

POST /api/v1/auth/refresh
Request:
{
  "refresh_token": "string"
}
Response:
{
  "access_token": "string",
  "refresh_token": "string"
}

POST /api/v1/auth/logout
Headers: Authorization: Bearer {token}
Response: 204 No Content
```

#### ポートフォリオ API

```
GET /api/v1/portfolios
Headers: Authorization: Bearer {token}
Query Parameters:
  - page: int (default: 1)
  - limit: int (default: 10)
Response:
{
  "items": [Portfolio],
  "total": int,
  "page": int,
  "pages": int
}

GET /api/v1/portfolios/{portfolio_id}
Response: Portfolio

POST /api/v1/portfolios
Request:
{
  "name": "string",
  "initial_capital": float,
  "description": "string"
}
Response: Portfolio

PUT /api/v1/portfolios/{portfolio_id}
Request: Partial Portfolio
Response: Portfolio

DELETE /api/v1/portfolios/{portfolio_id}
Response: 204 No Content

GET /api/v1/portfolios/{portfolio_id}/performance
Response:
{
  "total_return": float,
  "daily_return": float,
  "monthly_return": float,
  "win_rate": float,
  "sharpe_ratio": float,
  "max_drawdown": float
}
```

#### 取引 API

```
GET /api/v1/trades
Query Parameters:
  - portfolio_id: uuid
  - symbol: string
  - start_date: date
  - end_date: date
  - page: int
  - limit: int
Response: Paginated Trades

POST /api/v1/trades
Request:
{
  "portfolio_id": "uuid",
  "symbol": "string",
  "action": "buy|sell",
  "quantity": int,
  "price": float,
  "order_type": "market|limit",
  "ai_decision_id": "uuid"
}
Response: Trade

GET /api/v1/trades/{trade_id}
Response: Trade

PUT /api/v1/trades/{trade_id}/cancel
Response: Trade
```

#### AI 分析 API

```
POST /api/v1/ai/analyze
Request:
{
  "symbol": "string",
  "timeframes": ["1m", "5m", "1h", "4h"],
  "providers": ["gpt-5", "gemini-2.5"],
  "indicators": ["RSI", "MACD", "BB"]
}
Response:
{
  "decision_id": "uuid",
  "symbol": "string",
  "decision": "buy|sell|hold",
  "confidence": float,
  "reasoning": "string",
  "chart_url": "string",
  "indicators": object,
  "timestamp": "datetime"
}

GET /api/v1/ai/decisions
Query Parameters:
  - symbol: string
  - start_date: datetime
  - end_date: datetime
  - provider: string
Response: Paginated AI Decisions

GET /api/v1/ai/decisions/{decision_id}
Response: AI Decision with full details
```

#### バックテスト API

```
POST /api/v1/backtest/run
Request:
{
  "strategy": "string",
  "symbols": ["string"],
  "start_date": "date",
  "end_date": "date",
  "initial_capital": float,
  "ai_providers": ["string"],
  "parameters": object
}
Response:
{
  "backtest_id": "uuid",
  "status": "pending|running|completed|failed",
  "created_at": "datetime"
}

GET /api/v1/backtest/results/{backtest_id}
Response:
{
  "backtest_id": "uuid",
  "status": "string",
  "summary": {
    "total_return": float,
    "win_rate": float,
    "total_trades": int,
    "sharpe_ratio": float,
    "max_drawdown": float
  },
  "trades": [Trade],
  "equity_curve": [DataPoint],
  "monthly_returns": object
}

GET /api/v1/backtest/status/{backtest_id}
Response:
{
  "status": "string",
  "progress": float,
  "current_date": "date",
  "estimated_completion": "datetime"
}
```

#### 市場データ API

```
GET /api/v1/market/prices
Query Parameters:
  - symbols: string (comma-separated)
Response:
{
  "prices": {
    "symbol": {
      "current": float,
      "change": float,
      "change_percent": float,
      "volume": int,
      "timestamp": "datetime"
    }
  }
}

GET /api/v1/market/indicators/{symbol}
Query Parameters:
  - timeframe: string
  - indicators: string (comma-separated)
Response:
{
  "symbol": "string",
  "timeframe": "string",
  "indicators": {
    "RSI": float,
    "MACD": object,
    "BB": object
  }
}

GET /api/v1/market/chart/{symbol}
Query Parameters:
  - timeframes: string (comma-separated)
  - width: int
  - height: int
Response: Image binary or URL
```

#### 管理者 API

```
GET /api/v1/admin/users
Headers: Authorization: Bearer {admin_token}
Response: Paginated Users

PUT /api/v1/admin/users/{user_id}
Request:
{
  "role": "user|admin",
  "is_active": boolean
}
Response: User

GET /api/v1/admin/metrics
Response:
{
  "active_users": int,
  "total_trades": int,
  "total_volume": float,
  "api_calls": object,
  "error_rate": float,
  "system_status": object
}

GET /api/v1/admin/ai-usage
Response:
{
  "providers": {
    "provider_name": {
      "calls": int,
      "cost": float,
      "success_rate": float
    }
  }
}
```

### 3.2 WebSocket 仕様

#### 接続管理

```python
接続URL: ws://localhost:8000/ws/{user_id}

認証:
- クエリパラメータでトークンを送信
- 接続後の最初のメッセージで認証

接続維持:
- 30秒ごとにping/pong
- 自動再接続機能
```

#### イベント仕様

```python
# サーバー → クライアント

価格更新:
{
  "event": "price_update",
  "data": {
    "symbol": "7203",
    "price": 2345.00,
    "change": 23.00,
    "change_percent": 1.02,
    "volume": 1234567,
    "timestamp": "2024-01-01T12:00:00Z"
  }
}

ポートフォリオ更新:
{
  "event": "portfolio_update",
  "data": {
    "portfolio_id": "uuid",
    "total_assets": 5234500,
    "daily_pnl": 123400,
    "daily_pnl_percent": 2.41,
    "positions": [...]
  }
}

AI判断通知:
{
  "event": "ai_decision",
  "data": {
    "symbol": "7203",
    "decision": "buy",
    "confidence": 0.85,
    "provider": "gpt-5",
    "reasoning": "...",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}

取引実行通知:
{
  "event": "trade_executed",
  "data": {
    "trade_id": "uuid",
    "symbol": "7203",
    "action": "buy",
    "quantity": 100,
    "price": 2345.00,
    "timestamp": "2024-01-01T12:00:00Z"
  }
}

システム通知:
{
  "event": "system_notification",
  "data": {
    "type": "info|warning|error",
    "message": "string",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}

# クライアント → サーバー

購読リクエスト:
{
  "action": "subscribe",
  "channels": ["prices", "portfolio", "ai_decisions"],
  "symbols": ["7203", "9984"]
}

購読解除:
{
  "action": "unsubscribe",
  "channels": ["prices"],
  "symbols": ["7203"]
}
```

## 4. データベース設計

### 4.1 テーブル定義

```sql
-- ユーザーテーブル
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);

-- ポートフォリオテーブル
CREATE TABLE portfolios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    initial_capital DECIMAL(15,2) NOT NULL,
    current_balance DECIMAL(15,2) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, name)
);

-- 取引テーブル
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol VARCHAR(10) NOT NULL,
    action VARCHAR(10) NOT NULL CHECK (action IN ('buy', 'sell')),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    price DECIMAL(10,2) NOT NULL,
    commission DECIMAL(10,2) DEFAULT 0,
    order_type VARCHAR(20) DEFAULT 'market',
    status VARCHAR(20) DEFAULT 'pending',
    ai_decision_id UUID REFERENCES ai_decisions(id),
    executed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    profit_loss DECIMAL(10,2),
    INDEX idx_portfolio_symbol (portfolio_id, symbol),
    INDEX idx_executed_at (executed_at)
);

-- AI判断テーブル
CREATE TABLE ai_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(10) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    decision VARCHAR(10) NOT NULL CHECK (decision IN ('buy', 'sell', 'hold')),
    confidence DECIMAL(3,2) CHECK (confidence >= 0 AND confidence <= 1),
    chart_image_url TEXT,
    technical_indicators JSONB,
    reasoning TEXT,
    model_version VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    INDEX idx_symbol_created (symbol, created_at DESC)
);

-- バックテスト結果テーブル
CREATE TABLE backtest_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    strategy_name VARCHAR(100) NOT NULL,
    symbols TEXT[] NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_capital DECIMAL(15,2) NOT NULL,
    final_capital DECIMAL(15,2),
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    win_rate DECIMAL(5,2),
    total_return DECIMAL(10,2),
    max_drawdown DECIMAL(5,2),
    sharpe_ratio DECIMAL(5,2),
    parameters JSONB,
    equity_curve JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ウォッチリストテーブル
CREATE TABLE watchlist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(10) NOT NULL,
    notes TEXT,
    alert_price DECIMAL(10,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, symbol)
);

-- APIキー管理テーブル
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    encrypted_key TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, provider)
);

-- 監査ログテーブル
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    INDEX idx_user_created (user_id, created_at DESC)
);
```

### 4.2 インデックス戦略

```sql
-- パフォーマンス最適化のためのインデックス
CREATE INDEX idx_trades_portfolio_date ON trades(portfolio_id, executed_at DESC);
CREATE INDEX idx_trades_symbol_date ON trades(symbol, executed_at DESC);
CREATE INDEX idx_ai_decisions_symbol ON ai_decisions(symbol, created_at DESC);
CREATE INDEX idx_ai_decisions_provider ON ai_decisions(provider, created_at DESC);
CREATE INDEX idx_backtest_user_status ON backtest_results(user_id, status);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, created_at DESC);
```

## 5. LangGraph 実装設計

### 5.1 エージェント構成

```python
# 市場分析エージェント
class MarketAnalyzerAgent:
    """
    役割: 市場データの収集と基本分析
    入力: 銘柄コード、期間
    出力: 価格データ、出来高、基本統計
    """

# テクニカル分析エージェント
class TechnicalAnalyzerAgent:
    """
    役割: テクニカル指標の計算と解釈
    入力: 価格データ、指標リスト
    出力: 指標値、シグナル、トレンド判定
    """

# チャート生成エージェント
class ChartGeneratorAgent:
    """
    役割: チャート画像の生成
    入力: 価格データ、時間軸
    出力: チャート画像URL、画像バイナリ
    """

# AI判断エージェント
class AIDecisionAgent:
    """
    役割: 複数AIプロバイダーでの判断
    入力: チャート画像、テクニカル指標
    出力: 売買判断、信頼度、理由
    """

# 意思決定エージェント
class DecisionMakerAgent:
    """
    役割: 最終的な取引判断
    入力: 複数AI判断、リスク設定
    出力: 最終判断、実行推奨度
    """
```

### 5.2 ワークフロー定義

```python
# 分析ワークフロー
trading_workflow = StateGraph(TradingState)

# ノード追加
trading_workflow.add_node("fetch_data", fetch_market_data)
trading_workflow.add_node("calculate_indicators", calculate_technical_indicators)
trading_workflow.add_node("generate_charts", generate_chart_images)
trading_workflow.add_node("ai_analysis", run_ai_analysis)
trading_workflow.add_node("aggregate_decisions", aggregate_ai_decisions)
trading_workflow.add_node("final_decision", make_final_decision)

# エッジ定義
trading_workflow.add_edge("fetch_data", "calculate_indicators")
trading_workflow.add_edge("fetch_data", "generate_charts")
trading_workflow.add_edge("calculate_indicators", "ai_analysis")
trading_workflow.add_edge("generate_charts", "ai_analysis")
trading_workflow.add_conditional_edges(
    "ai_analysis",
    lambda x: "aggregate" if len(x["ai_results"]) > 1 else "decide",
    {
        "aggregate": "aggregate_decisions",
        "decide": "final_decision"
    }
)
trading_workflow.add_edge("aggregate_decisions", "final_decision")

# エントリーポイント
trading_workflow.set_entry_point("fetch_data")
```

## 6. 外部 API 連携

### 6.1 立花証券 API

```python
# 認証フロー
1. OAuth2.0認証
2. アクセストークン取得
3. リフレッシュトークン管理

# エンドポイント
- 注文発注: POST /orders
- 注文取消: DELETE /orders/{order_id}
- 残高照会: GET /accounts/balance
- 約定照会: GET /executions
- 銘柄情報: GET /symbols/{symbol}

# レート制限
- 1秒あたり10リクエスト
- 1日あたり10,000リクエスト

# エラーハンドリング
- 自動リトライ（最大3回）
- エクスポネンシャルバックオフ
- 緊急停止機能
```

### 6.2 yfinance API

```python
# データ取得
- 価格データ: download()
- リアルタイム: Ticker.info
- 履歴データ: Ticker.history()

# 制限事項
- 無料枠: 制限なし（ただし頻度制限あり）
- データ遅延: 15分（無料版）

# キャッシュ戦略
- 日足: 24時間キャッシュ
- 分足: キャッシュなし
```

### 6.3 AI Provider APIs

```python
# OpenAI (GPT-5)
- エンドポイント: /v1/chat/completions
- モデル: gpt-5-turbo
- 画像入力: Vision API
- レート制限: 10,000 TPM
- コスト: $0.01/1K tokens

# Google Gemini
- エンドポイント: /v1beta/models/gemini-2.5-flash:generateContent
- マルチモーダル対応
- レート制限: 60 RPM
- コスト: $0.0001/1K characters

# プロンプト戦略
- チャート画像 + テクニカル指標
- 構造化出力（JSON）
- Few-shot examples
```

## 7. リアルタイム処理

### 7.1 WebSocket 実装

```python
# 接続管理
class ConnectionManager:
    - active_connections: Dict[str, WebSocket]
    - user_subscriptions: Dict[str, Set[str]]
    - heartbeat_interval: 30秒

    Methods:
    - connect(websocket, user_id)
    - disconnect(user_id)
    - broadcast(message, channel)
    - send_personal(message, user_id)
```

### 7.2 Redis Pub/Sub

```python
# チャンネル設計
channels:
- price:{symbol} - 価格更新
- portfolio:{user_id} - ポートフォリオ更新
- ai_decision:{symbol} - AI判断
- trade:{user_id} - 取引通知
- system:broadcast - システム通知

# メッセージフォーマット
{
  "channel": "string",
  "event": "string",
  "data": object,
  "timestamp": "ISO8601"
}
```

## 8. バックグラウンドタスク

### 8.1 Celery タスク

```python
# 定期タスク
- 価格データ更新: 1分ごと
- AI分析実行: 5分ごと
- ポートフォリオ評価: 1時間ごと
- バックテスト実行: オンデマンド
- レポート生成: 日次

# タスク優先度
- HIGH: 取引実行、価格更新
- MEDIUM: AI分析、通知
- LOW: レポート生成、バックテスト
```

### 8.2 スケジューリング

```python
# Celery Beat設定
CELERYBEAT_SCHEDULE = {
    'update-prices': {
        'task': 'tasks.update_market_prices',
        'schedule': crontab(minute='*'),
    },
    'run-ai-analysis': {
        'task': 'tasks.run_ai_analysis',
        'schedule': crontab(minute='*/5'),
    },
    'daily-report': {
        'task': 'tasks.generate_daily_report',
        'schedule': crontab(hour=18, minute=0),
    }
}
```

## 9. セキュリティ実装

### 9.1 認証・認可

```python
# JWT設定
- アルゴリズム: RS256
- Access Token: 1時間
- Refresh Token: 30日
- Token Rotation: 有効

# 権限管理
Roles:
- user: 基本機能
- premium: 高度な機能
- admin: 管理機能

Permissions:
- portfolio:read
- portfolio:write
- trade:execute
- backtest:run
- admin:users
```

### 9.2 データ保護

```python
# 暗号化
- APIキー: AES-256-GCM
- パスワード: bcrypt (cost=12)
- 通信: TLS 1.3

# 入力検証
- SQLインジェクション対策
- XSS対策
- CSRF対策
- レート制限
```

## 10. パフォーマンス最適化

### 10.1 キャッシュ戦略

```python
# Redisキャッシュ
cache_config = {
    "market_prices": {"ttl": 60},  # 1分
    "technical_indicators": {"ttl": 300},  # 5分
    "ai_decisions": {"ttl": 1800},  # 30分
    "user_portfolio": {"ttl": 300},  # 5分
    "backtest_results": {"ttl": 86400}  # 1日
}
```

### 10.2 データベース最適化

```python
# コネクションプール
- min_size: 10
- max_size: 50
- max_queries: 50000
- max_inactive_connection_lifetime: 300

# クエリ最適化
- N+1問題対策
- バッチ処理
- 非同期処理
- パーティショニング（取引テーブル）
```

## 11. モニタリング・ログ

### 11.1 メトリクス

```python
# Prometheus メトリクス
- API応答時間
- エラー率
- アクティブ接続数
- タスクキュー長
- AI API使用量
- データベース接続数
```

### 11.2 ログ設計

```python
# ログレベル
- ERROR: システムエラー、例外
- WARNING: 異常値、閾値超過
- INFO: 取引実行、API呼び出し
- DEBUG: 詳細情報

# ログフォーマット
{
  "timestamp": "ISO8601",
  "level": "string",
  "service": "string",
  "user_id": "uuid",
  "trace_id": "uuid",
  "message": "string",
  "extra": object
}
```

## 12. エラーハンドリング

### 12.1 エラー分類

```python
# ビジネスエラー
- InsufficientBalance: 残高不足
- InvalidSymbol: 無効な銘柄
- MarketClosed: 市場時間外
- RateLimitExceeded: レート制限

# システムエラー
- DatabaseError: DB接続エラー
- ExternalAPIError: 外部API エラー
- AIProviderError: AI API エラー

# バリデーションエラー
- ValidationError: 入力値エラー
- AuthenticationError: 認証エラー
- PermissionError: 権限エラー
```

### 12.2 リトライ戦略

```python
# リトライ設定
retry_config = {
    "max_attempts": 3,
    "backoff_factor": 2,
    "max_backoff": 60,
    "retry_on": [
        ConnectionError,
        TimeoutError,
        ExternalAPIError
    ]
}
```

## 13. テスト戦略

### 13.1 テストカバレッジ

```
目標カバレッジ:
- ユニットテスト: 80%
- 統合テスト: 60%
- E2Eテスト: クリティカルパス100%
```

### 13.2 テスト環境

```python
# テストデータベース
- PostgreSQL (Docker)
- テストデータシーダー
- トランザクションロールバック

# モック
- 外部API モック
- Redis モック
- WebSocket モック
```

## 14. デプロイメント

### 14.1 Docker 構成

```yaml
services:
  api:
    - FastAPI アプリケーション
    - Uvicorn サーバー
    - 自動再起動

  celery:
    - Celery ワーカー
    - Celery Beat

  redis:
    - キャッシュ
    - Pub/Sub
    - Celery ブローカー

  nginx:
    - リバースプロキシ
    - SSL終端
    - 静的ファイル配信
```

### 14.2 環境変数

```
# データベース
DATABASE_URL=
REDIS_URL=

# 認証
JWT_SECRET_KEY=
JWT_ALGORITHM=

# 外部API
TACHIBANA_API_KEY=
OPENAI_API_KEY=
GEMINI_API_KEY=

# 監視
SENTRY_DSN=
```

## 15. 開発ガイドライン

### 15.1 コーディング規約

```python
# スタイルガイド
- PEP 8準拠
- Black フォーマッター
- isort インポート整理
- mypy 型チェック

# 命名規則
- snake_case: 変数、関数
- PascalCase: クラス
- UPPER_CASE: 定数
```

### 15.2 Git ワークフロー

```
# ブランチ戦略
- main: 本番環境
- develop: 開発環境
- feature/*: 機能開発
- hotfix/*: 緊急修正

# コミットメッセージ
- feat: 新機能
- fix: バグ修正
- docs: ドキュメント
- refactor: リファクタリング
- test: テスト
```

## 16. 連携仕様（フロントエンド向け）

### 16.1 API 呼び出し規約

- 全 API に Bearer 認証が必要
- エラーレスポンスは統一フォーマット
- ページネーションは統一パラメータ
- 日時は ISO 8601 形式

### 16.2 WebSocket 接続手順

1. JWT トークンで認証
2. ユーザー ID でコネクション確立
3. チャンネル購読
4. ハートビート維持

### 16.3 エラーコード一覧

- 400: バリデーションエラー
- 401: 認証エラー
- 403: 権限エラー
- 404: リソース不在
- 429: レート制限
- 500: サーバーエラー
