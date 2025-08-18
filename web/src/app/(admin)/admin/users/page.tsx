import { UserManagementTable } from '@/components/admin/UserManagementTable'

export default function UsersPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold" style={{ color: 'var(--kb-text)' }}>
            ユーザー管理
          </h2>
          <p className="text-sm mt-1" style={{ color: 'var(--kb-text-muted)' }}>
            システム利用者のアカウント管理と権限設定
          </p>
        </div>
      </div>

      <UserManagementTable />
    </div>
  )
}