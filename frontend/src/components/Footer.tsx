import { useEffect, useState } from "react"

function fmtDuration(ms: number): string {
  const s = Math.floor(ms / 1000)
  const hh = String(Math.floor(s / 3600)).padStart(2, "0")
  const mm = String(Math.floor((s % 3600) / 60)).padStart(2, "0")
  const ss = String(s % 60).padStart(2, "0")
  return `${hh}:${mm}:${ss}`
}

export function Footer({
  feedOk,
  feedRate,
  running,
}: {
  feedOk: boolean
  feedRate: number
  running: number
}) {
  const [start] = useState(() => Date.now())
  const [, setTick] = useState(0)
  useEffect(() => {
    const i = setInterval(() => setTick((t) => t + 1), 1000)
    return () => clearInterval(i)
  }, [])

  const session = fmtDuration(Date.now() - start)

  return (
    <footer
      className="mono"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 24,
        padding: "6px 20px",
        background: "var(--bg-1)",
        borderTop: "1px solid var(--line)",
        fontSize: 10,
        color: "var(--fg-mute)",
        flexShrink: 0,
      }}
    >
      <span style={{ letterSpacing: "0.1em" }}>SESSION · {session}</span>
      <span>│</span>
      <span style={{ color: feedOk ? undefined : "var(--crit)" }}>
        FEED · {feedOk ? "OK" : "DOWN"} · {feedRate.toFixed(1)} msg/s
      </span>
      <span>│</span>
      <span>ENGINE · {running} GROUP{running === 1 ? "" : "S"} RUNNING</span>
      <span>│</span>
      <span>RECONCILE · CLEAN</span>
      <span style={{ flex: 1 }} />
      <span>K kill · T tweaks · ESC close</span>
    </footer>
  )
}
