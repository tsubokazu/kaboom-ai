import { SystemLogs } from '@/components/admin/SystemLogs'

export default function LogsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold" style={{ color: 'var(--kb-text)' }}>
            ログ・監視
          </h2>
          <p className="text-sm mt-1" style={{ color: 'var(--kb-text-muted)' }}>
            システムログとアラートの管理・監視
          </p>
        </div>
      </div>

      <SystemLogs />
    </div>
  )
}