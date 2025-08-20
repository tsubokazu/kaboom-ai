'use client'

import { useEffect, useState, useCallback } from 'react'
import { CheckCircleIcon, ExclamationCircleIcon, ExclamationTriangleIcon, InformationCircleIcon, XMarkIcon } from '@heroicons/react/24/outline'

export interface ToastData {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  duration?: number
  autoClose?: boolean
}

interface ToastProps {
  toast: ToastData
  onClose: (id: string) => void
}

const toastStyles = {
  success: {
    container: 'bg-green-50 border-green-200 text-green-800 dark:bg-green-900/50 dark:border-green-700 dark:text-green-200',
    icon: CheckCircleIcon,
    iconColor: 'text-green-400 dark:text-green-300'
  },
  error: {
    container: 'bg-red-50 border-red-200 text-red-800 dark:bg-red-900/50 dark:border-red-700 dark:text-red-200',
    icon: ExclamationCircleIcon,
    iconColor: 'text-red-400 dark:text-red-300'
  },
  warning: {
    container: 'bg-yellow-50 border-yellow-200 text-yellow-800 dark:bg-yellow-900/50 dark:border-yellow-700 dark:text-yellow-200',
    icon: ExclamationTriangleIcon,
    iconColor: 'text-yellow-400 dark:text-yellow-300'
  },
  info: {
    container: 'bg-blue-50 border-blue-200 text-blue-800 dark:bg-blue-900/50 dark:border-blue-700 dark:text-blue-200',
    icon: InformationCircleIcon,
    iconColor: 'text-blue-400 dark:text-blue-300'
  }
}

export function Toast({ toast, onClose }: ToastProps) {
  const [isVisible, setIsVisible] = useState(false)
  const [isLeaving, setIsLeaving] = useState(false)
  
  const style = toastStyles[toast.type]
  const IconComponent = style.icon

  const handleClose = useCallback(() => {
    setIsLeaving(true)
    setTimeout(() => {
      onClose(toast.id)
    }, 300)
  }, [onClose, toast.id])

  useEffect(() => {
    // Trigger enter animation
    const timer = setTimeout(() => setIsVisible(true), 10)
    return () => clearTimeout(timer)
  }, [])

  useEffect(() => {
    if (toast.autoClose !== false && toast.duration) {
      const timer = setTimeout(() => {
        handleClose()
      }, toast.duration)

      return () => clearTimeout(timer)
    }
  }, [toast.autoClose, toast.duration, handleClose])

  return (
    <div
      className={`
        relative max-w-sm w-full border rounded-lg shadow-lg p-4 mb-4 transition-all duration-300 ease-in-out transform
        ${style.container}
        ${isVisible && !isLeaving 
          ? 'translate-x-0 opacity-100 scale-100' 
          : 'translate-x-full opacity-0 scale-95'
        }
      `}
    >
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <IconComponent className={`h-5 w-5 ${style.iconColor}`} />
        </div>
        <div className="ml-3 flex-1">
          <h3 className="text-sm font-medium">
            {toast.title}
          </h3>
          {toast.message && (
            <p className="mt-1 text-sm opacity-90">
              {toast.message}
            </p>
          )}
        </div>
        <div className="ml-4 flex-shrink-0">
          <button
            className={`
              inline-flex rounded-md p-1.5 transition-colors
              hover:bg-black/5 dark:hover:bg-white/5
              focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-transparent
              ${toast.type === 'success' ? 'focus:ring-green-400' : ''}
              ${toast.type === 'error' ? 'focus:ring-red-400' : ''}
              ${toast.type === 'warning' ? 'focus:ring-yellow-400' : ''}
              ${toast.type === 'info' ? 'focus:ring-blue-400' : ''}
            `}
            onClick={handleClose}
          >
            <XMarkIcon className="h-4 w-4 opacity-70 hover:opacity-100" />
          </button>
        </div>
      </div>
      
      {/* Progress bar for auto-close */}
      {toast.autoClose !== false && toast.duration && (
        <div className="absolute bottom-0 left-0 right-0 h-1 bg-black/10 dark:bg-white/10 rounded-b-lg overflow-hidden">
          <div
            className={`
              h-full transition-all linear
              ${toast.type === 'success' ? 'bg-green-400' : ''}
              ${toast.type === 'error' ? 'bg-red-400' : ''}
              ${toast.type === 'warning' ? 'bg-yellow-400' : ''}
              ${toast.type === 'info' ? 'bg-blue-400' : ''}
            `}
            style={{
              width: '100%',
              animationName: 'toast-progress',
              animationDuration: `${toast.duration}ms`,
              animationTimingFunction: 'linear',
              animationFillMode: 'forwards'
            }}
          />
        </div>
      )}

      <style jsx>{`
        @keyframes toast-progress {
          from {
            width: 100%;
          }
          to {
            width: 0%;
          }
        }
      `}</style>
    </div>
  )
}

interface ToastContainerProps {
  toasts: ToastData[]
  onClose: (id: string) => void
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center'
}

const positionStyles = {
  'top-right': 'top-4 right-4',
  'top-left': 'top-4 left-4', 
  'bottom-right': 'bottom-4 right-4',
  'bottom-left': 'bottom-4 left-4',
  'top-center': 'top-4 left-1/2 transform -translate-x-1/2',
  'bottom-center': 'bottom-4 left-1/2 transform -translate-x-1/2'
}

export function ToastContainer({ toasts, onClose, position = 'top-right' }: ToastContainerProps) {
  return (
    <div 
      className={`fixed z-50 ${positionStyles[position]} pointer-events-none`}
      aria-live="assertive"
      aria-atomic="true"
    >
      <div className="flex flex-col space-y-2 pointer-events-auto">
        {toasts.map((toast) => (
          <Toast key={toast.id} toast={toast} onClose={onClose} />
        ))}
      </div>
    </div>
  )
}