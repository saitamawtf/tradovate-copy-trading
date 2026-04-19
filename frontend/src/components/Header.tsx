import { NavLink } from "react-router-dom"
import { Dot } from "./atoms"
import { useClock } from "../lib/useTweaks"

const NAV = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/accounts", label: "Accounts" },
  { to: "/groups", label: "Groups" },
]

export function Header({
  connected,
  onKill,
  onTweaks,
}: {
  connected: boolean
  onKill: () => void
  onTweaks: () => void
}) {
  const now = useClock()
  return (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        gap: 24,
        padding: "14px 24px",
        background: "var(--bg-1)",
        borderBottom: "1px solid var(--line)",
        flexShrink: 0,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <svg width="22" height="22" viewBox="0 0 22 22" style={{ flexShrink: 0 }}>
          <rect x="2" y="2" width="8" height="8" fill="var(--accent)" />
          <rect x="12" y="2" width="8" height="8" fill="none" stroke="var(--accent)" strokeWidth="1.5" />
          <rect x="2" y="12" width="8" height="8" fill="none" stroke="var(--accent)" strokeWidth="1.5" />
          <rect x="12" y="12" width="8" height="8" fill="var(--accent)" />
        </svg>
        <div>
          <div
            className="mono"
            style={{ fontSize: 12, fontWeight: 600, letterSpacing: "0.14em", color: "var(--fg)" }}
          >
            PARALLAX·OPS
          </div>
          <div
            className="mono"
            style={{
              fontSize: 9,
              color: "var(--fg-mute)",
              letterSpacing: "0.16em",
              marginTop: 1,
            }}
          >
            COPIER CONSOLE / v1.0
          </div>
        </div>
      </div>

      <nav style={{ display: "flex", gap: 2, marginLeft: 16 }}>
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.end}
            style={({ isActive }) => ({
              padding: "8px 14px",
              fontSize: 12,
              fontWeight: 500,
              color: isActive ? "var(--fg)" : "var(--fg-dim)",
              background: isActive ? "var(--bg-3)" : "transparent",
              borderRadius: 2,
              textDecoration: "none",
            })}
          >
            {n.label}
          </NavLink>
        ))}
      </nav>

      <div style={{ flex: 1 }} />

      <div
        className="mono"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 16,
          fontSize: 11,
          color: "var(--fg-dim)",
        }}
      >
        <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <Dot color={connected ? "#4ade80" : "#ef4444"} pulse />
          {connected ? "BROKER·LINK OK" : "BROKER·LINK DOWN"}
        </span>
        <span style={{ color: "var(--fg-mute)" }}>│</span>
        <span>CME · {now}</span>
      </div>

      <button
        onClick={onTweaks}
        className="mono"
        style={{
          padding: "9px 12px",
          fontSize: 10,
          letterSpacing: "0.14em",
          background: "transparent",
          border: "1px solid var(--line-2)",
          color: "var(--fg-dim)",
          borderRadius: 2,
          cursor: "pointer",
        }}
      >
        ◎ TWEAKS
      </button>

      <button
        onClick={onKill}
        data-kill
        style={{
          padding: "9px 14px",
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: "0.14em",
          color: "#fff",
          background: "var(--crit)",
          borderRadius: 2,
          display: "flex",
          alignItems: "center",
          gap: 8,
          border: "none",
          cursor: "pointer",
        }}
      >
        <svg width="12" height="12" viewBox="0 0 12 12">
          <path
            d="M6 1v5M3 3.5a4 4 0 1 0 6 0"
            stroke="#fff"
            strokeWidth="1.5"
            fill="none"
            strokeLinecap="round"
          />
        </svg>
        KILL SWITCH
      </button>
    </header>
  )
}
