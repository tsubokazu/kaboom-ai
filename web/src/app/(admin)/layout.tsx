import { redirect } from 'next/navigation'

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode
}) {
  // TODO: バックエンド統合時に実際の権限チェックを実装
  const isAdmin = true // モック権限チェック

  if (!isAdmin) {
    redirect('/dashboard')
  }

  return (
    <div className="min-h-screen" style={{ background: 'var(--kb-bg)' }}>
      <header className="border-b" style={{ borderColor: 'var(--kb-border)', background: 'var(--kb-bg-surface)' }}>
        <div className="kb-container py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center" 
                   style={{ background: 'var(--kb-primary)' }}>
                <span className="text-white font-bold text-sm">A</span>
              </div>
              <div>
                <h1 className="font-semibold" style={{ color: 'var(--kb-text)' }}>
                  管理者パネル
                </h1>
                <p className="text-xs" style={{ color: 'var(--kb-text-muted)' }}>
                  Kaboom.ai Admin Dashboard
                </p>
              </div>
            </div>
            <div className="text-sm" style={{ color: 'var(--kb-text-muted)' }}>
              管理者としてログイン中
            </div>
          </div>
        </div>
      </header>
      <main className="kb-container py-6">
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold" style={{ color: 'var(--kb-text)' }}>
                管理者ダッシュボード
              </h1>
              <p className="text-sm mt-1" style={{ color: 'var(--kb-text-muted)' }}>
                システムの監視・管理を行います
              </p>
            </div>
          </div>
        </div>
        {children}
      </main>
    </div>
  )
}