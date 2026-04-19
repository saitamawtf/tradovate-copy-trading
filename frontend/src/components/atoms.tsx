import type { CSSProperties, ReactNode } from "react"

export function Dot({
  color,
  pulse = false,
  size = 7,
}: {
  color: string
  pulse?: boolean
  size?: number
}) {
  return (
    <span
      style={{
        display: "inline-block",
        width: size,
        height: size,
        borderRadius: "50%",
        background: color,
        boxShadow: `0 0 ${size}px ${color}`,
        animation: pulse ? "pulse-dot 1.8s ease-in-out infinite" : "none",
        flexShrink: 0,
      }}
    />
  )
}

export type PillStatus = "synced" | "lagging" | "error" | "paused" | "live" | "idle"

const PILL_MAP: Record<PillStatus, { color: string; label: string }> = {
  synced: { color: "#4ade80", label: "synced" },
  lagging: { color: "#fbbf24", label: "lagging" },
  error: { color: "#ef4444", label: "error" },
  paused: { color: "#8b97a3", label: "paused" },
  live: { color: "#2dd4bf", label: "live" },
  idle: { color: "#5a6670", label: "idle" },
}

export function StatusPill({ status }: { status: PillStatus }) {
  const s = PILL_MAP[status] || PILL_MAP.idle
  return (
    <span
      className="mono"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        fontSize: 10,
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        color: s.color,
      }}
    >
      <Dot color={s.color} pulse={status === "live" || status === "synced"} size={6} />
      {s.label}
    </span>
  )
}

export function Panel({
  title,
  subtitle,
  action,
  children,
  style,
  pad = true,
  id,
}: {
  title: ReactNode
  subtitle?: ReactNode
  action?: ReactNode
  children: ReactNode
  style?: CSSProperties
  pad?: boolean
  id?: string
}) {
  return (
    <section
      id={id}
      style={{
        background: "var(--bg-1)",
        border: "1px solid var(--line)",
        borderRadius: 2,
        display: "flex",
        flexDirection: "column",
        minHeight: 0,
        height: "100%",
        ...style,
      }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          padding: "14px 16px 12px",
          borderBottom: "1px solid var(--line)",
          flexShrink: 0,
          gap: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline", gap: 12, minWidth: 0 }}>
          <h3
            className="mono"
            style={{
              margin: 0,
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              color: "var(--fg)",
              whiteSpace: "nowrap",
            }}
          >
            {title}
          </h3>
          {subtitle && (
            <span
              className="mono"
              style={{
                fontSize: 10,
                color: "var(--fg-mute)",
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {subtitle}
            </span>
          )}
        </div>
        {action}
      </header>
      <div
        style={{
          padding: pad ? "var(--density-pad) 16px 16px" : 0,
          flex: 1,
          minHeight: 0,
          display: "flex",
          flexDirection: "column",
        }}
      >
        {children}
      </div>
    </section>
  )
}

export function Sparkline({
  points,
  color = "var(--accent)",
  width = 120,
  height = 28,
  fill = true,
}: {
  points: number[]
  color?: string
  width?: number
  height?: number
  fill?: boolean
}) {
  if (points.length < 2) {
    return (
      <svg width={width} height={height}>
        <line
          x1="0"
          x2={width}
          y1={height / 2}
          y2={height / 2}
          stroke="var(--line-2)"
          strokeDasharray="2 3"
          strokeWidth="1"
        />
      </svg>
    )
  }
  const min = Math.min(...points)
  const max = Math.max(...points)
  const range = max - min || 1
  const step = width / (points.length - 1)
  const coords = points.map((p, i) => [i * step, height - ((p - min) / range) * height] as const)
  const d = coords.map((c, i) => (i === 0 ? "M" : "L") + c[0].toFixed(1) + " " + c[1].toFixed(1)).join(" ")
  const fillD = d + ` L ${width} ${height} L 0 ${height} Z`
  const gradId = "g" + Math.floor(Math.random() * 100000)
  return (
    <svg width={width} height={height} style={{ display: "block", overflow: "visible" }}>
      {fill && (
        <>
          <defs>
            <linearGradient id={gradId} x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity="0.28" />
              <stop offset="100%" stopColor={color} stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d={fillD} fill={`url(#${gradId})`} />
        </>
      )}
      <path d={d} fill="none" stroke={color} strokeWidth="1.2" />
    </svg>
  )
}

export function Bar({
  value,
  max = 100,
  color,
  warnAt = 70,
  critAt = 90,
  height = 4,
}: {
  value: number
  max?: number
  color?: string
  warnAt?: number
  critAt?: number
  height?: number
}) {
  const pct = Math.min(100, (value / max) * 100)
  let c = color || "var(--accent)"
  if (!color) {
    if (pct >= critAt) c = "var(--crit)"
    else if (pct >= warnAt) c = "var(--warn)"
  }
  return (
    <div
      style={{
        width: "100%",
        height,
        background: "var(--bg-3)",
        borderRadius: 1,
        overflow: "hidden",
      }}
    >
      <div style={{ width: pct + "%", height: "100%", background: c, transition: "width 0.4s ease" }} />
    </div>
  )
}

export function KBD({ children }: { children: ReactNode }) {
  return (
    <kbd
      className="mono"
      style={{
        display: "inline-block",
        padding: "2px 6px",
        fontSize: 10,
        border: "1px solid var(--line-2)",
        borderRadius: 2,
        background: "var(--chip)",
        color: "var(--fg-dim)",
        marginLeft: 4,
      }}
    >
      {children}
    </kbd>
  )
}
