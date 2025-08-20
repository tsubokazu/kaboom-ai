'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card } from '@/components/ui/Card'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer, AreaChart, Area } from 'recharts'
import { 
  ServerIcon,
  UserGroupIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon
} from '@heroicons/react/24/outline'
import { useWebSocket } from '@/hooks/useWebSocket'
import { WebSocketMessage } from '@/stores/websocketStore'

interface SystemMetric {
  timestamp: string
  activeUsers: number
  websocketConnections: number
  apiRequests: number
  errorRate: number
  responseTime: number
  cpuUsage: number
  memoryUsage: number
}

export function SystemMetrics() {
  const [timeRange, setTimeRange] = useState<'1h' | '6h' | '24h' | '7d'>('24h')
  const [lastUpdateTime, setLastUpdateTime] = useState<Date>(new Date())

  // WebSocket接続とシステムメトリクス更新の監視
  const { subscribe, isConnected } = useWebSocket({
    autoConnect: true
  })
  
  // モックメトリクスデータの生成
  const generateMetrics = useCallback((): SystemMetric[] => {
    const now = new Date()
    const data: SystemMetric[] = []
    const points = timeRange === '1h' ? 60 : timeRange === '6h' ? 36 : timeRange === '24h' ? 24 : 168
    const interval = timeRange === '1h' ? 1 : timeRange === '6h' ? 10 : timeRange === '24h' ? 60 : 60 * 24
    
    for (let i = points; i >= 0; i--) {
      const timestamp = new Date(now.getTime() - i * interval * 60000)
      data.push({
        timestamp: timestamp.toLocaleTimeString('ja-JP', { 
          hour: '2-digit', 
          minute: '2-digit',
          ...(timeRange === '7d' ? { month: '2-digit', day: '2-digit' } : {})
        }),
        activeUsers: Math.floor(Math.random() * 50) + 80,
        websocketConnections: Math.floor(Math.random() * 30) + 60,
        apiRequests: Math.floor(Math.random() * 200) + 300,
        errorRate: Math.random() * 2,
        responseTime: Math.random() * 100 + 150,
        cpuUsage: Math.random() * 30 + 40,
        memoryUsage: Math.random() * 20 + 60
      })
    }
    return data
  }, [timeRange])

  const [metrics, setMetrics] = useState<SystemMetric[]>(generateMetrics)

  useEffect(() => {
    setMetrics(generateMetrics())
  }, [timeRange, generateMetrics])

  // WebSocketからシステムメトリクス更新を受信
  useEffect(() => {
    const unsubscribe = subscribe('system_metrics', (message: WebSocketMessage) => {
      const { payload } = message
      
      setMetrics(prev => {
        const newMetrics = [...prev]
        const now = new Date()
        const latest: SystemMetric = {
          timestamp: now.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' }),
          activeUsers: (payload.activeUsers as number) || Math.floor(Math.random() * 50) + 80,
          websocketConnections: (payload.websocketConnections as number) || Math.floor(Math.random() * 30) + 60,
          apiRequests: (payload.apiRequests as number) || Math.floor(Math.random() * 200) + 300,
          errorRate: payload.errorRate !== undefined ? (payload.errorRate as number) : Math.random() * 2,
          responseTime: (payload.responseTime as number) || Math.random() * 100 + 150,
          cpuUsage: (payload.cpuUsage as number) || Math.random() * 30 + 40,
          memoryUsage: (payload.memoryUsage as number) || Math.random() * 20 + 60
        }
        
        newMetrics.shift() // 最古のデータを削除
        newMetrics.push(latest) // 新しいデータを追加
        setLastUpdateTime(now) // 更新時間を記録
        
        return newMetrics
      })
    })

    return unsubscribe
  }, [subscribe])

  // WebSocket未接続時のモック更新
  useEffect(() => {
    if (isConnected) return // WebSocket接続時はモック無効

    const interval = setInterval(() => {
      setMetrics(prev => {
        const newMetrics = [...prev]
        const now = new Date()
        const latest = {
          timestamp: now.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' }),
          activeUsers: Math.floor(Math.random() * 50) + 80,
          websocketConnections: Math.floor(Math.random() * 30) + 60,
          apiRequests: Math.floor(Math.random() * 200) + 300,
          errorRate: Math.random() * 2,
          responseTime: Math.random() * 100 + 150,
          cpuUsage: Math.random() * 30 + 40,
          memoryUsage: Math.random() * 20 + 60
        }
        newMetrics.shift() // 最古のデータを削除
        newMetrics.push(latest) // 新しいデータを追加
        setLastUpdateTime(now)
        return newMetrics
      })
    }, 30000) // 30秒ごとに更新

    return () => clearInterval(interval)
  }, [isConnected])

  const currentMetrics = metrics[metrics.length - 1]

  const statusCards = [
    {
      title: 'システム状態',
      value: isConnected ? 'オンライン' : 'オフライン',
      status: isConnected ? 'success' : 'warning',
      icon: CheckCircleIcon,
      description: isConnected ? 'リアルタイム接続中' : 'モックデータ表示中'
    },
    {
      title: 'アクティブユーザー',
      value: currentMetrics?.activeUsers || 0,
      status: 'info',
      icon: UserGroupIcon,
      description: '現在システムを使用中'
    },
    {
      title: 'WebSocket接続',
      value: currentMetrics?.websocketConnections || 0,
      status: 'info',
      icon: ServerIcon,
      description: 'リアルタイム接続数'
    },
    {
      title: 'エラー率',
      value: `${(currentMetrics?.errorRate || 0).toFixed(2)}%`,
      status: (currentMetrics?.errorRate || 0) > 1 ? 'warning' : 'success',
      icon: ExclamationTriangleIcon,
      description: '直近1時間の平均'
    }
  ]

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return 'text-green-500'
      case 'warning': return 'text-orange-500'
      case 'error': return 'text-red-500'
      default: return 'var(--kb-primary)'
    }
  }

  return (
    <div className="space-y-6">
      {/* 時間範囲セレクター */}
      <div className="flex justify-end">
        <div className="flex rounded-lg border p-1" style={{ borderColor: 'var(--kb-border)' }}>
          {[
            { key: '1h', label: '1時間' },
            { key: '6h', label: '6時間' },
            { key: '24h', label: '24時間' },
            { key: '7d', label: '7日間' }
          ].map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setTimeRange(key as typeof timeRange)}
              className={`px-3 py-1 text-sm rounded transition-colors ${
                timeRange === key 
                  ? 'text-white' 
                  : ''
              }`}
              style={{
                background: timeRange === key ? 'var(--kb-primary)' : 'transparent',
                color: timeRange === key ? 'white' : 'var(--kb-text)'
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* ステータスカード */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statusCards.map((card, index) => (
          <Card key={index} className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg" style={{ background: 'var(--kb-bg)' }}>
                <card.icon className={`w-6 h-6 ${getStatusColor(card.status)}`} />
              </div>
              <div className="flex-1">
                <div className="text-sm" style={{ color: 'var(--kb-text-muted)' }}>
                  {card.title}
                </div>
                <div className="text-xl font-bold" style={{ color: 'var(--kb-text)' }}>
                  {card.value}
                </div>
                <div className="text-xs" style={{ color: 'var(--kb-text-muted)' }}>
                  {card.description}
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* チャート */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* アクティブユーザー */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--kb-text)' }}>
            アクティブユーザー数
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={metrics}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--kb-border)" />
              <XAxis dataKey="timestamp" stroke="var(--kb-text-muted)" fontSize={12} />
              <YAxis stroke="var(--kb-text-muted)" fontSize={12} />
              <Line 
                type="monotone" 
                dataKey="activeUsers" 
                stroke="var(--kb-primary)" 
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        {/* API リクエスト数 */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--kb-text)' }}>
            API リクエスト/分
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={metrics}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--kb-border)" />
              <XAxis dataKey="timestamp" stroke="var(--kb-text-muted)" fontSize={12} />
              <YAxis stroke="var(--kb-text-muted)" fontSize={12} />
              <Area 
                type="monotone" 
                dataKey="apiRequests" 
                stroke="var(--kb-success)" 
                fill="var(--kb-success)"
                fillOpacity={0.1}
              />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        {/* レスポンス時間 */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--kb-text)' }}>
            平均レスポンス時間
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={metrics}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--kb-border)" />
              <XAxis dataKey="timestamp" stroke="var(--kb-text-muted)" fontSize={12} />
              <YAxis stroke="var(--kb-text-muted)" fontSize={12} />
              <Line 
                type="monotone" 
                dataKey="responseTime" 
                stroke="var(--kb-warning)" 
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
          <div className="mt-2 text-sm" style={{ color: 'var(--kb-text-muted)' }}>
            現在: {(currentMetrics?.responseTime || 0).toFixed(0)}ms
          </div>
        </Card>

        {/* システムリソース */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--kb-text)' }}>
            システムリソース
          </h3>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span style={{ color: 'var(--kb-text)' }}>CPU使用率</span>
                <span style={{ color: 'var(--kb-text)' }}>
                  {(currentMetrics?.cpuUsage || 0).toFixed(1)}%
                </span>
              </div>
              <div className="h-2 rounded-full" style={{ background: 'var(--kb-bg)' }}>
                <div 
                  className="h-2 rounded-full transition-all duration-300"
                  style={{ 
                    width: `${currentMetrics?.cpuUsage || 0}%`,
                    background: (currentMetrics?.cpuUsage || 0) > 80 ? 'var(--kb-error)' : 'var(--kb-primary)'
                  }}
                />
              </div>
            </div>
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span style={{ color: 'var(--kb-text)' }}>メモリ使用率</span>
                <span style={{ color: 'var(--kb-text)' }}>
                  {(currentMetrics?.memoryUsage || 0).toFixed(1)}%
                </span>
              </div>
              <div className="h-2 rounded-full" style={{ background: 'var(--kb-bg)' }}>
                <div 
                  className="h-2 rounded-full transition-all duration-300"
                  style={{ 
                    width: `${currentMetrics?.memoryUsage || 0}%`,
                    background: (currentMetrics?.memoryUsage || 0) > 80 ? 'var(--kb-error)' : 'var(--kb-success)'
                  }}
                />
              </div>
            </div>
          </div>
          <div className="mt-4 p-3 rounded-lg flex items-center gap-2"
               style={{ background: 'var(--kb-bg)' }}>
            <ClockIcon className="w-4 h-4" style={{ color: 'var(--kb-text-muted)' }} />
            <span className="text-sm" style={{ color: 'var(--kb-text-muted)' }}>
              最終更新: {lastUpdateTime.toLocaleTimeString('ja-JP')}
            </span>
            {isConnected && (
              <div className="ml-2 w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}