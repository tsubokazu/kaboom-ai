'use client'

import { useState } from 'react'
import { Card } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { 
  MagnifyingGlassIcon,
  UserIcon,
  PencilIcon,
  LockClosedIcon,
  LockOpenIcon
} from '@heroicons/react/24/outline'

interface User {
  id: string
  email: string
  name: string
  role: 'user' | 'admin'
  status: 'active' | 'suspended' | 'pending'
  createdAt: string
  lastLogin: string
  totalTrades: number
  totalVolume: number
}

export function UserManagementTable() {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedRole, setSelectedRole] = useState<string>('all')
  const [selectedStatus, setSelectedStatus] = useState<string>('all')

  // モックユーザーデータ
  const mockUsers: User[] = [
    {
      id: 'U-1001',
      email: 'trader1@example.com',
      name: '田中太郎',
      role: 'user',
      status: 'active',
      createdAt: '2025-01-15',
      lastLogin: '2025-08-18',
      totalTrades: 127,
      totalVolume: 2500000
    },
    {
      id: 'U-1002',
      email: 'admin@kaboom.ai',
      name: '管理者',
      role: 'admin',
      status: 'active',
      createdAt: '2024-12-01',
      lastLogin: '2025-08-18',
      totalTrades: 0,
      totalVolume: 0
    },
    {
      id: 'U-1003',
      email: 'trader2@example.com',
      name: '佐藤花子',
      role: 'user',
      status: 'suspended',
      createdAt: '2025-02-01',
      lastLogin: '2025-08-15',
      totalTrades: 89,
      totalVolume: 1200000
    },
    {
      id: 'U-1004',
      email: 'newuser@example.com',
      name: '鈴木一郎',
      role: 'user',
      status: 'pending',
      createdAt: '2025-08-17',
      lastLogin: '-',
      totalTrades: 0,
      totalVolume: 0
    },
    {
      id: 'U-1005',
      email: 'protrader@example.com',
      name: '高橋美咲',
      role: 'user',
      status: 'active',
      createdAt: '2025-01-10',
      lastLogin: '2025-08-17',
      totalTrades: 234,
      totalVolume: 4200000
    },
    {
      id: 'U-1006',
      email: 'daytrader@example.com',
      name: '山田健太',
      role: 'user',
      status: 'active',
      createdAt: '2025-03-01',
      lastLogin: '2025-08-16',
      totalTrades: 345,
      totalVolume: 6800000
    }
  ]

  const filteredUsers = mockUsers.filter(user => {
    const matchesSearch = user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         user.id.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesRole = selectedRole === 'all' || user.role === selectedRole
    const matchesStatus = selectedStatus === 'all' || user.status === selectedStatus
    return matchesSearch && matchesRole && matchesStatus
  })

  const getStatusBadge = (status: User['status']) => {
    const variants = {
      active: { variant: 'success' as const, label: 'アクティブ' },
      suspended: { variant: 'error' as const, label: '停止中' },
      pending: { variant: 'warning' as const, label: '承認待ち' }
    }
    return variants[status]
  }

  const getRoleBadge = (role: User['role']) => {
    return role === 'admin' 
      ? { variant: 'primary' as const, label: '管理者' }
      : { variant: 'default' as const, label: 'ユーザー' }
  }

  const handleUserAction = (userId: string, action: 'edit' | 'suspend' | 'activate') => {
    // TODO: バックエンド統合時に実装
    console.log(`Action: ${action} for user: ${userId}`)
  }

  const formatVolume = (volume: number) => {
    return volume.toLocaleString('ja-JP') + '円'
  }

  return (
    <Card className="p-6">
      {/* 検索・フィルタ */}
      <div className="mb-6 flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4" 
                               style={{ color: 'var(--kb-text-muted)' }} />
          <Input
            type="text"
            placeholder="ユーザー名、メール、IDで検索"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
        <select
          value={selectedRole}
          onChange={(e) => setSelectedRole(e.target.value)}
          className="px-3 py-2 rounded-lg border text-sm"
          style={{ 
            background: 'var(--kb-bg-surface)', 
            borderColor: 'var(--kb-border)',
            color: 'var(--kb-text)'
          }}
        >
          <option value="all">すべての権限</option>
          <option value="user">ユーザー</option>
          <option value="admin">管理者</option>
        </select>
        <select
          value={selectedStatus}
          onChange={(e) => setSelectedStatus(e.target.value)}
          className="px-3 py-2 rounded-lg border text-sm"
          style={{ 
            background: 'var(--kb-bg-surface)', 
            borderColor: 'var(--kb-border)',
            color: 'var(--kb-text)'
          }}
        >
          <option value="all">すべてのステータス</option>
          <option value="active">アクティブ</option>
          <option value="suspended">停止中</option>
          <option value="pending">承認待ち</option>
        </select>
      </div>

      {/* ユーザーテーブル */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b" style={{ borderColor: 'var(--kb-border)' }}>
              <th className="text-left py-3 px-4 font-medium" style={{ color: 'var(--kb-text)' }}>
                ユーザー
              </th>
              <th className="text-left py-3 px-4 font-medium" style={{ color: 'var(--kb-text)' }}>
                権限
              </th>
              <th className="text-left py-3 px-4 font-medium" style={{ color: 'var(--kb-text)' }}>
                ステータス
              </th>
              <th className="text-left py-3 px-4 font-medium" style={{ color: 'var(--kb-text)' }}>
                取引実績
              </th>
              <th className="text-left py-3 px-4 font-medium" style={{ color: 'var(--kb-text)' }}>
                最終ログイン
              </th>
              <th className="text-left py-3 px-4 font-medium" style={{ color: 'var(--kb-text)' }}>
                アクション
              </th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.map((user) => {
              const statusBadge = getStatusBadge(user.status)
              const roleBadge = getRoleBadge(user.role)
              
              return (
                <tr key={user.id} className="border-b hover:bg-opacity-50" 
                    style={{ 
                      borderColor: 'var(--kb-border)',
                      background: 'transparent'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'var(--kb-bg-surface)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'transparent'
                    }}>
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full flex items-center justify-center" 
                           style={{ background: 'var(--kb-bg)' }}>
                        <UserIcon className="w-4 h-4" style={{ color: 'var(--kb-text-muted)' }} />
                      </div>
                      <div>
                        <div className="font-medium" style={{ color: 'var(--kb-text)' }}>
                          {user.name}
                        </div>
                        <div className="text-xs" style={{ color: 'var(--kb-text-muted)' }}>
                          {user.email}
                        </div>
                        <div className="text-xs" style={{ color: 'var(--kb-text-muted)' }}>
                          {user.id}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <Badge variant={roleBadge.variant}>
                      {roleBadge.label}
                    </Badge>
                  </td>
                  <td className="py-3 px-4">
                    <Badge variant={statusBadge.variant}>
                      {statusBadge.label}
                    </Badge>
                  </td>
                  <td className="py-3 px-4">
                    <div className="text-sm" style={{ color: 'var(--kb-text)' }}>
                      {user.totalTrades}回
                    </div>
                    <div className="text-xs" style={{ color: 'var(--kb-text-muted)' }}>
                      {formatVolume(user.totalVolume)}
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <div className="text-sm" style={{ color: 'var(--kb-text)' }}>
                      {user.lastLogin}
                    </div>
                    <div className="text-xs" style={{ color: 'var(--kb-text-muted)' }}>
                      登録: {user.createdAt}
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleUserAction(user.id, 'edit')}
                        className="p-1 rounded hover:bg-gray-100 transition-colors"
                        title="編集"
                      >
                        <PencilIcon className="w-4 h-4" style={{ color: 'var(--kb-text-muted)' }} />
                      </button>
                      {user.status === 'active' ? (
                        <button
                          onClick={() => handleUserAction(user.id, 'suspend')}
                          className="p-1 rounded hover:bg-gray-100 transition-colors"
                          title="停止"
                        >
                          <LockClosedIcon className="w-4 h-4 text-red-500" />
                        </button>
                      ) : (
                        <button
                          onClick={() => handleUserAction(user.id, 'activate')}
                          className="p-1 rounded hover:bg-gray-100 transition-colors"
                          title="有効化"
                        >
                          <LockOpenIcon className="w-4 h-4 text-green-500" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* 結果統計 */}
      <div className="mt-4 flex items-center justify-between text-sm" style={{ color: 'var(--kb-text-muted)' }}>
        <div>
          {filteredUsers.length} / {mockUsers.length} ユーザーを表示
        </div>
        <div>
          アクティブ: {filteredUsers.filter(u => u.status === 'active').length} |
          停止中: {filteredUsers.filter(u => u.status === 'suspended').length} |
          承認待ち: {filteredUsers.filter(u => u.status === 'pending').length}
        </div>
      </div>
    </Card>
  )
}