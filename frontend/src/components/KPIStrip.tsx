import { useQuery } from "@tanstack/react-query"
import type { CSSProperties, ReactNode } from "react"
import { api } from "../lib/api"
import { Sparkline } from "./atoms"

function KPI({
  label,
  value,
  delta,
  sub,
  spark,
  accent,
  wide,
}: {
  label: string
  value: ReactNode
  delta?: string
  sub: ReactNode
  spark?: number[]
  accent?: string
  wide?: boolean
}) {
  const deltaStyle: CSSProperties = delta
    ? {
        fontSize: 12,
        color: delta.startsWith("−") || delta.startsWith("-") ? "var(--short)" : "var(--long)",
      }
    : {}
  return (
    <div
      style={{
        padding: "16px 20px",
        borderRight: "1px solid var(--line)",
        display: "flex",
        flexDirection: "column",
        gap: 6,
        minWidth: wide ? 280 : 200,
        flex: wide ? 1.3 : 1,
      }}
    >
      <div
        className="mono"
        style={{
          fontSize: 10,
          color: "var(--fg-mute)",
          letterSpacing: "0.12em",
          textTransform: "uppercase",
        }}
      >
        {label}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
        <div
          className="num"
          style={{
            fontSize: 26,
            fontWeight: 600,
            letterSpacing: "-0.02em",
            color: accent || "var(--fg)",
          }}
        >
          {value}
        </div>
        {delta && (
          <div className="num" style={deltaStyle}>
            {delta}
          </div>
        )}
      </div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
        }}
      >
        <div className="mono" style={{ fontSize: 10, color: "var(--fg-dim)" }}>
          {sub}
        </div>
        {spark && <Sparkline points={spark} width={80} height={18} color={accent || "var(--accent)"} />}
      </div>
    </div>
  )
}

export function KPIStrip() {
  const { data: stats } = useQuery({
    queryKey: ["stats"],
    queryFn: api.stats,
    refetchInterval: 3000,
  })

  const accountsTotal = stats?.accounts_total ?? 0
  const byStatus = stats?.accounts_by_status ?? {}
  const ok = (byStatus["ok"] ?? 0) + (byStatus["connected"] ?? 0)
  const groupsActive = stats?.groups_active ?? 0
  const groupsTotal = stats?.groups_total ?? 0
  const running = stats?.running_group_ids?.length ?? 0
  const copiesToday = stats?.copies_today ?? 0
  const failsToday = stats?.fails_today ?? 0
  const fillRate = stats?.fill_rate ?? 100

  const fillPoints = [100, 99.2, 99.6, 98.8, 99.4, 99.1, fillRate]

  return (
    <div
      style={{
        display: "flex",
        background: "var(--bg-1)",
        border: "1px solid var(--line)",
        borderLeft: "none",
        borderRight: "none",
      }}
    >
      <KPI
        label={`ACCOUNTS · ${accountsTotal}`}
        value={accountsTotal}
        sub={`${ok} ok · ${accountsTotal - ok} other`}
        wide
      />
      <KPI
        label="ACTIVE GROUPS"
        value={groupsActive}
        sub={`${groupsTotal} total · ${running} running`}
        accent={groupsActive > 0 ? "var(--accent)" : undefined}
      />
      <KPI
        label="COPIES TODAY"
        value={copiesToday.toLocaleString("en-US")}
        delta={failsToday ? `${failsToday} fail` : undefined}
        sub={`${failsToday} failed · since 00:00 ET`}
      />
      <KPI
        label="FILL RATE"
        value={`${fillRate.toFixed(1)}%`}
        sub="target > 98%"
        accent={fillRate >= 98 ? "var(--long)" : fillRate >= 90 ? "var(--warn)" : "var(--crit)"}
        spark={fillPoints}
      />
      <KPI
        label="RUNNING TASKS"
        value={running}
        sub={`${groupsTotal - running} idle · ${groupsActive} armed`}
      />
    </div>
  )
}
