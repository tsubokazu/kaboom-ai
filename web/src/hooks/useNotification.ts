import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import { ToastData } from '@/components/ui/Toast'
import { WebSocketMessage } from '@/stores/websocketStore'

interface NotificationState {
  toasts: ToastData[]
  addToast: (toast: Omit<ToastData, 'id'>) => string
  removeToast: (id: string) => void
  clearAllToasts: () => void
  updateToast: (id: string, updates: Partial<ToastData>) => void
}

let toastIdCounter = 0

export const useNotificationStore = create<NotificationState>()(
  devtools(
    (set) => ({
      toasts: [],

      addToast: (toastData) => {
        const id = `toast-${++toastIdCounter}-${Date.now()}`
        const toast: ToastData = {
          id,
          duration: 5000,
          autoClose: true,
          ...toastData
        }

        set(state => ({
          toasts: [...state.toasts, toast]
        }))

        return id
      },

      removeToast: (id) => {
        set(state => ({
          toasts: state.toasts.filter(toast => toast.id !== id)
        }))
      },

      clearAllToasts: () => {
        set({ toasts: [] })
      },

      updateToast: (id, updates) => {
        set(state => ({
          toasts: state.toasts.map(toast =>
            toast.id === id ? { ...toast, ...updates } : toast
          )
        }))
      }
    }),
    { name: 'notification-store' }
  )
)

// Hook for using notifications
export function useNotification() {
  const { addToast, removeToast, clearAllToasts, updateToast, toasts } = useNotificationStore()

  // Convenience methods for different toast types
  const showSuccess = (title: string, message?: string, options?: Partial<ToastData>) => {
    return addToast({
      type: 'success',
      title,
      message: message || '',
      ...options
    })
  }

  const showError = (title: string, message?: string, options?: Partial<ToastData>) => {
    return addToast({
      type: 'error',
      title,
      message: message || '',
      duration: 8000, // Longer duration for errors
      ...options
    })
  }

  const showWarning = (title: string, message?: string, options?: Partial<ToastData>) => {
    return addToast({
      type: 'warning',
      title,
      message: message || '',
      ...options
    })
  }

  const showInfo = (title: string, message?: string, options?: Partial<ToastData>) => {
    return addToast({
      type: 'info',
      title,
      message: message || '',
      ...options
    })
  }

  // Loading toast with manual control
  const showLoading = (title: string, message?: string) => {
    return addToast({
      type: 'info',
      title,
      message: message || '',
      autoClose: false // Don't auto-close loading toasts
    })
  }

  // Update loading toast to success/error
  const updateLoadingToast = (id: string, type: 'success' | 'error', title: string, message?: string) => {
    updateToast(id, {
      type,
      title,
      message: message || '',
      autoClose: true,
      duration: type === 'error' ? 8000 : 5000
    })
  }

  return {
    toasts,
    showSuccess,
    showError, 
    showWarning,
    showInfo,
    showLoading,
    updateLoadingToast,
    addToast,
    removeToast,
    clearAllToasts,
    updateToast
  }
}

// Hook for WebSocket notifications specifically
export function useWebSocketNotifications() {
  const { showSuccess, showError, showWarning, showInfo } = useNotification()

  const handleWebSocketMessage = (message: WebSocketMessage) => {
    if (message.type === 'notification') {
      const { notificationType, title, message: content } = message.payload as {
        notificationType: string
        title?: string
        message: string
      }

      switch (notificationType) {
        case 'trade_executed':
          showSuccess('取引実行完了', content)
          break
        
        case 'trade_failed':
          showError('取引実行失敗', content)
          break
        
        case 'ai_analysis_complete':
          showInfo('AI分析完了', content)
          break
        
        case 'backtest_complete':
          showSuccess('バックテスト完了', content)
          break
        
        case 'backtest_failed':
          showError('バックテストエラー', content)
          break
        
        case 'system_warning':
          showWarning('システム警告', content)
          break
        
        case 'system_error':
          showError('システムエラー', content)
          break
        
        case 'connection_restored':
          showSuccess('接続復旧', 'WebSocket接続が復旧しました')
          break
        
        case 'connection_lost':
          showWarning('接続失敗', 'WebSocket接続が失われました。再接続を試行中...')
          break
        
        default:
          showInfo(title || '通知', content)
      }
    }
  }

  return {
    handleWebSocketMessage,
    showSuccess,
    showError,
    showWarning,
    showInfo
  }
}