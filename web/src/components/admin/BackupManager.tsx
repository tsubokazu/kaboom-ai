'use client'

import { useState } from 'react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { 
  CloudArrowDownIcon,
  CloudArrowUpIcon,
  TrashIcon,
  ClockIcon,
  DocumentArrowDownIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon
} from '@heroicons/react/24/outline'

interface BackupFile {
  id: string
  name: string
  size: string
  createdAt: string
  type: 'full' | 'incremental' | 'database' | 'settings'
  status: 'completed' | 'in-progress' | 'failed'
  description: string
}

export function BackupManager() {
  const [isCreatingBackup, setIsCreatingBackup] = useState(false)
  const [selectedBackupType, setSelectedBackupType] = useState<'full' | 'incremental' | 'database' | 'settings'>('full')

  // モックバックアップファイル
  const mockBackups: BackupFile[] = [
    {
      id: 'backup-001',
      name: 'full_backup_20250818_120000',
      size: '2.1 GB',
      createdAt: '2025-08-18 12:00:00',
      type: 'full',
      status: 'completed',
      description: 'すべてのデータとシステム設定の完全バックアップ'
    },
    {
      id: 'backup-002',
      name: 'database_backup_20250818_060000',
      size: '845 MB',
      createdAt: '2025-08-18 06:00:00',
      type: 'database',
      status: 'completed',
      description: 'ユーザーデータと取引履歴のデータベースバックアップ'
    },
    {
      id: 'backup-003',
      name: 'incremental_backup_20250817_180000',
      size: '126 MB',
      createdAt: '2025-08-17 18:00:00',
      type: 'incremental',
      status: 'completed',
      description: '前回のフルバックアップ以降の変更分'
    },
    {
      id: 'backup-004',
      name: 'settings_backup_20250817_120000',
      size: '12 MB',
      createdAt: '2025-08-17 12:00:00',
      type: 'settings',
      status: 'completed',
      description: 'システム設定とAI設定のバックアップ'
    },
    {
      id: 'backup-005',
      name: 'full_backup_20250816_120000',
      size: '1.9 GB',
      createdAt: '2025-08-16 12:00:00',
      type: 'full',
      status: 'failed',
      description: 'バックアップ中にディスク容量不足でエラー'
    }
  ]

  const [backups, setBackups] = useState<BackupFile[]>(mockBackups)

  const backupTypeLabels = {
    full: 'フル',
    incremental: '増分',
    database: 'データベース',
    settings: '設定'
  }

  const getStatusBadge = (status: BackupFile['status']) => {
    const variants = {
      completed: { variant: 'success' as const, label: '完了', icon: CheckCircleIcon },
      'in-progress': { variant: 'warning' as const, label: '実行中', icon: ClockIcon },
      failed: { variant: 'error' as const, label: '失敗', icon: ExclamationTriangleIcon }
    }
    return variants[status]
  }

  const getTypeBadge = (type: BackupFile['type']) => {
    const variants = {
      full: { variant: 'primary' as const, label: 'フル' },
      incremental: { variant: 'default' as const, label: '増分' },
      database: { variant: 'warning' as const, label: 'DB' },
      settings: { variant: 'default' as const, label: '設定' }
    }
    return variants[type]
  }

  const handleCreateBackup = async () => {
    setIsCreatingBackup(true)
    
    // モックバックアップ作成プロセス
    const newBackup: BackupFile = {
      id: `backup-${Date.now()}`,
      name: `${selectedBackupType}_backup_${new Date().toISOString().replace(/[:.]/g, '').slice(0, 15)}`,
      size: '--- MB',
      createdAt: new Date().toLocaleString('ja-JP'),
      type: selectedBackupType,
      status: 'in-progress',
      description: 'バックアップを作成中...'
    }

    setBackups(prev => [newBackup, ...prev])

    // 3秒後に完了状態に変更
    setTimeout(() => {
      setBackups(prev => 
        prev.map(backup => 
          backup.id === newBackup.id 
            ? { 
                ...backup, 
                status: 'completed' as const, 
                size: Math.floor(Math.random() * 1000 + 100) + ' MB',
                description: '正常にバックアップが作成されました'
              }
            : backup
        )
      )
      setIsCreatingBackup(false)
    }, 3000)
  }

  const handleDownloadBackup = (backupId: string) => {
    // TODO: 実際のダウンロード機能を実装
    console.log(`Downloading backup: ${backupId}`)
    alert('バックアップファイルのダウンロードを開始します')
  }

  const handleRestoreBackup = (backupId: string) => {
    const confirmed = confirm('このバックアップを使用してシステムを復元しますか？\n※現在のデータは上書きされます。')
    if (confirmed) {
      // TODO: 実際の復元機能を実装
      console.log(`Restoring from backup: ${backupId}`)
      alert('復元処理を開始します。完了まで数分かかる場合があります。')
    }
  }

  const handleDeleteBackup = (backupId: string) => {
    const confirmed = confirm('このバックアップファイルを削除しますか？')
    if (confirmed) {
      setBackups(prev => prev.filter(backup => backup.id !== backupId))
    }
  }

  const totalBackupSize = backups
    .filter(b => b.status === 'completed')
    .reduce((total, backup) => {
      const size = parseFloat(backup.size.split(' ')[0])
      const unit = backup.size.split(' ')[1]
      return total + (unit === 'GB' ? size * 1024 : size)
    }, 0)

  const completedBackups = backups.filter(b => b.status === 'completed').length

  return (
    <div className="space-y-6">
      {/* 統計情報 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <CloudArrowDownIcon className="w-8 h-8" style={{ color: 'var(--kb-primary)' }} />
            <div>
              <div className="text-sm" style={{ color: 'var(--kb-text-muted)' }}>
                総バックアップ数
              </div>
              <div className="text-xl font-bold" style={{ color: 'var(--kb-text)' }}>
                {completedBackups}
              </div>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <DocumentArrowDownIcon className="w-8 h-8" style={{ color: 'var(--kb-primary)' }} />
            <div>
              <div className="text-sm" style={{ color: 'var(--kb-text-muted)' }}>
                合計サイズ
              </div>
              <div className="text-xl font-bold" style={{ color: 'var(--kb-text)' }}>
                {(totalBackupSize / 1024).toFixed(1)} GB
              </div>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <ClockIcon className="w-8 h-8" style={{ color: 'var(--kb-primary)' }} />
            <div>
              <div className="text-sm" style={{ color: 'var(--kb-text-muted)' }}>
                最新バックアップ
              </div>
              <div className="text-lg font-bold" style={{ color: 'var(--kb-text)' }}>
                {backups.find(b => b.status === 'completed')?.createdAt.split(' ')[1] || '-'}
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* バックアップ作成 */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--kb-text)' }}>
          新しいバックアップの作成
        </h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm mb-2" style={{ color: 'var(--kb-text)' }}>
              バックアップタイプ
            </label>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {Object.entries(backupTypeLabels).map(([type, label]) => (
                <button
                  key={type}
                  onClick={() => setSelectedBackupType(type as typeof selectedBackupType)}
                  className={`p-3 rounded-lg border text-sm transition-colors ${
                    selectedBackupType === type 
                      ? 'border-blue-500 bg-blue-50' 
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  style={{ 
                    borderColor: selectedBackupType === type ? 'var(--kb-primary)' : 'var(--kb-border)',
                    background: selectedBackupType === type ? 'var(--kb-bg-surface)' : 'transparent',
                    color: 'var(--kb-text)'
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div className="p-4 rounded-lg" style={{ background: 'var(--kb-bg)' }}>
            <div className="flex items-start gap-3">
              <InformationCircleIcon className="w-5 h-5 mt-0.5" style={{ color: 'var(--kb-primary)' }} />
              <div className="text-sm" style={{ color: 'var(--kb-text-muted)' }}>
                <div className="font-medium mb-1" style={{ color: 'var(--kb-text)' }}>
                  {backupTypeLabels[selectedBackupType]}バックアップについて
                </div>
                {selectedBackupType === 'full' && 'すべてのデータ、設定、システムファイルを含む完全なバックアップです。復元時に全システムが復旧します。'}
                {selectedBackupType === 'incremental' && '前回のバックアップ以降に変更されたファイルのみをバックアップします。'}
                {selectedBackupType === 'database' && 'ユーザーデータ、取引履歴、ポートフォリオ情報などのデータベースのみをバックアップします。'}
                {selectedBackupType === 'settings' && 'システム設定、AI設定、ユーザー設定などの構成情報のみをバックアップします。'}
              </div>
            </div>
          </div>

          <Button 
            onClick={handleCreateBackup}
            disabled={isCreatingBackup}
            className="flex items-center gap-2"
          >
            <CloudArrowDownIcon className="w-4 h-4" />
            {isCreatingBackup ? 'バックアップ作成中...' : 'バックアップを作成'}
          </Button>
        </div>
      </Card>

      {/* バックアップリスト */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--kb-text)' }}>
          バックアップファイル
        </h3>

        <div className="space-y-3">
          {backups.map((backup) => {
            const statusBadge = getStatusBadge(backup.status)
            const typeBadge = getTypeBadge(backup.type)
            const StatusIcon = statusBadge.icon

            return (
              <div key={backup.id} className="border rounded-lg p-4" 
                   style={{ borderColor: 'var(--kb-border)' }}>
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4 flex-1">
                    <div className="w-12 h-12 rounded-lg flex items-center justify-center" 
                         style={{ background: 'var(--kb-bg)' }}>
                      <StatusIcon className="w-6 h-6" 
                                  style={{ color: backup.status === 'completed' ? 'var(--kb-success)' : 
                                                 backup.status === 'failed' ? 'var(--kb-error)' : 'var(--kb-warning)' }} />
                    </div>
                    
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="font-medium" style={{ color: 'var(--kb-text)' }}>
                          {backup.name}
                        </span>
                        <Badge variant={typeBadge.variant}>
                          {typeBadge.label}
                        </Badge>
                        <Badge variant={statusBadge.variant}>
                          {statusBadge.label}
                        </Badge>
                      </div>
                      
                      <p className="text-sm mb-2" style={{ color: 'var(--kb-text-muted)' }}>
                        {backup.description}
                      </p>
                      
                      <div className="flex gap-4 text-sm" style={{ color: 'var(--kb-text-muted)' }}>
                        <span>サイズ: {backup.size}</span>
                        <span>作成日時: {backup.createdAt}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {backup.status === 'completed' && (
                      <>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleDownloadBackup(backup.id)}
                          className="flex items-center gap-1"
                        >
                          <DocumentArrowDownIcon className="w-4 h-4" />
                          ダウンロード
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => handleRestoreBackup(backup.id)}
                          className="flex items-center gap-1"
                        >
                          <CloudArrowUpIcon className="w-4 h-4" />
                          復元
                        </Button>
                      </>
                    )}
                    <button
                      onClick={() => handleDeleteBackup(backup.id)}
                      className="p-2 text-red-500 hover:bg-red-50 rounded transition-colors"
                      title="削除"
                    >
                      <TrashIcon className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </Card>

      {/* 自動バックアップ設定 */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--kb-text)' }}>
          自動バックアップ設定
        </h3>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium" style={{ color: 'var(--kb-text)' }}>
                毎日の自動バックアップ
              </div>
              <div className="text-sm" style={{ color: 'var(--kb-text-muted)' }}>
                毎日午前6時にデータベースバックアップを自動実行
              </div>
            </div>
            <div className="w-12 h-6 bg-green-500 rounded-full">
              <div className="w-5 h-5 bg-white rounded-full translate-x-6 transition-transform" />
            </div>
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium" style={{ color: 'var(--kb-text)' }}>
                週次フルバックアップ
              </div>
              <div className="text-sm" style={{ color: 'var(--kb-text-muted)' }}>
                毎週日曜日にフルバックアップを自動実行
              </div>
            </div>
            <div className="w-12 h-6 bg-green-500 rounded-full">
              <div className="w-5 h-5 bg-white rounded-full translate-x-6 transition-transform" />
            </div>
          </div>
        </div>
      </Card>
    </div>
  )
}