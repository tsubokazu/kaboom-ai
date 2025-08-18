import { SystemMetrics } from '@/components/admin/SystemMetrics'

export default function MetricsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold" style={{ color: 'var(--kb-text)' }}>
            システムメトリクス
          </h2>
          <p className="text-sm mt-1" style={{ color: 'var(--kb-text-muted)' }}>
            システムパフォーマンスとリソース使用状況の監視
          </p>
        </div>
      </div>

      <SystemMetrics />
    </div>
  )
}