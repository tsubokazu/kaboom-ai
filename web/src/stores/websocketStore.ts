import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

export interface WebSocketMessage {
  type: 'price_update' | 'ai_analysis' | 'system_metrics' | 'notification' | 'portfolio_update' | 'trade_execution' | 'backtest_progress' | 'ping' | 'pong'
  payload: Record<string, unknown>
  timestamp: string
  id: string
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error'

interface WebSocketState {
  socket: WebSocket | null
  connectionStatus: ConnectionStatus
  reconnectAttempts: number
  maxReconnectAttempts: number
  reconnectTimeout: NodeJS.Timeout | null
  lastMessage: WebSocketMessage | null
  subscriptions: Map<string, Set<(message: WebSocketMessage) => void>>
  isReconnecting: boolean
  connect: (url?: string) => void
  disconnect: () => void
  send: (message: Partial<WebSocketMessage>) => boolean
  subscribe: (eventType: string, callback: (message: WebSocketMessage) => void) => () => void
  clearSubscriptions: () => void
  resetReconnectAttempts: () => void
  scheduleReconnect: () => void
}

const WS_URL = process.env.NODE_ENV === 'development' 
  ? 'ws://localhost:8080/ws' 
  : `wss://${window.location.host}/ws`

const MAX_RECONNECT_ATTEMPTS = 10
const INITIAL_RECONNECT_DELAY = 1000

const websocketStore = (set: (partial: Partial<WebSocketState>) => void, get: () => WebSocketState) => ({
      socket: null,
      connectionStatus: 'disconnected',
      reconnectAttempts: 0,
      maxReconnectAttempts: MAX_RECONNECT_ATTEMPTS,
      reconnectTimeout: null,
      lastMessage: null,
      subscriptions: new Map<string, Set<(message: WebSocketMessage) => void>>(),
      isReconnecting: false,

      connect: (url = WS_URL) => {
        const state = get()
        
        if (state.socket?.readyState === WebSocket.CONNECTING || 
            state.socket?.readyState === WebSocket.OPEN) {
          return
        }

        set({ connectionStatus: 'connecting' })

        try {
          const socket = new WebSocket(url)

          socket.onopen = () => {
            console.log('WebSocket connected')
            set({ 
              connectionStatus: 'connected',
              reconnectAttempts: 0,
              isReconnecting: false
            })

            // Send heartbeat every 30 seconds
            const heartbeatInterval = setInterval(() => {
              if (socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                  type: 'ping',
                  timestamp: new Date().toISOString(),
                  id: Date.now().toString()
                }))
              } else {
                clearInterval(heartbeatInterval)
              }
            }, 30000)
          }

          socket.onmessage = (event) => {
            try {
              const message: WebSocketMessage = JSON.parse(event.data)
              
              // Handle pong messages
              if (message.type === 'pong') {
                return
              }

              set({ lastMessage: message })

              // Notify subscribers
              const { subscriptions } = get()
              const callbacks = subscriptions.get(message.type) || new Set()
              callbacks.forEach(callback => callback(message))

            } catch (error) {
              console.error('Failed to parse WebSocket message:', error)
            }
          }

          socket.onclose = (event) => {
            console.log('WebSocket disconnected:', event.code, event.reason)
            set({ socket: null, connectionStatus: 'disconnected' })

            // Auto-reconnect if not a manual disconnect
            if (event.code !== 1000 && !event.wasClean) {
              get().scheduleReconnect()
            }
          }

          socket.onerror = (error) => {
            // Only log actual errors, not connection failures
            if (error.type !== 'error' || socket.readyState !== WebSocket.CLOSED) {
              console.error('WebSocket error:', error.type || 'Connection error')
            }
            set({ connectionStatus: 'error' })
          }

          set({ socket })

        } catch (error) {
          console.error('Failed to create WebSocket connection:', error)
          set({ connectionStatus: 'error' })
          get().scheduleReconnect()
        }
      },

      disconnect: () => {
        const { socket, reconnectTimeout } = get()
        
        if (reconnectTimeout) {
          clearTimeout(reconnectTimeout)
        }

        if (socket) {
          socket.close(1000, 'Manual disconnect')
        }

        set({ 
          socket: null,
          connectionStatus: 'disconnected',
          reconnectTimeout: null,
          isReconnecting: false
        })
      },

      send: (message: Partial<WebSocketMessage>) => {
        const { socket } = get()
        
        if (!socket || socket.readyState !== WebSocket.OPEN) {
          console.warn('WebSocket is not connected')
          return false
        }

        try {
          const fullMessage: WebSocketMessage = {
            type: message.type || 'notification',
            payload: message.payload || {},
            timestamp: message.timestamp || new Date().toISOString(),
            id: message.id || Date.now().toString()
          }

          socket.send(JSON.stringify(fullMessage))
          return true
        } catch (error) {
          console.error('Failed to send WebSocket message:', error)
          return false
        }
      },

      subscribe: (eventType: string, callback: (message: WebSocketMessage) => void) => {
        const { subscriptions } = get()
        
        if (!subscriptions.has(eventType)) {
          subscriptions.set(eventType, new Set<(message: WebSocketMessage) => void>())
        }
        
        subscriptions.get(eventType)!.add(callback)

        // Return unsubscribe function
        return () => {
          const callbacks = subscriptions.get(eventType)
          if (callbacks) {
            callbacks.delete(callback)
            if (callbacks.size === 0) {
              subscriptions.delete(eventType)
            }
          }
        }
      },

      clearSubscriptions: () => {
        set({ subscriptions: new Map<string, Set<(message: WebSocketMessage) => void>>() })
      },

      resetReconnectAttempts: () => {
        set({ reconnectAttempts: 0 })
      },

      // Internal method for scheduling reconnection
      scheduleReconnect: () => {
        const { reconnectAttempts, maxReconnectAttempts, isReconnecting } = get()
        
        if (reconnectAttempts >= maxReconnectAttempts || isReconnecting) {
          console.warn('Max reconnection attempts reached or already reconnecting')
          return
        }

        const delay = Math.min(INITIAL_RECONNECT_DELAY * Math.pow(2, reconnectAttempts), 30000)
        
        set({ isReconnecting: true })
        
        console.log(`Scheduling reconnect in ${delay}ms (attempt ${reconnectAttempts + 1})`)
        
        const timeout = setTimeout(() => {
          set({ 
            reconnectAttempts: reconnectAttempts + 1,
            reconnectTimeout: null 
          })
          get().connect()
        }, delay)

        set({ reconnectTimeout: timeout })
      }
    })

export const useWebSocketStore = create<WebSocketState>()(
  devtools(websocketStore, { name: 'websocket-store' })
)

// Selector hooks with stable references
export const useWebSocketConnection = () => {
  const socket = useWebSocketStore(state => state.socket)
  const status = useWebSocketStore(state => state.connectionStatus)
  const isConnected = useWebSocketStore(state => state.connectionStatus === 'connected')
  
  return { socket, status, isConnected }
}

export const useWebSocketActions = () => {
  const connect = useWebSocketStore(state => state.connect)
  const disconnect = useWebSocketStore(state => state.disconnect)
  const send = useWebSocketStore(state => state.send)
  const subscribe = useWebSocketStore(state => state.subscribe)
  
  return { connect, disconnect, send, subscribe }
}