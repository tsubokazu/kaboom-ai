'use client'

import { useState, useEffect } from 'react'
import { Card } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { 
  MagnifyingGlassIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  XCircleIcon,
  CheckCircleIcon,
  ClockIcon,
  ArrowDownTrayIcon
} from '@heroicons/react/24/outline'

interface LogEntry {
  id: string
  timestamp: string
  level: 'info' | 'warning' | 'error' | 'success'
  source: string
  message: string
  details?: string
  userId?: string
  ip?: string
}

export function SystemLogs() {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedLevel, setSelectedLevel] = useState<string>('all')
  const [selectedSource, setSelectedSource] = useState<string>('all')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [expandedLog, setExpandedLog] = useState<string | null>(null)

  // モックログデータの生成
  const generateLogs = (): LogEntry[] => {
    const sources = ['auth', 'trading', 'ai-analysis', 'websocket', 'database', 'api']
    const levels: LogEntry['level'][] = ['info', 'warning', 'error', 'success']
    const messages = {
      info: [
        'ユーザーログインが完了しました',
        'バックテストが開始されました',
        'AI分析を実行中です',
        'WebSocket接続が確立されました',
        'データベース接続を確認しました'
      ],
      warning: [
        'API使用量が上限の80%に達しています',
        'WebSocket接続が不安定です',
        'AI分析の処理時間が長くなっています',
        'メモリ使用量が高くなっています'
      ],
      error: [
        'データベース接続エラーが発生しました',
        'AI分析でタイムアウトが発生しました',
        '取引API呼び出しに失敗しました',
        '認証トークンの検証に失敗しました'
      ],
      success: [
        '取引が正常に実行されました',
        'バックテスト結果の保存が完了しました',
        'システムヘルスチェックが正常に完了しました',
        'データベースバックアップが完了しました'
      ]
    }

    const logs: LogEntry[] = []
    const now = new Date()

    for (let i = 0; i < 50; i++) {
      const level = levels[Math.floor(Math.random() * levels.length)]
      const source = sources[Math.floor(Math.random() * sources.length)]
      const messageList = messages[level]
      const message = messageList[Math.floor(Math.random() * messageList.length)]
      const timestamp = new Date(now.getTime() - i * Math.random() * 3600000) // 過去1時間内のランダム時間

      logs.push({
        id: `log-${1000 + i}`,
        timestamp: timestamp.toLocaleString('ja-JP'),
        level,
        source,
        message,
        details: level === 'error' ? `Stack trace: Error at line ${Math.floor(Math.random() * 100) + 1}` : undefined,
        userId: Math.random() > 0.5 ? `U-${1000 + Math.floor(Math.random() * 10)}` : undefined,
        ip: `192.168.1.${Math.floor(Math.random() * 255)}`
      })
    }

    return logs.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
  }

  const [logs, setLogs] = useState<LogEntry[]>(generateLogs)

  // 自動リフレッシュ
  useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(() => {
      // 新しいログエントリーを追加
      const newLog: LogEntry = {
        id: `log-${Date.now()}`,
        timestamp: new Date().toLocaleString('ja-JP'),
        level: ['info', 'warning', 'error', 'success'][Math.floor(Math.random() * 4)] as LogEntry['level'],
        source: ['auth', 'trading', 'ai-analysis', 'websocket', 'database', 'api'][Math.floor(Math.random() * 6)],
        message: '新しいシステムイベントが発生しました',
        ip: `192.168.1.${Math.floor(Math.random() * 255)}`
      }

      setLogs(prev => [newLog, ...prev.slice(0, 49)]) // 最大50件を保持
    }, 10000) // 10秒ごとに新しいログ追加

    return () => clearInterval(interval)
  }, [autoRefresh])

  const filteredLogs = logs.filter(log => {
    const matchesSearch = log.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         log.source.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (log.userId && log.userId.toLowerCase().includes(searchTerm.toLowerCase()))
    const matchesLevel = selectedLevel === 'all' || log.level === selectedLevel
    const matchesSource = selectedSource === 'all' || log.source === selectedSource
    return matchesSearch && matchesLevel && matchesSource
  })

  const getLevelIcon = (level: LogEntry['level']) => {
    const icons = {
      info: InformationCircleIcon,
      warning: ExclamationTriangleIcon,
      error: XCircleIcon,
      success: CheckCircleIcon
    }
    return icons[level]
  }

  const getLevelBadge = (level: LogEntry['level']) => {
    const variants = {
      info: { variant: 'default' as const, label: '情報' },
      warning: { variant: 'warning' as const, label: '警告' },
      error: { variant: 'error' as const, label: 'エラー' },
      success: { variant: 'success' as const, label: '成功' }
    }
    return variants[level]
  }

  const getSourceBadge = (source: string) => {
    const sourceLabels: { [key: string]: string } = {
      'auth': '認証',
      'trading': '取引',
      'ai-analysis': 'AI分析',
      'websocket': 'WebSocket',
      'database': 'データベース',
      'api': 'API'
    }
    return sourceLabels[source] || source
  }

  const exportLogs = () => {
    const csvContent = [
      ['時刻', 'レベル', 'ソース', 'メッセージ', 'ユーザーID', 'IP'].join(','),
      ...filteredLogs.map(log => [
        log.timestamp,
        log.level,
        log.source,
        `"${log.message}"`,
        log.userId || '',
        log.ip || ''
      ].join(','))
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `system_logs_${new Date().toISOString().split('T')[0]}.csv`
    link.click()
  }

  const logStats = {
    total: logs.length,
    info: logs.filter(l => l.level === 'info').length,
    warning: logs.filter(l => l.level === 'warning').length,
    error: logs.filter(l => l.level === 'error').length,
    success: logs.filter(l => l.level === 'success').length
  }

  return (
    <div className="space-y-6">
      {/* 統計とコントロール */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ログ統計 */}
        <Card className="p-4">
          <h3 className="text-lg font-semibold mb-3" style={{ color: 'var(--kb-text)' }}>
            ログ統計
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold" style={{ color: 'var(--kb-text)' }}>
                {logStats.total}
              </div>
              <div className="text-sm" style={{ color: 'var(--kb-text-muted)' }}>
                総ログ数
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span style={{ color: 'var(--kb-text-muted)' }}>エラー</span>
                <span className="text-red-500 font-medium">{logStats.error}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span style={{ color: 'var(--kb-text-muted)' }}>警告</span>
                <span className="text-orange-500 font-medium">{logStats.warning}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span style={{ color: 'var(--kb-text-muted)' }}>情報</span>
                <span style={{ color: 'var(--kb-text)' }}>{logStats.info}</span>
              </div>
            </div>
          </div>
        </Card>

        {/* コントロールパネル */}
        <Card className="p-4">
          <h3 className="text-lg font-semibold mb-3" style={{ color: 'var(--kb-text)' }}>
            監視設定
          </h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm" style={{ color: 'var(--kb-text)' }}>
                自動リフレッシュ
              </span>
              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`w-12 h-6 rounded-full transition-colors ${
                  autoRefresh ? 'bg-green-500' : 'bg-gray-300'
                }`}
              >
                <div className={`w-5 h-5 rounded-full bg-white transition-transform ${
                  autoRefresh ? 'translate-x-6' : 'translate-x-1'
                }`} />
              </button>
            </div>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={exportLogs}
              className="w-full flex items-center gap-2"
            >
              <ArrowDownTrayIcon className="w-4 h-4" />
              ログをエクスポート
            </Button>
          </div>
        </Card>
      </div>

      {/* 検索・フィルタ */}
      <Card className="p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4" 
                                 style={{ color: 'var(--kb-text-muted)' }} />
            <Input
              type="text"
              placeholder="ログメッセージ、ソース、ユーザーIDで検索"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
          <select
            value={selectedLevel}
            onChange={(e) => setSelectedLevel(e.target.value)}
            className="px-3 py-2 rounded-lg border text-sm"
            style={{ 
              background: 'var(--kb-bg-surface)', 
              borderColor: 'var(--kb-border)',
              color: 'var(--kb-text)'
            }}
          >
            <option value="all">すべてのレベル</option>
            <option value="error">エラー</option>
            <option value="warning">警告</option>
            <option value="info">情報</option>
            <option value="success">成功</option>
          </select>
          <select
            value={selectedSource}
            onChange={(e) => setSelectedSource(e.target.value)}
            className="px-3 py-2 rounded-lg border text-sm"
            style={{ 
              background: 'var(--kb-bg-surface)', 
              borderColor: 'var(--kb-border)',
              color: 'var(--kb-text)'
            }}
          >
            <option value="all">すべてのソース</option>
            <option value="auth">認証</option>
            <option value="trading">取引</option>
            <option value="ai-analysis">AI分析</option>
            <option value="websocket">WebSocket</option>
            <option value="database">データベース</option>
            <option value="api">API</option>
          </select>
        </div>
      </Card>

      {/* ログテーブル */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold" style={{ color: 'var(--kb-text)' }}>
            システムログ
          </h3>
          <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--kb-text-muted)' }}>
            <ClockIcon className="w-4 h-4" />
            <span>最終更新: {new Date().toLocaleTimeString('ja-JP')}</span>
          </div>
        </div>

        <div className="space-y-2 max-h-96 overflow-y-auto">
          {filteredLogs.map((log) => {
            const levelBadge = getLevelBadge(log.level)
            const LevelIcon = getLevelIcon(log.level)
            const isExpanded = expandedLog === log.id

            return (
              <div key={log.id} className="border rounded-lg p-4 hover:bg-opacity-50 transition-colors"
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
                <div className="flex items-start gap-3">
                  <LevelIcon className="w-5 h-5 mt-0.5 flex-shrink-0" 
                             style={{ color: levelBadge.variant === 'error' ? 'var(--kb-error)' : 
                                             levelBadge.variant === 'warning' ? 'var(--kb-warning)' :
                                             levelBadge.variant === 'success' ? 'var(--kb-success)' : 'var(--kb-primary)' }} />
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant={levelBadge.variant} className="text-xs">
                            {levelBadge.label}
                          </Badge>
                          <Badge variant="default" className="text-xs">
                            {getSourceBadge(log.source)}
                          </Badge>
                          <span className="text-xs" style={{ color: 'var(--kb-text-muted)' }}>
                            {log.timestamp}
                          </span>
                        </div>
                        <p className="text-sm mb-2" style={{ color: 'var(--kb-text)' }}>
                          {log.message}
                        </p>
                        {(log.userId || log.ip) && (
                          <div className="flex gap-4 text-xs" style={{ color: 'var(--kb-text-muted)' }}>
                            {log.userId && <span>ユーザー: {log.userId}</span>}
                            {log.ip && <span>IP: {log.ip}</span>}
                          </div>
                        )}
                      </div>
                      {log.details && (
                        <button
                          onClick={() => setExpandedLog(isExpanded ? null : log.id)}
                          className="text-xs px-2 py-1 rounded hover:bg-gray-100 transition-colors"
                          style={{ color: 'var(--kb-primary)' }}
                        >
                          {isExpanded ? '閉じる' : '詳細'}
                        </button>
                      )}
                    </div>
                    {isExpanded && log.details && (
                      <div className="mt-3 p-3 rounded border-l-2 text-xs font-mono" 
                           style={{ 
                             background: 'var(--kb-bg)',
                             borderColor: 'var(--kb-error)',
                             color: 'var(--kb-text-muted)'
                           }}>
                        {log.details}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {filteredLogs.length === 0 && (
          <div className="text-center py-8" style={{ color: 'var(--kb-text-muted)' }}>
            検索条件に一致するログが見つかりませんでした
          </div>
        )}
      </Card>
    </div>
  )
}