import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api, type Mapping } from '../lib/api'

export default function Groups() {
  const qc = useQueryClient()
  const { data: accounts = [] } = useQuery({ queryKey: ['accounts'], queryFn: api.listAccounts })
  const { data: groups = [] } = useQuery({ queryKey: ['groups'], queryFn: api.listGroups })

  const [name, setName] = useState('')
  const [leaderId, setLeaderId] = useState<number | ''>('')
  const [mappings, setMappings] = useState<Partial<Mapping>[]>([])

  const create = useMutation({
    mutationFn: () =>
      api.createGroup({
        name,
        leader_account_id: leaderId,
        mappings: mappings.map((m) => ({
          follower_account_id: m.follower_account_id,
          size_mode: m.size_mode || 'ratio',
          size_value: m.size_value ?? 1,
          reverse: !!m.reverse,
        })),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['groups'] })
      setName(''); setLeaderId(''); setMappings([])
    },
  })
  const start = useMutation({ mutationFn: (id: number) => api.startGroup(id), onSuccess: () => qc.invalidateQueries({ queryKey: ['groups'] }) })
  const stop = useMutation({ mutationFn: (id: number) => api.stopGroup(id), onSuccess: () => qc.invalidateQueries({ queryKey: ['groups'] }) })
  const del = useMutation({ mutationFn: (id: number) => api.deleteGroup(id), onSuccess: () => qc.invalidateQueries({ queryKey: ['groups'] }) })

  return (
    <div className="space-y-6">
      <section className="bg-white rounded border p-4">
        <h2 className="font-semibold mb-3">New group</h2>
        <div className="grid grid-cols-2 gap-2 mb-3">
          <input className="border p-2 rounded" placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
          <select className="border p-2 rounded" value={leaderId} onChange={(e) => setLeaderId(Number(e.target.value) || '')}>
            <option value="">-- Leader account --</option>
            {accounts.map((a) => <option key={a.id} value={a.id}>{a.label} ({a.broker})</option>)}
          </select>
        </div>
        <div className="space-y-2">
          <div className="font-medium text-sm">Followers</div>
          {mappings.map((m, i) => (
            <div key={i} className="grid grid-cols-5 gap-2">
              <select className="border p-2 rounded col-span-2" value={m.follower_account_id || ''} onChange={(e) => {
                const next = [...mappings]; next[i] = { ...m, follower_account_id: Number(e.target.value) }; setMappings(next)
              }}>
                <option value="">-- account --</option>
                {accounts.filter((a) => a.id !== leaderId).map((a) => <option key={a.id} value={a.id}>{a.label} ({a.broker})</option>)}
              </select>
              <select className="border p-2 rounded" value={m.size_mode || 'ratio'} onChange={(e) => {
                const next = [...mappings]; next[i] = { ...m, size_mode: e.target.value as any }; setMappings(next)
              }}>
                <option value="ratio">ratio</option>
                <option value="fixed">fixed</option>
                <option value="equity_scaled">equity_scaled</option>
              </select>
              <input type="number" step="0.1" className="border p-2 rounded" value={m.size_value ?? 1} onChange={(e) => {
                const next = [...mappings]; next[i] = { ...m, size_value: Number(e.target.value) }; setMappings(next)
              }} />
              <label className="flex items-center gap-1 text-sm">
                <input type="checkbox" checked={!!m.reverse} onChange={(e) => {
                  const next = [...mappings]; next[i] = { ...m, reverse: e.target.checked }; setMappings(next)
                }} /> reverse
              </label>
            </div>
          ))}
          <button className="text-sm text-blue-600" onClick={() => setMappings([...mappings, {}])}>+ add follower</button>
        </div>
        <button
          className="mt-3 bg-slate-900 text-white rounded px-4 py-2 disabled:opacity-50"
          disabled={!name || !leaderId || mappings.length === 0}
          onClick={() => create.mutate()}
        >
          Create group
        </button>
      </section>

      <section className="bg-white rounded border p-4">
        <h2 className="font-semibold mb-3">Groups</h2>
        <table className="w-full text-sm">
          <thead><tr className="text-left text-slate-500"><th>Name</th><th>Leader</th><th>Followers</th><th>Active</th><th></th></tr></thead>
          <tbody>
            {groups.map((g) => (
              <tr key={g.id} className="border-t">
                <td className="py-1">{g.name}</td>
                <td>{accounts.find((a) => a.id === g.leader_account_id)?.label}</td>
                <td>{g.mappings.length}</td>
                <td>{g.is_active ? 'yes' : 'no'}</td>
                <td className="text-right">
                  {g.is_active ? (
                    <button className="text-orange-600 mr-2" onClick={() => stop.mutate(g.id)}>Stop</button>
                  ) : (
                    <button className="text-green-700 mr-2" onClick={() => start.mutate(g.id)}>Start</button>
                  )}
                  <button className="text-red-600" onClick={() => del.mutate(g.id)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  )
}
