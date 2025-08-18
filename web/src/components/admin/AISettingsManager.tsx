'use client'

import { useState } from 'react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { 
  CpuChipIcon,
  KeyIcon,
  ChartBarIcon,
  CurrencyDollarIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline'

interface AIProvider {
  id: string
  name: string
  status: 'active' | 'inactive' | 'error'
  apiKey: string
  model: string
  rateLimit: number
  monthlyCost: number
  monthlyUsage: number
  lastUsed: string
}

export function AISettingsManager() {
  const [providers, setProviders] = useState<AIProvider[]>([
    {
      id: 'openai',
      name: 'OpenAI GPT',
      status: 'active',
      apiKey: 'sk-***...***abc',
      model: 'gpt-4-1106-preview',
      rateLimit: 10000,
      monthlyCost: 45.67,
      monthlyUsage: 3420,
      lastUsed: '2分前'
    },
    {
      id: 'gemini',
      name: 'Google Gemini Pro',
      status: 'active',
      apiKey: 'AIza***...***xyz',
      model: 'gemini-1.5-pro',
      rateLimit: 60,
      monthlyCost: 23.45,
      monthlyUsage: 1890,
      lastUsed: '15分前'
    },
    {
      id: 'claude',
      name: 'Anthropic Claude',
      status: 'inactive',
      apiKey: '',
      model: 'claude-3-sonnet',
      rateLimit: 5000,
      monthlyCost: 0,
      monthlyUsage: 0,
      lastUsed: '-'
    }
  ])

  const [editingProvider, setEditingProvider] = useState<string | null>(null)
  const [editForm, setEditForm] = useState<Partial<AIProvider>>({})

  const handleEdit = (providerId: string) => {
    const provider = providers.find(p => p.id === providerId)
    if (provider) {
      setEditingProvider(providerId)
      setEditForm({ ...provider })
    }
  }

  const handleSave = () => {
    if (editingProvider && editForm) {
      setProviders(prev => 
        prev.map(p => 
          p.id === editingProvider 
            ? { ...p, ...editForm }
            : p
        )
      )
      setEditingProvider(null)
      setEditForm({})
    }
  }

  const handleCancel = () => {
    setEditingProvider(null)
    setEditForm({})
  }

  const toggleProviderStatus = (providerId: string) => {
    setProviders(prev =>
      prev.map(p =>
        p.id === providerId
          ? { ...p, status: p.status === 'active' ? 'inactive' : 'active' }
          : p
      )
    )
  }

  const getStatusBadge = (status: AIProvider['status']) => {
    const variants = {
      active: { variant: 'success' as const, label: 'アクティブ', icon: CheckCircleIcon },
      inactive: { variant: 'default' as const, label: '非アクティブ', icon: null },
      error: { variant: 'error' as const, label: 'エラー', icon: ExclamationTriangleIcon }
    }
    return variants[status]
  }

  const formatCost = (cost: number) => `$${cost.toFixed(2)}`
  const formatUsage = (usage: number) => usage.toLocaleString()

  const totalMonthlyCost = providers.reduce((sum, p) => sum + p.monthlyCost, 0)
  const activeProviders = providers.filter(p => p.status === 'active').length

  return (
    <div className="space-y-6">
      {/* 概要統計 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <CpuChipIcon className="w-8 h-8" style={{ color: 'var(--kb-primary)' }} />
            <div>
              <div className="text-sm" style={{ color: 'var(--kb-text-muted)' }}>
                アクティブプロバイダー
              </div>
              <div className="text-xl font-bold" style={{ color: 'var(--kb-text)' }}>
                {activeProviders} / {providers.length}
              </div>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <CurrencyDollarIcon className="w-8 h-8" style={{ color: 'var(--kb-primary)' }} />
            <div>
              <div className="text-sm" style={{ color: 'var(--kb-text-muted)' }}>
                月次コスト
              </div>
              <div className="text-xl font-bold" style={{ color: 'var(--kb-text)' }}>
                {formatCost(totalMonthlyCost)}
              </div>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <ChartBarIcon className="w-8 h-8" style={{ color: 'var(--kb-primary)' }} />
            <div>
              <div className="text-sm" style={{ color: 'var(--kb-text-muted)' }}>
                総使用量（今月）
              </div>
              <div className="text-xl font-bold" style={{ color: 'var(--kb-text)' }}>
                {formatUsage(providers.reduce((sum, p) => sum + p.monthlyUsage, 0))}
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* プロバイダー設定 */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--kb-text)' }}>
          AIプロバイダー設定
        </h3>
        
        <div className="space-y-4">
          {providers.map((provider) => {
            const statusBadge = getStatusBadge(provider.status)
            const isEditing = editingProvider === provider.id
            
            return (
              <div key={provider.id} className="border rounded-lg p-4" 
                   style={{ borderColor: 'var(--kb-border)' }}>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-4 flex-1">
                    <div className="w-12 h-12 rounded-lg flex items-center justify-center" 
                         style={{ background: 'var(--kb-bg)' }}>
                      <CpuChipIcon className="w-6 h-6" style={{ color: 'var(--kb-primary)' }} />
                    </div>
                    
                    <div className="flex-1 grid grid-cols-1 md:grid-cols-4 gap-4">
                      <div>
                        <div className="font-medium" style={{ color: 'var(--kb-text)' }}>
                          {provider.name}
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          <Badge variant={statusBadge.variant}>
                            {statusBadge.label}
                          </Badge>
                        </div>
                      </div>

                      <div>
                        <div className="text-sm" style={{ color: 'var(--kb-text-muted)' }}>
                          APIキー
                        </div>
                        {isEditing ? (
                          <Input
                            type="password"
                            value={editForm.apiKey || ''}
                            onChange={(e) => setEditForm(prev => ({ ...prev, apiKey: e.target.value }))}
                            placeholder="APIキーを入力"
                            className="mt-1"
                          />
                        ) : (
                          <div className="flex items-center gap-2 mt-1">
                            <KeyIcon className="w-4 h-4" style={{ color: 'var(--kb-text-muted)' }} />
                            <span className="text-sm font-mono" style={{ color: 'var(--kb-text)' }}>
                              {provider.apiKey || '未設定'}
                            </span>
                          </div>
                        )}
                      </div>

                      <div>
                        <div className="text-sm" style={{ color: 'var(--kb-text-muted)' }}>
                          コスト・使用量
                        </div>
                        <div className="mt-1">
                          <div className="text-sm font-medium" style={{ color: 'var(--kb-text)' }}>
                            {formatCost(provider.monthlyCost)}
                          </div>
                          <div className="text-xs" style={{ color: 'var(--kb-text-muted)' }}>
                            {formatUsage(provider.monthlyUsage)} calls
                          </div>
                        </div>
                      </div>

                      <div>
                        <div className="text-sm" style={{ color: 'var(--kb-text-muted)' }}>
                          最終使用
                        </div>
                        <div className="text-sm mt-1" style={{ color: 'var(--kb-text)' }}>
                          {provider.lastUsed}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {isEditing ? (
                      <>
                        <Button size="sm" onClick={handleSave}>
                          保存
                        </Button>
                        <Button size="sm" variant="outline" onClick={handleCancel}>
                          キャンセル
                        </Button>
                      </>
                    ) : (
                      <>
                        <Button 
                          size="sm" 
                          variant="outline"
                          onClick={() => handleEdit(provider.id)}
                        >
                          編集
                        </Button>
                        <Button
                          size="sm"
                          variant={provider.status === 'active' ? 'outline' : 'default'}
                          onClick={() => toggleProviderStatus(provider.id)}
                        >
                          {provider.status === 'active' ? '無効化' : '有効化'}
                        </Button>
                      </>
                    )}
                  </div>
                </div>

                {isEditing && (
                  <div className="mt-4 pt-4 border-t grid grid-cols-1 md:grid-cols-2 gap-4" 
                       style={{ borderColor: 'var(--kb-border)' }}>
                    <div>
                      <label className="block text-sm mb-1" style={{ color: 'var(--kb-text-muted)' }}>
                        モデル
                      </label>
                      <Input
                        value={editForm.model || ''}
                        onChange={(e) => setEditForm(prev => ({ ...prev, model: e.target.value }))}
                        placeholder="モデル名"
                      />
                    </div>
                    <div>
                      <label className="block text-sm mb-1" style={{ color: 'var(--kb-text-muted)' }}>
                        レート制限 (calls/min)
                      </label>
                      <Input
                        type="number"
                        value={editForm.rateLimit || ''}
                        onChange={(e) => setEditForm(prev => ({ ...prev, rateLimit: Number(e.target.value) }))}
                        placeholder="レート制限"
                      />
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </Card>
    </div>
  )
}