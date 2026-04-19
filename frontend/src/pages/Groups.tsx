import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState, type CSSProperties, type ReactNode } from "react"
import { api, type Account, type Mapping } from "../lib/api"
import { Panel, StatusPill, type PillStatus } from "../components/atoms"
import { colorForGroup } from "../lib/format"

const inputStyle: CSSProperties = {
  padding: "8px 10px",
  fontSize: 12,
  background: "var(--bg-2)",
  border: "1px solid var(--line-2)",
  color: "var(--fg)",
  borderRadius: 2,
  outline: "none",
  width: "100%",
  boxSizing: "border-box",
  fontFamily: "inherit",
}

const labelStyle: CSSProperties = {
  fontSize: 10,
  color: "var(--fg-mute)",
  letterSpacing: "0.12em",
  marginBottom: 4,
  display: "block",
  textTransform: "uppercase",
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <div className="mono" style={labelStyle}>
        {label}
      </div>
      {children}
    </div>
  )
}

function groupStatus(active: boolean): PillStatus {
  return active ? "live" : "paused"
}

export default function Groups() {
  const qc = useQueryClient()
  const { data: accounts = [] } = useQuery({ queryKey: ["accounts"], queryFn: api.listAccounts })
  const { data: groups = [] } = useQuery({
    queryKey: ["groups"],
    queryFn: api.listGroups,
    refetchInterval: 5000,
  })

  const [name, setName] = useState("")
  const [leaderId, setLeaderId] = useState<number | "">("")
  const [mappings, setMappings] = useState<Partial<Mapping>[]>([])

  const accById = new Map<number, Account>(accounts.map((a) => [a.id, a]))

  const create = useMutation({
    mutationFn: () =>
      api.createGroup({
        name,
        leader_account_id: leaderId,
        mappings: mappings.map((m) => ({
          follower_account_id: m.follower_account_id,
          size_mode: m.size_mode || "ratio",
          size_value: m.size_value ?? 1,
          reverse: !!m.reverse,
        })),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["groups"] })
      qc.invalidateQueries({ queryKey: ["stats"] })
      setName("")
      setLeaderId("")
      setMappings([])
    },
  })
  const start = useMutation({
    mutationFn: (id: number) => api.startGroup(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["groups"] })
      qc.invalidateQueries({ queryKey: ["stats"] })
    },
  })
  const stop = useMutation({
    mutationFn: (id: number) => api.stopGroup(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["groups"] })
      qc.invalidateQueries({ queryKey: ["stats"] })
    },
  })
  const del = useMutation({
    mutationFn: (id: number) => api.deleteGroup(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["groups"] })
      qc.invalidateQueries({ queryKey: ["stats"] })
    },
  })

  const canCreate = !!name && !!leaderId && mappings.length > 0

  return (
    <div
      style={{
        flex: 1,
        minHeight: 0,
        display: "grid",
        gridTemplateColumns: "1fr 1.2fr",
        gap: 1,
        background: "var(--line)",
        padding: 1,
      }}
    >
      <div style={{ background: "var(--bg)", minHeight: 0 }}>
        <Panel
          title="NEW COPY GROUP"
          subtitle="1 LEADER → N FOLLOWERS"
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <Field label="NAME">
              <input
                style={inputStyle}
                className="mono"
                placeholder="MNQ Scalper · Apex"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </Field>
            <Field label="LEADER ACCOUNT">
              <select
                style={inputStyle}
                className="mono"
                value={leaderId}
                onChange={(e) => setLeaderId(Number(e.target.value) || "")}
              >
                <option value="">-- select --</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.label} ({a.broker} · {a.env})
                  </option>
                ))}
              </select>
            </Field>

            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                borderTop: "1px solid var(--line)",
                paddingTop: 12,
              }}
            >
              <div className="mono" style={labelStyle}>
                FOLLOWERS · {mappings.length}
              </div>
              <button
                onClick={() => setMappings([...mappings, { size_mode: "ratio", size_value: 1 }])}
                className="mono"
                style={{
                  fontSize: 10,
                  color: "var(--accent)",
                  letterSpacing: "0.1em",
                  background: "transparent",
                  border: "1px solid var(--accent-dim)",
                  padding: "4px 10px",
                  borderRadius: 2,
                  cursor: "pointer",
                }}
              >
                + ADD FOLLOWER
              </button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {mappings.map((m, i) => (
                <div
                  key={i}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "2fr 1fr 1fr auto",
                    gap: 6,
                    alignItems: "center",
                  }}
                >
                  <select
                    style={inputStyle}
                    className="mono"
                    value={m.follower_account_id || ""}
                    onChange={(e) => {
                      const next = [...mappings]
                      next[i] = { ...m, follower_account_id: Number(e.target.value) }
                      setMappings(next)
                    }}
                  >
                    <option value="">-- account --</option>
                    {accounts
                      .filter((a) => a.id !== leaderId)
                      .map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.label} ({a.broker})
                        </option>
                      ))}
                  </select>
                  <select
                    style={inputStyle}
                    className="mono"
                    value={m.size_mode || "ratio"}
                    onChange={(e) => {
                      const next = [...mappings]
                      next[i] = { ...m, size_mode: e.target.value as Mapping["size_mode"] }
                      setMappings(next)
                    }}
                  >
                    <option value="ratio">ratio</option>
                    <option value="fixed">fixed</option>
                    <option value="equity_scaled">eq-scaled</option>
                  </select>
                  <input
                    type="number"
                    step="0.1"
                    style={inputStyle}
                    className="num"
                    value={m.size_value ?? 1}
                    onChange={(e) => {
                      const next = [...mappings]
                      next[i] = { ...m, size_value: Number(e.target.value) }
                      setMappings(next)
                    }}
                  />
                  <button
                    onClick={() => setMappings(mappings.filter((_, j) => j !== i))}
                    className="mono"
                    style={{
                      fontSize: 10,
                      color: "var(--crit)",
                      padding: "4px 8px",
                      letterSpacing: "0.1em",
                      background: "transparent",
                      border: "1px solid var(--line-2)",
                      borderRadius: 2,
                      cursor: "pointer",
                    }}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>

            <button
              onClick={() => create.mutate()}
              disabled={!canCreate || create.isPending}
              className="mono"
              style={{
                padding: "9px 16px",
                fontSize: 11,
                letterSpacing: "0.14em",
                fontWeight: 700,
                color: "#0a0d10",
                background: "var(--accent)",
                border: "none",
                borderRadius: 2,
                opacity: !canCreate || create.isPending ? 0.5 : 1,
                cursor: !canCreate ? "not-allowed" : "pointer",
              }}
            >
              {create.isPending ? "CREATING..." : "+ CREATE GROUP"}
            </button>
            {create.isError && (
              <div
                className="mono"
                style={{ color: "var(--crit)", fontSize: 10, letterSpacing: "0.08em" }}
              >
                ERR · {(create.error as Error).message}
              </div>
            )}
          </div>
        </Panel>
      </div>

      <div style={{ background: "var(--bg)", minHeight: 0 }}>
        <Panel title="GROUPS" subtitle={`${groups.length} TOTAL`} pad={false}>
          <div className="scroll" style={{ overflow: "auto", flex: 1 }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ background: "var(--bg-2)", borderBottom: "1px solid var(--line)" }}>
                  {["GROUP", "LEADER", "FOLLOWERS", "STATE", ""].map((h) => (
                    <th
                      key={h}
                      className="mono"
                      style={{
                        textAlign: h === "FOLLOWERS" ? "right" : "left",
                        padding: "10px 12px",
                        fontSize: 9,
                        fontWeight: 500,
                        color: "var(--fg-mute)",
                        letterSpacing: "0.12em",
                        position: "sticky",
                        top: 0,
                        background: "var(--bg-2)",
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {groups.map((g) => {
                  const leader = accById.get(g.leader_account_id)
                  return (
                    <tr
                      key={g.id}
                      style={{
                        borderBottom: "1px solid var(--line)",
                        height: "var(--density-row)",
                      }}
                    >
                      <td style={{ padding: "0 12px" }}>
                        <span
                          style={{ display: "inline-flex", alignItems: "center", gap: 6 }}
                        >
                          <span
                            style={{
                              width: 3,
                              height: 14,
                              background: colorForGroup(g.id),
                            }}
                          />
                          <span style={{ fontWeight: 600 }}>{g.name}</span>
                        </span>
                      </td>
                      <td
                        className="mono"
                        style={{ padding: "0 12px", color: "var(--fg-dim)" }}
                      >
                        {leader?.label || "?"}
                      </td>
                      <td
                        className="num"
                        style={{ padding: "0 12px", textAlign: "right" }}
                      >
                        {g.mappings.length}
                      </td>
                      <td style={{ padding: "0 12px" }}>
                        <StatusPill status={groupStatus(g.is_active)} />
                      </td>
                      <td style={{ padding: "0 8px", textAlign: "right", whiteSpace: "nowrap" }}>
                        {g.is_active ? (
                          <button
                            onClick={() => stop.mutate(g.id)}
                            className="mono"
                            style={{
                              fontSize: 10,
                              padding: "4px 10px",
                              color: "var(--warn)",
                              border: "1px solid var(--line-2)",
                              borderRadius: 2,
                              letterSpacing: "0.08em",
                              marginRight: 6,
                              background: "transparent",
                            }}
                          >
                            STOP
                          </button>
                        ) : (
                          <button
                            onClick={() => start.mutate(g.id)}
                            className="mono"
                            style={{
                              fontSize: 10,
                              padding: "4px 10px",
                              color: "var(--accent)",
                              border: "1px solid var(--accent-dim)",
                              borderRadius: 2,
                              letterSpacing: "0.08em",
                              marginRight: 6,
                              background: "var(--accent-bg)",
                            }}
                          >
                            START
                          </button>
                        )}
                        <button
                          onClick={() => del.mutate(g.id)}
                          className="mono"
                          style={{
                            fontSize: 10,
                            padding: "4px 10px",
                            color: "var(--crit)",
                            border: "1px solid var(--line-2)",
                            borderRadius: 2,
                            letterSpacing: "0.08em",
                            background: "transparent",
                          }}
                        >
                          DEL
                        </button>
                      </td>
                    </tr>
                  )
                })}
                {groups.length === 0 && (
                  <tr>
                    <td
                      colSpan={5}
                      className="mono"
                      style={{
                        padding: 20,
                        fontSize: 11,
                        color: "var(--fg-mute)",
                        letterSpacing: "0.08em",
                        textAlign: "center",
                      }}
                    >
                      NO GROUPS YET
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>
    </div>
  )
}
