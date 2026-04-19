import { useEffect, useRef, useState } from "react"

export type LiveEvent = {
  ts: string
  group_id: number
  kind: string
  message: string
}

export function useEvents(limit = 200): LiveEvent[] {
  const [events, setEvents] = useState<LiveEvent[]>([])
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const proto = location.protocol === "https:" ? "wss" : "ws"
    const url = `${proto}://${location.host}/ws`
    let ws: WebSocket | null = null
    let stopped = false
    let retryMs = 1000

    const connect = () => {
      if (stopped) return
      ws = new WebSocket(url)
      wsRef.current = ws
      ws.onopen = () => (retryMs = 1000)
      ws.onmessage = (e) => {
        try {
          const payload = JSON.parse(e.data) as LiveEvent
          setEvents((cur) => [payload, ...cur].slice(0, limit))
        } catch {
          /* ignore */
        }
      }
      ws.onclose = () => {
        if (stopped) return
        setTimeout(connect, retryMs)
        retryMs = Math.min(retryMs * 2, 15_000)
      }
      ws.onerror = () => ws?.close()
    }
    connect()
    return () => {
      stopped = true
      ws?.close()
    }
  }, [limit])

  return events
}
