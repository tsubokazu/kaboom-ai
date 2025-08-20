import { useEffect, useCallback, useRef, useState } from 'react'
import { useWebSocketActions, useWebSocketConnection, WebSocketMessage } from '@/stores/websocketStore'

// Tab synchronization using BroadcastChannel
const BROADCAST_CHANNEL_NAME = 'kaboom-websocket-sync'
const MASTER_TAB_KEY = 'kaboom-master-tab'

export interface UseWebSocketOptions {
  autoConnect?: boolean
  url?: string
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: Event) => void
  onMessage?: (message: WebSocketMessage) => void
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    autoConnect = true,
    url,
    onConnect,
    onDisconnect,
    onError,
    onMessage
  } = options

  const { socket, status, isConnected } = useWebSocketConnection()
  const { connect, disconnect, send, subscribe } = useWebSocketActions()
  const broadcastChannelRef = useRef<BroadcastChannel | null>(null)
  const tabIdRef = useRef<string>(Date.now() + Math.random().toString(36))
  const isMasterTabRef = useRef<boolean>(false)

  // Initialize BroadcastChannel for tab synchronization
  useEffect(() => {
    if (typeof window === 'undefined') return

    const channel = new BroadcastChannel(BROADCAST_CHANNEL_NAME)
    broadcastChannelRef.current = channel

    // Check if this should be the master tab
    const existingMasterTab = localStorage.getItem(MASTER_TAB_KEY)
    if (!existingMasterTab) {
      localStorage.setItem(MASTER_TAB_KEY, tabIdRef.current)
      isMasterTabRef.current = true
    }

    // Listen for master tab messages
    const handleBroadcastMessage = (event: MessageEvent) => {
      const { type, data, tabId } = event.data

      switch (type) {
        case 'master-tab-claiming':
          if (tabId !== tabIdRef.current) {
            isMasterTabRef.current = false
          }
          break
        
        case 'websocket-data':
          // Sync WebSocket data across tabs
          if (tabId !== tabIdRef.current && onMessage) {
            onMessage(data)
          }
          break
        
        case 'connection-status':
          // Only non-master tabs should listen to status updates
          if (!isMasterTabRef.current && tabId !== tabIdRef.current) {
            // Sync connection status (implementation depends on needs)
          }
          break
      }
    }

    channel.addEventListener('message', handleBroadcastMessage)

    // Cleanup on page unload
    const handleBeforeUnload = () => {
      if (isMasterTabRef.current) {
        localStorage.removeItem(MASTER_TAB_KEY)
        channel.postMessage({
          type: 'master-tab-disconnecting',
          tabId: tabIdRef.current
        })
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)

    return () => {
      channel.removeEventListener('message', handleBroadcastMessage)
      window.removeEventListener('beforeunload', handleBeforeUnload)
      channel.close()
      
      if (isMasterTabRef.current) {
        localStorage.removeItem(MASTER_TAB_KEY)
      }
    }
  }, [onMessage])

  // Auto-connect only for master tab with stable dependency
  useEffect(() => {
    if (autoConnect && isMasterTabRef.current && !socket) {
      connect(url)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoConnect, url]) // Intentionally exclude socket and connect to prevent infinite loops

  // Handle connection events
  useEffect(() => {
    let unsubscribeConnect: (() => void) | undefined
    let unsubscribeDisconnect: (() => void) | undefined
    let unsubscribeError: (() => void) | undefined

    if (isMasterTabRef.current && socket) {
      if (onConnect && status === 'connected') {
        onConnect()
      }

      if (onDisconnect && status === 'disconnected') {
        onDisconnect()
      }

      if (onError && status === 'error') {
        onError(new Event('WebSocket error'))
      }

      // Subscribe to all messages if onMessage is provided
      if (onMessage) {
        const handleMessage = (message: WebSocketMessage) => {
          onMessage(message)
          
          // Broadcast to other tabs
          broadcastChannelRef.current?.postMessage({
            type: 'websocket-data',
            data: message,
            tabId: tabIdRef.current
          })
        }

        const unsubscribes = [
          'price_update',
          'ai_analysis', 
          'system_metrics',
          'notification',
          'portfolio_update',
          'trade_execution',
          'backtest_progress'
        ].map(eventType => subscribe(eventType, handleMessage))

        return () => {
          unsubscribes.forEach(unsubscribe => unsubscribe())
        }
      }
    }

    return () => {
      unsubscribeConnect?.()
      unsubscribeDisconnect?.()
      unsubscribeError?.()
    }
  }, [socket, status, onConnect, onDisconnect, onError, onMessage, subscribe])

  // Enhanced send function that works only for master tab
  const sendMessage = useCallback((message: Partial<WebSocketMessage>) => {
    if (!isMasterTabRef.current) {
      console.warn('Only master tab can send WebSocket messages')
      return false
    }
    return send(message)
  }, [send])

  // Manual connect/disconnect functions
  const connectManual = useCallback(() => {
    if (isMasterTabRef.current) {
      connect(url)
    }
  }, [connect, url])

  const disconnectManual = useCallback(() => {
    if (isMasterTabRef.current) {
      disconnect()
    }
  }, [disconnect])

  return {
    socket,
    status,
    isConnected,
    isMasterTab: isMasterTabRef.current,
    send: sendMessage,
    connect: connectManual,
    disconnect: disconnectManual,
    subscribe
  }
}

// Specialized hooks for specific data types
export function useWebSocketPrice(symbol?: string) {
  const [priceData, setPriceData] = useState<Record<string, unknown> | null>(null)
  const { subscribe } = useWebSocketActions()

  useEffect(() => {
    const unsubscribe = subscribe('price_update', (message: WebSocketMessage) => {
      if (!symbol || message.payload.symbol === symbol) {
        setPriceData(message.payload)
      }
    })

    return unsubscribe
  }, [symbol, subscribe])

  return priceData
}

export function useWebSocketSystemMetrics() {
  const [metrics, setMetrics] = useState<Record<string, unknown> | null>(null)
  const { subscribe } = useWebSocketActions()

  useEffect(() => {
    const unsubscribe = subscribe('system_metrics', (message: WebSocketMessage) => {
      setMetrics(message.payload)
    })

    return unsubscribe
  }, [subscribe])

  return metrics
}

export function useWebSocketNotifications() {
  const [notifications, setNotifications] = useState<WebSocketMessage[]>([])
  const { subscribe } = useWebSocketActions()

  useEffect(() => {
    const unsubscribe = subscribe('notification', (message: WebSocketMessage) => {
      setNotifications(prev => [...prev, message].slice(-10)) // Keep only last 10
    })

    return unsubscribe
  }, [subscribe])

  const clearNotifications = useCallback(() => {
    setNotifications([])
  }, [])

  return { notifications, clearNotifications }
}

export function useWebSocketAIAnalysis() {
  const [analysis, setAnalysis] = useState<Record<string, unknown> | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const { subscribe } = useWebSocketActions()

  useEffect(() => {
    const unsubscribe = subscribe('ai_analysis', (message: WebSocketMessage) => {
      setAnalysis(message.payload)
      setIsAnalyzing(false)
    })

    return unsubscribe
  }, [subscribe])

  const startAnalysis = useCallback(() => {
    setIsAnalyzing(true)
  }, [])

  return { analysis, isAnalyzing, startAnalysis }
}