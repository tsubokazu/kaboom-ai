import { BackupManager } from '@/components/admin/BackupManager'

export default function BackupPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold" style={{ color: 'var(--kb-text)' }}>
            バックアップ・復元
          </h2>
          <p className="text-sm mt-1" style={{ color: 'var(--kb-text-muted)' }}>
            データバックアップと復元の管理
          </p>
        </div>
      </div>

      <BackupManager />
    </div>
  )
}