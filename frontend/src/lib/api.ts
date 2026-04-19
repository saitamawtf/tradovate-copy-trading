export type Account = {
  id: number
  broker: "tradovate" | "projectx"
  label: string
  env: "live" | "demo"
  external_account_id: string | null
  status: string
  last_seen_at: string | null
}

export type Mapping = {
  id: number
  follower_account_id: number
  size_mode: "fixed" | "ratio" | "equity_scaled"
  size_value: number
  reverse: boolean
}

export type Group = {
  id: number
  name: string
  leader_account_id: number
  is_active: boolean
  mappings: Mapping[]
}

export type GroupStatus = {
  id: number
  is_active: boolean
  leader_connected: boolean
  followers_connected: number
  followers_total: number
  last_events: Array<{
    ts: string
    kind: string
    symbol: string | null
    side: string | null
    qty: number
  }>
}

export type Stats = {
  accounts_total: number
  accounts_by_status: Record<string, number>
  groups_total: number
  groups_active: number
  running_group_ids: number[]
  copies_today: number
  fails_today: number
  fill_rate: number
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  })
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)
  return res.json() as Promise<T>
}

export const api = {
  listAccounts: () => request<Account[]>("/api/accounts"),
  createAccount: (body: any) =>
    request<Account>("/api/accounts", { method: "POST", body: JSON.stringify(body) }),
  testAccount: (id: number) =>
    request<{ ok: boolean; message: string; accounts: any[] }>(`/api/accounts/${id}/test`, {
      method: "POST",
    }),
  deleteAccount: (id: number) =>
    request<{ ok: boolean }>(`/api/accounts/${id}`, { method: "DELETE" }),

  listGroups: () => request<Group[]>("/api/groups"),
  createGroup: (body: any) =>
    request<Group>("/api/groups", { method: "POST", body: JSON.stringify(body) }),
  deleteGroup: (id: number) => request<{ ok: boolean }>(`/api/groups/${id}`, { method: "DELETE" }),
  startGroup: (id: number) =>
    request<{ ok: boolean }>(`/api/groups/${id}/start`, { method: "POST" }),
  stopGroup: (id: number) =>
    request<{ ok: boolean }>(`/api/groups/${id}/stop`, { method: "POST" }),
  groupStatus: (id: number) => request<GroupStatus>(`/api/groups/${id}/status`),

  stats: () => request<Stats>("/api/stats"),
}
