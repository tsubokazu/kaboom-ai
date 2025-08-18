import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'

// Types
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

interface SystemMetrics {
  activeUsers: number
  websocketConnections: number
  apiRequests: number
  errorRate: number
  responseTime: number
  cpuUsage: number
  memoryUsage: number
  timestamp: string
}

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

interface BackupFile {
  id: string
  name: string
  size: string
  createdAt: string
  type: 'full' | 'incremental' | 'database' | 'settings'
  status: 'completed' | 'in-progress' | 'failed'
  description: string
}

// Store State
interface AdminStore {
  // Users
  users: User[]
  selectedUser: User | null
  userSearchTerm: string
  userFilters: {
    role: string
    status: string
  }

  // System Metrics
  currentMetrics: SystemMetrics | null
  metricsHistory: SystemMetrics[]
  metricsTimeRange: '1h' | '6h' | '24h' | '7d'

  // Logs
  logs: LogEntry[]
  logSearchTerm: string
  logFilters: {
    level: string
    source: string
  }
  autoRefreshLogs: boolean

  // AI Providers
  aiProviders: AIProvider[]
  editingProvider: string | null

  // Backups
  backups: BackupFile[]
  isCreatingBackup: boolean
  selectedBackupType: 'full' | 'incremental' | 'database' | 'settings'

  // Actions
  // User Management
  setUsers: (users: User[]) => void
  selectUser: (user: User | null) => void
  setUserSearchTerm: (term: string) => void
  setUserFilters: (filters: Partial<AdminStore['userFilters']>) => void
  updateUser: (userId: string, updates: Partial<User>) => void
  toggleUserStatus: (userId: string) => void

  // System Metrics
  setCurrentMetrics: (metrics: SystemMetrics) => void
  addMetricsToHistory: (metrics: SystemMetrics) => void
  setMetricsTimeRange: (range: AdminStore['metricsTimeRange']) => void

  // Logs
  setLogs: (logs: LogEntry[]) => void
  addLog: (log: LogEntry) => void
  setLogSearchTerm: (term: string) => void
  setLogFilters: (filters: Partial<AdminStore['logFilters']>) => void
  toggleAutoRefreshLogs: () => void

  // AI Providers
  setAIProviders: (providers: AIProvider[]) => void
  updateAIProvider: (providerId: string, updates: Partial<AIProvider>) => void
  setEditingProvider: (providerId: string | null) => void
  toggleProviderStatus: (providerId: string) => void

  // Backups
  setBackups: (backups: BackupFile[]) => void
  addBackup: (backup: BackupFile) => void
  updateBackup: (backupId: string, updates: Partial<BackupFile>) => void
  deleteBackup: (backupId: string) => void
  setIsCreatingBackup: (creating: boolean) => void
  setSelectedBackupType: (type: AdminStore['selectedBackupType']) => void

  // Utility
  getFilteredUsers: () => User[]
  getFilteredLogs: () => LogEntry[]
  getTotalBackupSize: () => number
}

export const useAdminStore = create<AdminStore>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial State
        users: [],
        selectedUser: null,
        userSearchTerm: '',
        userFilters: { role: 'all', status: 'all' },

        currentMetrics: null,
        metricsHistory: [],
        metricsTimeRange: '24h',

        logs: [],
        logSearchTerm: '',
        logFilters: { level: 'all', source: 'all' },
        autoRefreshLogs: true,

        aiProviders: [],
        editingProvider: null,

        backups: [],
        isCreatingBackup: false,
        selectedBackupType: 'full',

        // User Management Actions
        setUsers: (users) => set({ users }),
        selectUser: (user) => set({ selectedUser: user }),
        setUserSearchTerm: (term) => set({ userSearchTerm: term }),
        setUserFilters: (filters) => 
          set((state) => ({ 
            userFilters: { ...state.userFilters, ...filters } 
          })),
        updateUser: (userId, updates) =>
          set((state) => ({
            users: state.users.map(user =>
              user.id === userId ? { ...user, ...updates } : user
            )
          })),
        toggleUserStatus: (userId) =>
          set((state) => ({
            users: state.users.map(user =>
              user.id === userId
                ? { 
                    ...user, 
                    status: user.status === 'active' ? 'suspended' : 'active' 
                  }
                : user
            )
          })),

        // System Metrics Actions
        setCurrentMetrics: (metrics) => set({ currentMetrics: metrics }),
        addMetricsToHistory: (metrics) =>
          set((state) => ({
            metricsHistory: [...state.metricsHistory.slice(-99), metrics] // Keep last 100 entries
          })),
        setMetricsTimeRange: (range) => set({ metricsTimeRange: range }),

        // Logs Actions
        setLogs: (logs) => set({ logs }),
        addLog: (log) =>
          set((state) => ({
            logs: [log, ...state.logs.slice(0, 49)] // Keep last 50 logs
          })),
        setLogSearchTerm: (term) => set({ logSearchTerm: term }),
        setLogFilters: (filters) =>
          set((state) => ({
            logFilters: { ...state.logFilters, ...filters }
          })),
        toggleAutoRefreshLogs: () =>
          set((state) => ({ autoRefreshLogs: !state.autoRefreshLogs })),

        // AI Providers Actions
        setAIProviders: (providers) => set({ aiProviders: providers }),
        updateAIProvider: (providerId, updates) =>
          set((state) => ({
            aiProviders: state.aiProviders.map(provider =>
              provider.id === providerId ? { ...provider, ...updates } : provider
            )
          })),
        setEditingProvider: (providerId) => set({ editingProvider: providerId }),
        toggleProviderStatus: (providerId) =>
          set((state) => ({
            aiProviders: state.aiProviders.map(provider =>
              provider.id === providerId
                ? { 
                    ...provider, 
                    status: provider.status === 'active' ? 'inactive' : 'active' 
                  }
                : provider
            )
          })),

        // Backups Actions
        setBackups: (backups) => set({ backups }),
        addBackup: (backup) =>
          set((state) => ({
            backups: [backup, ...state.backups]
          })),
        updateBackup: (backupId, updates) =>
          set((state) => ({
            backups: state.backups.map(backup =>
              backup.id === backupId ? { ...backup, ...updates } : backup
            )
          })),
        deleteBackup: (backupId) =>
          set((state) => ({
            backups: state.backups.filter(backup => backup.id !== backupId)
          })),
        setIsCreatingBackup: (creating) => set({ isCreatingBackup: creating }),
        setSelectedBackupType: (type) => set({ selectedBackupType: type }),

        // Utility Functions
        getFilteredUsers: () => {
          const { users, userSearchTerm, userFilters } = get()
          return users.filter(user => {
            const matchesSearch = user.name.toLowerCase().includes(userSearchTerm.toLowerCase()) ||
                                 user.email.toLowerCase().includes(userSearchTerm.toLowerCase()) ||
                                 user.id.toLowerCase().includes(userSearchTerm.toLowerCase())
            const matchesRole = userFilters.role === 'all' || user.role === userFilters.role
            const matchesStatus = userFilters.status === 'all' || user.status === userFilters.status
            return matchesSearch && matchesRole && matchesStatus
          })
        },

        getFilteredLogs: () => {
          const { logs, logSearchTerm, logFilters } = get()
          return logs.filter(log => {
            const matchesSearch = log.message.toLowerCase().includes(logSearchTerm.toLowerCase()) ||
                                 log.source.toLowerCase().includes(logSearchTerm.toLowerCase()) ||
                                 (log.userId && log.userId.toLowerCase().includes(logSearchTerm.toLowerCase()))
            const matchesLevel = logFilters.level === 'all' || log.level === logFilters.level
            const matchesSource = logFilters.source === 'all' || log.source === logFilters.source
            return matchesSearch && matchesLevel && matchesSource
          })
        },

        getTotalBackupSize: () => {
          const { backups } = get()
          return backups
            .filter(b => b.status === 'completed')
            .reduce((total, backup) => {
              const size = parseFloat(backup.size.split(' ')[0])
              const unit = backup.size.split(' ')[1]
              return total + (unit === 'GB' ? size * 1024 : size)
            }, 0)
        }
      }),
      {
        name: 'admin-store',
        // 永続化から除外するフィールド（一時的な状態）
        partialize: (state) => ({
          userFilters: state.userFilters,
          metricsTimeRange: state.metricsTimeRange,
          logFilters: state.logFilters,
          autoRefreshLogs: state.autoRefreshLogs,
          selectedBackupType: state.selectedBackupType
        })
      }
    ),
    { name: 'admin-store' }
  )
)

// Selector hooks for better performance
export const useAdminUsers = () => useAdminStore((state) => ({
  users: state.users,
  selectedUser: state.selectedUser,
  searchTerm: state.userSearchTerm,
  filters: state.userFilters,
  filteredUsers: state.getFilteredUsers(),
  actions: {
    setUsers: state.setUsers,
    selectUser: state.selectUser,
    setSearchTerm: state.setUserSearchTerm,
    setFilters: state.setUserFilters,
    updateUser: state.updateUser,
    toggleStatus: state.toggleUserStatus
  }
}))

export const useAdminMetrics = () => useAdminStore((state) => ({
  current: state.currentMetrics,
  history: state.metricsHistory,
  timeRange: state.metricsTimeRange,
  actions: {
    setCurrent: state.setCurrentMetrics,
    addToHistory: state.addMetricsToHistory,
    setTimeRange: state.setMetricsTimeRange
  }
}))

export const useAdminLogs = () => useAdminStore((state) => ({
  logs: state.logs,
  searchTerm: state.logSearchTerm,
  filters: state.logFilters,
  autoRefresh: state.autoRefreshLogs,
  filteredLogs: state.getFilteredLogs(),
  actions: {
    setLogs: state.setLogs,
    addLog: state.addLog,
    setSearchTerm: state.setLogSearchTerm,
    setFilters: state.setLogFilters,
    toggleAutoRefresh: state.toggleAutoRefreshLogs
  }
}))

export const useAdminAI = () => useAdminStore((state) => ({
  providers: state.aiProviders,
  editingProvider: state.editingProvider,
  actions: {
    setProviders: state.setAIProviders,
    updateProvider: state.updateAIProvider,
    setEditingProvider: state.setEditingProvider,
    toggleStatus: state.toggleProviderStatus
  }
}))

export const useAdminBackups = () => useAdminStore((state) => ({
  backups: state.backups,
  isCreating: state.isCreatingBackup,
  selectedType: state.selectedBackupType,
  totalSize: state.getTotalBackupSize(),
  actions: {
    setBackups: state.setBackups,
    addBackup: state.addBackup,
    updateBackup: state.updateBackup,
    deleteBackup: state.deleteBackup,
    setIsCreating: state.setIsCreatingBackup,
    setSelectedType: state.setSelectedBackupType
  }
}))