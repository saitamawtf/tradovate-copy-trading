import type { ReactNode } from "react"
import type { AccentId, Density, Theme, Tweaks } from "../lib/useTweaks"

const ACCENTS: { id: AccentId; hex: string }[] = [
  { id: "teal", hex: "#2dd4bf" },
  { id: "violet", hex: "#a78bfa" },
  { id: "amber", hex: "#f59e0b" },
  { id: "mint", hex: "#34d399" },
  { id: "rose", hex: "#fb7185" },
]

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 14 }}>
      <div
        className="mono"
        style={{ fontSize: 10, color: "var(--fg-mute)", letterSpacing: "0.12em" }}
      >
        {label}
      </div>
      {children}
    </div>
  )
}

function Seg<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { value: T; label: string }[]
  value: T
  onChange: (v: T) => void
}) {
  return (
    <div
      style={{
        display: "flex",
        gap: 4,
        background: "var(--bg-2)",
        padding: 3,
        borderRadius: 2,
        border: "1px solid var(--line)",
      }}
    >
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className="mono"
          style={{
            flex: 1,
            padding: "6px 8px",
            fontSize: 10,
            letterSpacing: "0.1em",
            background: value === o.value ? "var(--bg-3)" : "transparent",
            color: value === o.value ? "var(--fg)" : "var(--fg-mute)",
            borderRadius: 1,
            border: "none",
            cursor: "pointer",
          }}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

export function TweaksPanel({
  open,
  onClose,
  tweaks,
  setTweaks,
}: {
  open: boolean
  onClose: () => void
  tweaks: Tweaks
  setTweaks: (t: Tweaks) => void
}) {
  if (!open) return null
  const set = <K extends keyof Tweaks>(k: K, v: Tweaks[K]) => setTweaks({ ...tweaks, [k]: v })

  return (
    <div
      style={{
        position: "fixed",
        bottom: 24,
        right: 24,
        zIndex: 900,
        width: 280,
        background: "var(--bg-1)",
        border: "1px solid var(--line-2)",
        borderRadius: 2,
        boxShadow: "0 20px 40px rgba(0,0,0,0.5)",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 14px",
          borderBottom: "1px solid var(--line)",
        }}
      >
        <div
          className="mono"
          style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.16em" }}
        >
          TWEAKS
        </div>
        <button
          onClick={onClose}
          className="mono"
          style={{
            fontSize: 14,
            color: "var(--fg-mute)",
            background: "transparent",
            border: "none",
            cursor: "pointer",
          }}
        >
          ×
        </button>
      </div>
      <div style={{ padding: 14 }}>
        <Row label="THEME">
          <Seg<Theme>
            value={tweaks.theme}
            onChange={(v) => set("theme", v)}
            options={[
              { value: "dark", label: "DARK" },
              { value: "light", label: "LIGHT" },
            ]}
          />
        </Row>
        <Row label="ACCENT">
          <div style={{ display: "flex", gap: 6 }}>
            {ACCENTS.map((c) => (
              <button
                key={c.id}
                onClick={() => set("accent", c.id)}
                style={{
                  width: 28,
                  height: 28,
                  background: c.hex,
                  borderRadius: 2,
                  border:
                    tweaks.accent === c.id ? "2px solid var(--fg)" : "2px solid transparent",
                  outline: "1px solid var(--line)",
                  cursor: "pointer",
                }}
              />
            ))}
          </div>
        </Row>
        <Row label="DENSITY">
          <Seg<Density>
            value={tweaks.density}
            onChange={(v) => set("density", v)}
            options={[
              { value: "spacious", label: "WIDE" },
              { value: "balanced", label: "BAL" },
              { value: "dense", label: "DENSE" },
            ]}
          />
        </Row>
        <Row label="PRIVACY · HIDE P&L">
          <Seg<"on" | "off">
            value={tweaks.privacy ? "on" : "off"}
            onChange={(v) => set("privacy", v === "on")}
            options={[
              { value: "off", label: "OFF" },
              { value: "on", label: "ON" },
            ]}
          />
        </Row>
      </div>
    </div>
  )
}
