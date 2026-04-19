import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState, type CSSProperties, type ReactNode } from "react"
import { api, type Account } from "../lib/api"
import { Panel, StatusPill, type PillStatus } from "../components/atoms"

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

const btnPrimary: CSSProperties = {
  padding: "9px 16px",
  fontSize: 11,
  letterSpacing: "0.14em",
  fontWeight: 700,
  color: "#0a0d10",
  background: "var(--accent)",
  border: "none",
  borderRadius: 2,
  cursor: "pointer",
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

function accountStatus(s: string): PillStatus {
  const x = (s || "").toLowerCase()
  if (x === "ok" || x === "connected") return "synced"
  if (x === "error" || x === "failed") return "error"
  if (x === "lagging") return "lagging"
  if (x === "") return "idle"
  return "paused"
}

export default function Accounts() {
  const qc = useQueryClient()
  const { data: accounts = [] } = useQuery({ queryKey: ["accounts"], queryFn: api.listAccounts })

  const [broker, setBroker] = useState<"tradovate" | "projectx">("tradovate")
  const [label, setLabel] = useState("")
  const [env, setEnv] = useState<"live" | "demo">("demo")
  const [tradovate, setTradovate] = useState({ name: "", password: "", cid: "", sec: "" })
  const [projectx, setProjectx] = useState({ username: "", api_key: "", base_url: "" })

  const create = useMutation({
    mutationFn: () =>
      api.createAccount({
        broker,
        label,
        env,
        credentials:
          broker === "tradovate"
            ? { ...tradovate, cid: Number(tradovate.cid) }
            : { ...projectx, base_url: projectx.base_url || null },
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["accounts"] })
      qc.invalidateQueries({ queryKey: ["stats"] })
      setLabel("")
      setTradovate({ name: "", password: "", cid: "", sec: "" })
      setProjectx({ username: "", api_key: "", base_url: "" })
    },
  })
  const testAcc = useMutation({
    mutationFn: (id: number) => api.testAccount(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["accounts"] }),
  })
  const del = useMutation({
    mutationFn: (id: number) => api.deleteAccount(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["accounts"] })
      qc.invalidateQueries({ queryKey: ["stats"] })
    },
  })

  return (
    <div
      style={{
        flex: 1,
        minHeight: 0,
        display: "grid",
        gridTemplateColumns: "1fr 1.4fr",
        gap: 1,
        background: "var(--line)",
        padding: 1,
      }}
    >
      <div style={{ background: "var(--bg)", minHeight: 0 }}>
        <Panel title="ADD BROKER ACCOUNT" subtitle="TRADOVATE · PROJECTX">
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <Field label="BROKER">
                <select
                  style={inputStyle}
                  value={broker}
                  onChange={(e) => setBroker(e.target.value as "tradovate" | "projectx")}
                >
                  <option value="tradovate">Tradovate</option>
                  <option value="projectx">ProjectX</option>
                </select>
              </Field>
              <Field label="ENV">
                <select
                  style={inputStyle}
                  value={env}
                  onChange={(e) => setEnv(e.target.value as "live" | "demo")}
                >
                  <option value="demo">demo</option>
                  <option value="live">live</option>
                </select>
              </Field>
            </div>
            <Field label="LABEL">
              <input
                style={inputStyle}
                className="mono"
                placeholder="Topstep 50k · A"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
              />
            </Field>

            {broker === "tradovate" ? (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <Field label="USERNAME">
                  <input
                    style={inputStyle}
                    className="mono"
                    value={tradovate.name}
                    onChange={(e) => setTradovate({ ...tradovate, name: e.target.value })}
                  />
                </Field>
                <Field label="PASSWORD">
                  <input
                    style={inputStyle}
                    className="mono"
                    type="password"
                    value={tradovate.password}
                    onChange={(e) => setTradovate({ ...tradovate, password: e.target.value })}
                  />
                </Field>
                <Field label="CID">
                  <input
                    style={inputStyle}
                    className="mono"
                    value={tradovate.cid}
                    onChange={(e) => setTradovate({ ...tradovate, cid: e.target.value })}
                  />
                </Field>
                <Field label="SEC">
                  <input
                    style={inputStyle}
                    className="mono"
                    value={tradovate.sec}
                    onChange={(e) => setTradovate({ ...tradovate, sec: e.target.value })}
                  />
                </Field>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <Field label="USERNAME">
                  <input
                    style={inputStyle}
                    className="mono"
                    value={projectx.username}
                    onChange={(e) => setProjectx({ ...projectx, username: e.target.value })}
                  />
                </Field>
                <Field label="API KEY">
                  <input
                    style={inputStyle}
                    className="mono"
                    value={projectx.api_key}
                    onChange={(e) => setProjectx({ ...projectx, api_key: e.target.value })}
                  />
                </Field>
                <Field label="BASE URL (OPTIONAL)">
                  <input
                    style={inputStyle}
                    className="mono"
                    placeholder="https://api.topstepx.com"
                    value={projectx.base_url}
                    onChange={(e) => setProjectx({ ...projectx, base_url: e.target.value })}
                  />
                </Field>
              </div>
            )}

            <button
              style={{ ...btnPrimary, opacity: !label || create.isPending ? 0.5 : 1 }}
              disabled={!label || create.isPending}
              onClick={() => create.mutate()}
            >
              {create.isPending ? "SAVING..." : "+ ADD ACCOUNT"}
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
        <Panel title="ACCOUNTS" subtitle={`${accounts.length} REGISTERED`} pad={false}>
          <div className="scroll" style={{ overflow: "auto", flex: 1 }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ background: "var(--bg-2)", borderBottom: "1px solid var(--line)" }}>
                  {["LABEL", "BROKER", "ENV", "STATUS", "LAST SEEN", ""].map((h) => (
                    <th
                      key={h}
                      className="mono"
                      style={{
                        textAlign: "left",
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
                {accounts.map((a: Account) => (
                  <tr
                    key={a.id}
                    style={{
                      borderBottom: "1px solid var(--line)",
                      height: "var(--density-row)",
                    }}
                  >
                    <td style={{ padding: "0 12px", fontWeight: 600 }}>{a.label}</td>
                    <td className="mono" style={{ padding: "0 12px", color: "var(--fg-dim)" }}>
                      {a.broker}
                    </td>
                    <td className="mono" style={{ padding: "0 12px", color: "var(--fg-dim)" }}>
                      {a.env}
                    </td>
                    <td style={{ padding: "0 12px" }}>
                      <StatusPill status={accountStatus(a.status)} />
                    </td>
                    <td className="mono" style={{ padding: "0 12px", color: "var(--fg-dim)" }}>
                      {a.last_seen_at ? new Date(a.last_seen_at).toLocaleTimeString("en-US", { hour12: false }) : "—"}
                    </td>
                    <td style={{ padding: "0 8px", textAlign: "right", whiteSpace: "nowrap" }}>
                      <button
                        onClick={() => testAcc.mutate(a.id)}
                        className="mono"
                        style={{
                          fontSize: 10,
                          padding: "4px 10px",
                          color: "var(--accent)",
                          border: "1px solid var(--accent-dim)",
                          borderRadius: 2,
                          letterSpacing: "0.08em",
                          marginRight: 6,
                          background: "transparent",
                        }}
                      >
                        TEST
                      </button>
                      <button
                        onClick={() => del.mutate(a.id)}
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
                ))}
                {accounts.length === 0 && (
                  <tr>
                    <td
                      colSpan={6}
                      className="mono"
                      style={{
                        padding: 20,
                        fontSize: 11,
                        color: "var(--fg-mute)",
                        letterSpacing: "0.08em",
                        textAlign: "center",
                      }}
                    >
                      NO ACCOUNTS · USE THE FORM TO ADD ONE
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
