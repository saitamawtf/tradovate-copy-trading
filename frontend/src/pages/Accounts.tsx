import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../lib/api'

export default function Accounts() {
  const qc = useQueryClient()
  const { data: accounts = [] } = useQuery({
    queryKey: ['accounts'],
    queryFn: api.listAccounts,
  })

  const [broker, setBroker] = useState<'tradovate' | 'projectx'>('tradovate')
  const [label, setLabel] = useState('')
  const [env, setEnv] = useState<'live' | 'demo'>('demo')
  const [tradovate, setTradovate] = useState({ name: '', password: '', cid: '', sec: '' })
  const [projectx, setProjectx] = useState({ username: '', api_key: '', base_url: '' })

  const create = useMutation({
    mutationFn: () =>
      api.createAccount({
        broker,
        label,
        env,
        credentials:
          broker === 'tradovate'
            ? { ...tradovate, cid: Number(tradovate.cid) }
            : { ...projectx, base_url: projectx.base_url || null },
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['accounts'] }),
  })
  const testAcc = useMutation({
    mutationFn: (id: number) => api.testAccount(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['accounts'] }),
  })
  const del = useMutation({
    mutationFn: (id: number) => api.deleteAccount(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['accounts'] }),
  })

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <section className="bg-white rounded border p-4">
        <h2 className="font-semibold mb-3">Add broker account</h2>
        <div className="space-y-2">
          <div className="flex gap-2">
            <select className="border p-2 rounded" value={broker} onChange={(e) => setBroker(e.target.value as any)}>
              <option value="tradovate">Tradovate</option>
              <option value="projectx">ProjectX</option>
            </select>
            <select className="border p-2 rounded" value={env} onChange={(e) => setEnv(e.target.value as any)}>
              <option value="demo">demo</option>
              <option value="live">live</option>
            </select>
            <input className="border p-2 rounded flex-1" placeholder="Label" value={label} onChange={(e) => setLabel(e.target.value)} />
          </div>
          {broker === 'tradovate' ? (
            <div className="grid grid-cols-2 gap-2">
              <input className="border p-2 rounded" placeholder="username" value={tradovate.name} onChange={(e) => setTradovate({ ...tradovate, name: e.target.value })} />
              <input className="border p-2 rounded" placeholder="password" type="password" value={tradovate.password} onChange={(e) => setTradovate({ ...tradovate, password: e.target.value })} />
              <input className="border p-2 rounded" placeholder="cid" value={tradovate.cid} onChange={(e) => setTradovate({ ...tradovate, cid: e.target.value })} />
              <input className="border p-2 rounded" placeholder="sec" value={tradovate.sec} onChange={(e) => setTradovate({ ...tradovate, sec: e.target.value })} />
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-2">
              <input className="border p-2 rounded" placeholder="username" value={projectx.username} onChange={(e) => setProjectx({ ...projectx, username: e.target.value })} />
              <input className="border p-2 rounded" placeholder="api_key" value={projectx.api_key} onChange={(e) => setProjectx({ ...projectx, api_key: e.target.value })} />
              <input className="border p-2 rounded" placeholder="base_url (optional, e.g. https://api.topstepx.com)" value={projectx.base_url} onChange={(e) => setProjectx({ ...projectx, base_url: e.target.value })} />
            </div>
          )}
          <button
            className="bg-slate-900 text-white rounded px-4 py-2 disabled:opacity-50"
            disabled={!label || create.isPending}
            onClick={() => create.mutate()}
          >
            {create.isPending ? 'Saving...' : 'Add account'}
          </button>
          {create.isError && <div className="text-red-600 text-sm">{(create.error as Error).message}</div>}
        </div>
      </section>

      <section className="bg-white rounded border p-4">
        <h2 className="font-semibold mb-3">Accounts ({accounts.length})</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500">
              <th>Label</th><th>Broker</th><th>Env</th><th>Status</th><th></th>
            </tr>
          </thead>
          <tbody>
            {accounts.map((a) => (
              <tr key={a.id} className="border-t">
                <td className="py-1">{a.label}</td>
                <td>{a.broker}</td>
                <td>{a.env}</td>
                <td>{a.status}</td>
                <td className="text-right">
                  <button className="text-blue-600 mr-2" onClick={() => testAcc.mutate(a.id)}>Test</button>
                  <button className="text-red-600" onClick={() => del.mutate(a.id)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  )
}
