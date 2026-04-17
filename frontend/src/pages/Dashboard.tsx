import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'

type Event = { ts: string; group_id: number; kind: string; message: string }

export default function Dashboard() {
  const { data: groups = [] } = useQuery({
    queryKey: ['groups'],
    queryFn: api.listGroups,
    refetchInterval: 5000,
  })
  const [events, setEvents] = useState<Event[]>([])
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${location.host}/ws`)
    ws.onmessage = (e) => {
      try {
        const payload = JSON.parse(e.data) as Event
        setEvents((cur) => [payload, ...cur].slice(0, 100))
      } catch {}
    }
    wsRef.current = ws
    return () => { ws.close() }
  }, [])

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <section className="bg-white rounded border p-4">
        <h2 className="font-semibold mb-3">Active groups</h2>
        {groups.length === 0 && <div className="text-sm text-slate-500">No groups yet. Go to Groups to create one.</div>}
        <ul className="space-y-2">
          {groups.map((g) => (
            <li key={g.id} className="flex justify-between border-b py-2 text-sm">
              <div>
                <div className="font-medium">{g.name}</div>
                <div className="text-slate-500">{g.mappings.length} followers</div>
              </div>
              <span className={`text-xs px-2 py-1 rounded ${g.is_active ? 'bg-green-100 text-green-800' : 'bg-slate-100 text-slate-600'}`}>
                {g.is_active ? 'running' : 'stopped'}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section className="bg-white rounded border p-4">
        <h2 className="font-semibold mb-3">Live events</h2>
        <div className="max-h-96 overflow-auto font-mono text-xs space-y-1">
          {events.length === 0 && <div className="text-slate-500">Waiting for events...</div>}
          {events.map((e, i) => (
            <div key={i}>
              <span className="text-slate-400">[{new Date(e.ts).toLocaleTimeString()}]</span>{' '}
              <span className="text-slate-600">g{e.group_id}</span>{' '}
              <span className="text-blue-700">{e.kind}</span>{' '}
              {e.message}
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
