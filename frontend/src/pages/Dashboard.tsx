import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useMemo } from "react"
import { api, type Account, type Group } from "../lib/api"
import { Dot, Panel, StatusPill, type PillStatus } from "../components/atoms"
import { colorForGroup } from "../lib/format"
import { useEvents, type LiveEvent } from "../lib/useEvents"

function groupStatus(g: Group): PillStatus {
  if (!g.is_active) return "paused"
  return "live"
}

function accountStatus(a: Account): PillStatus {
  const s = (a.status || "").toLowerCase()
  if (s === "ok" || s === "connected") return "synced"
  if (s === "error" || s === "failed") return "error"
  if (s === "lagging") return "lagging"
  if (s === "idle" || s === "") return "idle"
  return "paused"
}

function RelationshipsGraph({ groups, accounts }: { groups: Group[]; accounts: Account[] }) {
  const accById = useMemo(() => {
    const m = new Map<number, Account>()
    accounts.forEach((a) => m.set(a.id, a))
    return m
  }, [accounts])

  const running = groups.filter((g) => g.is_active).length

  return (
    <Panel
      title="COPY RELATIONSHIPS"
      subtitle={`${groups.length} GROUP${groups.length === 1 ? "" : "S"} → ${accounts.length} ACCOUNTS`}
      action={
        <div
          className="mono"
          style={{ display: "flex", gap: 12, fontSize: 10, color: "var(--fg-mute)" }}
        >
          <span><Dot color="#2dd4bf" size={5} /> LIVE {running}</span>
          <span><Dot color="#8b97a3" size={5} /> PAUSED {groups.length - running}</span>
        </div>
      }
    >
      {groups.length === 0 ? (
        <div
          className="mono"
          style={{ fontSize: 11, color: "var(--fg-mute)", padding: "20px 0", letterSpacing: "0.08em" }}
        >
          NO GROUPS · GO TO GROUPS TAB TO CREATE ONE
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
            gap: 12,
          }}
        >
          {groups.map((g) => {
            const leader = accById.get(g.leader_account_id)
            const color = colorForGroup(g.id)
            return (
              <div
                key={g.id}
                style={{
                  padding: 14,
                  background: "var(--bg-2)",
                  border: "1px solid var(--line)",
                  borderRadius: 2,
                  display: "flex",
                  flexDirection: "column",
                  gap: 12,
                  position: "relative",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    right: 0,
                    height: 2,
                    background: color,
                    opacity: g.is_active ? 1 : 0.35,
                  }}
                />
                <div
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    justifyContent: "space-between",
                    gap: 8,
                  }}
                >
                  <div style={{ minWidth: 0 }}>
                    <div
                      className="mono"
                      style={{ fontSize: 10, color: "var(--fg-mute)", letterSpacing: "0.12em" }}
                    >
                      G-{String(g.id).padStart(2, "0")}
                    </div>
                    <div
                      style={{
                        fontSize: 15,
                        fontWeight: 700,
                        letterSpacing: "-0.01em",
                        marginTop: 2,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {g.name}
                    </div>
                    <div
                      className="mono"
                      style={{ fontSize: 10, color: "var(--fg-dim)", marginTop: 2 }}
                    >
                      LEAD · {leader?.label || "?"} ({leader?.broker || "?"})
                    </div>
                  </div>
                  <StatusPill status={groupStatus(g)} />
                </div>

                <div>
                  <div
                    className="mono"
                    style={{
                      fontSize: 9,
                      color: "var(--fg-mute)",
                      letterSpacing: "0.1em",
                      marginBottom: 6,
                    }}
                  >
                    → {g.mappings.length} FOLLOWER{g.mappings.length === 1 ? "" : "S"}
                  </div>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fill, minmax(22px, 1fr))",
                      gap: 3,
                    }}
                  >
                    {g.mappings.map((m) => {
                      const a = accById.get(m.follower_account_id)
                      const st = a ? accountStatus(a) : "idle"
                      const c =
                        st === "synced"
                          ? "#4ade80"
                          : st === "lagging"
                          ? "#fbbf24"
                          : st === "error"
                          ? "#ef4444"
                          : "#5a6670"
                      return (
                        <div
                          key={m.id}
                          title={`${a?.label || "?"} · ${st} · ${m.size_mode} ${m.size_value}`}
                          style={{
                            height: 10,
                            background: c,
                            opacity: g.is_active ? 1 : 0.45,
                            borderRadius: 1,
                          }}
                        />
                      )
                    })}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </Panel>
  )
}

function EventsFeed({ events }: { events: LiveEvent[] }) {
  return (
    <Panel
      title="LIVE EVENTS"
      subtitle={`${events.length} BUFFERED`}
      action={
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <Dot color="#2dd4bf" pulse size={6} />
          <span
            className="mono"
            style={{ fontSize: 10, color: "var(--fg-dim)", letterSpacing: "0.08em" }}
          >
            STREAMING
          </span>
        </div>
      }
      pad={false}
    >
      <div className="scroll" style={{ overflow: "auto", flex: 1 }}>
        {events.length === 0 && (
          <div
            className="mono"
            style={{
              fontSize: 11,
              color: "var(--fg-mute)",
              padding: 16,
              letterSpacing: "0.08em",
            }}
          >
            WAITING FOR EVENTS · START A GROUP TO SEE ACTIVITY
          </div>
        )}
        {events.map((e, i) => {
          const levelColor =
            e.kind.includes("error") || e.kind.includes("fail")
              ? "var(--crit)"
              : e.kind.includes("close")
              ? "var(--short)"
              : e.kind.includes("open") || e.kind.includes("fill")
              ? "var(--long)"
              : "var(--fg-dim)"
          return (
            <div
              key={i}
              style={{
                padding: "8px 14px",
                borderBottom: "1px solid var(--line)",
                display: "flex",
                gap: 10,
              }}
            >
              <div
                style={{
                  width: 2,
                  background: levelColor,
                  flexShrink: 0,
                  borderRadius: 1,
                }}
              />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  className="mono"
                  style={{
                    fontSize: 9,
                    color: levelColor,
                    letterSpacing: "0.12em",
                    fontWeight: 600,
                    display: "flex",
                    gap: 8,
                  }}
                >
                  <span>{e.kind.toUpperCase()}</span>
                  <span style={{ color: "var(--fg-mute)" }}>· G{e.group_id}</span>
                  <span style={{ color: "var(--fg-mute)", marginLeft: "auto" }}>
                    {new Date(e.ts).toLocaleTimeString("en-US", { hour12: false })}
                  </span>
                </div>
                <div
                  className="mono"
                  style={{
                    fontSize: 11,
                    color: "var(--fg)",
                    marginTop: 3,
                    wordBreak: "break-word",
                  }}
                >
                  {e.message}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </Panel>
  )
}

function GroupsTable({
  groups,
  accounts,
}: {
  groups: Group[]
  accounts: Account[]
}) {
  const qc = useQueryClient()
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
  const accById = new Map(accounts.map((a) => [a.id, a]))

  return (
    <Panel title="GROUPS" subtitle={`${groups.length} TOTAL`} pad={false}>
      <div className="scroll" style={{ overflow: "auto", flex: 1 }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr
              style={{ background: "var(--bg-2)", borderBottom: "1px solid var(--line)" }}
            >
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
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
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
                  <td className="mono" style={{ padding: "0 12px", color: "var(--fg-dim)" }}>
                    {leader?.label} ({leader?.broker})
                  </td>
                  <td
                    className="num"
                    style={{ padding: "0 12px", textAlign: "right" }}
                  >
                    {g.mappings.length}
                  </td>
                  <td style={{ padding: "0 12px" }}>
                    <StatusPill status={groupStatus(g)} />
                  </td>
                  <td style={{ padding: "0 8px", textAlign: "right" }}>
                    {g.is_active ? (
                      <button
                        disabled={stop.isPending}
                        onClick={() => stop.mutate(g.id)}
                        className="mono"
                        style={{
                          fontSize: 10,
                          padding: "4px 10px",
                          color: "var(--warn)",
                          border: "1px solid var(--line-2)",
                          borderRadius: 2,
                          letterSpacing: "0.08em",
                          background: "transparent",
                          cursor: "pointer",
                        }}
                      >
                        STOP
                      </button>
                    ) : (
                      <button
                        disabled={start.isPending}
                        onClick={() => start.mutate(g.id)}
                        className="mono"
                        style={{
                          fontSize: 10,
                          padding: "4px 10px",
                          color: "var(--accent)",
                          border: "1px solid var(--accent-dim)",
                          borderRadius: 2,
                          letterSpacing: "0.08em",
                          background: "var(--accent-bg)",
                          cursor: "pointer",
                        }}
                      >
                        START
                      </button>
                    )}
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
  )
}

export default function Dashboard() {
  const { data: groups = [] } = useQuery({
    queryKey: ["groups"],
    queryFn: api.listGroups,
    refetchInterval: 5000,
  })
  const { data: accounts = [] } = useQuery({
    queryKey: ["accounts"],
    queryFn: api.listAccounts,
    refetchInterval: 10000,
  })
  const events = useEvents(200)

  return (
    <div
      style={{
        flex: 1,
        minHeight: 0,
        display: "grid",
        gridTemplateColumns: "1.6fr 1fr",
        gridTemplateRows: "minmax(280px, auto) 1fr",
        gap: 1,
        background: "var(--line)",
        padding: 1,
      }}
    >
      <div style={{ background: "var(--bg)", minHeight: 0, gridColumn: 1, gridRow: 1 }}>
        <RelationshipsGraph groups={groups} accounts={accounts} />
      </div>
      <div
        style={{
          background: "var(--bg)",
          minHeight: 0,
          gridColumn: 2,
          gridRow: "1 / 3",
        }}
      >
        <EventsFeed events={events} />
      </div>
      <div style={{ background: "var(--bg)", minHeight: 0, gridColumn: 1, gridRow: 2 }}>
        <GroupsTable groups={groups} accounts={accounts} />
      </div>
    </div>
  )
}
