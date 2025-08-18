'use client'

import { Card } from '@/components/ui/Card'
import Link from 'next/link'
import { 
  UserGroupIcon, 
  ChartBarIcon, 
  CogIcon, 
  DocumentTextIcon,
  ArrowRightIcon,
  ServerIcon,
  ExclamationTriangleIcon,
  CloudArrowDownIcon
} from '@heroicons/react/24/outline'

export default function AdminPage() {
  const quickStats = [
    { label: 'アクティブユーザー', value: '124', change: '+12%', color: 'text-green-500' },
    { label: 'WebSocket接続', value: '89', change: '+5%', color: 'text-blue-500' },
    { label: 'API使用率', value: '67%', change: '-3%', color: 'text-orange-500' },
    { label: 'エラー率', value: '0.2%', change: '-0.1%', color: 'text-red-500' },
  ]

  const adminMenus = [
    {
      title: 'ユーザー管理',
      description: 'ユーザーアカウントの管理と権限設定',
      icon: UserGroupIcon,
      href: '/admin/users',
      stats: '124 users'
    },
    {
      title: 'システムメトリクス',
      description: 'パフォーマンス監視とシステム状態',
      icon: ChartBarIcon,
      href: '/admin/metrics',
      stats: '99.8% uptime'
    },
    {
      title: 'システム設定',
      description: 'AI設定とシステム構成管理',
      icon: CogIcon,
      href: '/admin/settings',
      stats: '3 providers'
    },
    {
      title: 'ログ・監視',
      description: 'システムログとアラート管理',
      icon: DocumentTextIcon,
      href: '/admin/logs',
      stats: '2 warnings'
    },
    {
      title: 'バックアップ・復元',
      description: 'データバックアップと復元管理',
      icon: CloudArrowDownIcon,
      href: '/admin/backup',
      stats: '5 backups'
    }
  ]

  const recentAlerts = [
    { 
      type: 'warning', 
      message: 'API使用量が上限に近づいています',
      time: '2分前',
      severity: 'medium'
    },
    { 
      type: 'info', 
      message: '新規ユーザー登録: user@example.com',
      time: '15分前',
      severity: 'low'
    },
    { 
      type: 'error', 
      message: 'AI分析でタイムアウトが発生',
      time: '1時間前',
      severity: 'high'
    }
  ]

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return 'text-red-500'
      case 'medium': return 'text-orange-500'
      default: return 'text-blue-500'
    }
  }

  const getSeverityIcon = (severity: string) => {
    if (severity === 'high') {
      return <ExclamationTriangleIcon className="w-4 h-4 text-red-500" />
    }
    return <ServerIcon className="w-4 h-4 text-blue-500" />
  }

  return (
    <div className="space-y-6">
      {/* クイック統計 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {quickStats.map((stat, index) => (
          <Card key={index} className="p-4">
            <div className="text-2xl font-bold" style={{ color: 'var(--kb-text)' }}>
              {stat.value}
            </div>
            <div className="text-sm" style={{ color: 'var(--kb-text-muted)' }}>
              {stat.label}
            </div>
            <div className={`text-xs mt-1 ${stat.color}`}>
              {stat.change}
            </div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 管理メニュー */}
        <div>
          <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--kb-text)' }}>
            管理機能
          </h2>
          <div className="grid gap-4">
            {adminMenus.map((menu, index) => (
              <Link key={index} href={menu.href}>
                <Card className="p-4 hover:shadow-md transition-shadow cursor-pointer">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <div className="p-2 rounded-lg" style={{ background: 'var(--kb-bg-surface)' }}>
                        <menu.icon className="w-5 h-5" style={{ color: 'var(--kb-primary)' }} />
                      </div>
                      <div className="flex-1">
                        <h3 className="font-medium" style={{ color: 'var(--kb-text)' }}>
                          {menu.title}
                        </h3>
                        <p className="text-sm mt-1" style={{ color: 'var(--kb-text-muted)' }}>
                          {menu.description}
                        </p>
                        <div className="text-xs mt-2" style={{ color: 'var(--kb-primary)' }}>
                          {menu.stats}
                        </div>
                      </div>
                    </div>
                    <ArrowRightIcon className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--kb-text-muted)' }} />
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        </div>

        {/* 最近のアラート */}
        <div>
          <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--kb-text)' }}>
            最近のアラート
          </h2>
          <Card className="p-4">
            <div className="space-y-3">
              {recentAlerts.map((alert, index) => (
                <div key={index} className="flex items-start gap-3 p-3 rounded-lg" style={{ background: 'var(--kb-bg)' }}>
                  {getSeverityIcon(alert.severity)}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm" style={{ color: 'var(--kb-text)' }}>
                      {alert.message}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`text-xs ${getSeverityColor(alert.severity)}`}>
                        {alert.severity === 'high' ? '緊急' : alert.severity === 'medium' ? '警告' : '情報'}
                      </span>
                      <span className="text-xs" style={{ color: 'var(--kb-text-muted)' }}>
                        {alert.time}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 pt-3 border-t border-gray-200">
              <Link 
                href="/admin/logs" 
                className="text-sm hover:underline"
                style={{ color: 'var(--kb-primary)' }}
              >
                すべてのログを見る →
              </Link>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}