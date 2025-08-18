import { AISettingsManager } from '@/components/admin/AISettingsManager'

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold" style={{ color: 'var(--kb-text)' }}>
            システム設定
          </h2>
          <p className="text-sm mt-1" style={{ color: 'var(--kb-text-muted)' }}>
            AI設定とシステム構成の管理
          </p>
        </div>
      </div>

      <AISettingsManager />
    </div>
  )
}