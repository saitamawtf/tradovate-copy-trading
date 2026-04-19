import { useEffect, useState } from "react"

export type AccentId = "teal" | "violet" | "amber" | "mint" | "rose"
export type Density = "spacious" | "balanced" | "dense"
export type Theme = "dark" | "light"

export type Tweaks = {
  theme: Theme
  accent: AccentId
  density: Density
  privacy: boolean
}

const DEFAULT: Tweaks = { theme: "dark", accent: "teal", density: "balanced", privacy: false }
const KEY = "copier.tweaks.v1"

export const ACCENT_MAP: Record<AccentId, { accent: string; accentDim: string; accentBg: string }> = {
  teal: { accent: "#2dd4bf", accentDim: "#0f766e", accentBg: "rgba(45, 212, 191, 0.08)" },
  violet: { accent: "#a78bfa", accentDim: "#6d28d9", accentBg: "rgba(167, 139, 250, 0.1)" },
  amber: { accent: "#f59e0b", accentDim: "#b45309", accentBg: "rgba(245, 158, 11, 0.1)" },
  mint: { accent: "#34d399", accentDim: "#047857", accentBg: "rgba(52, 211, 153, 0.1)" },
  rose: { accent: "#fb7185", accentDim: "#be123c", accentBg: "rgba(251, 113, 133, 0.1)" },
}

function load(): Tweaks {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return DEFAULT
    return { ...DEFAULT, ...JSON.parse(raw) }
  } catch {
    return DEFAULT
  }
}

export function useTweaks() {
  const [tweaks, setTweaks] = useState<Tweaks>(load)

  useEffect(() => {
    const root = document.documentElement
    root.setAttribute("data-theme", tweaks.theme)
    root.setAttribute("data-density", tweaks.density)
    const a = ACCENT_MAP[tweaks.accent] || ACCENT_MAP.teal
    root.style.setProperty("--accent", a.accent)
    root.style.setProperty("--accent-dim", a.accentDim)
    root.style.setProperty("--accent-bg", a.accentBg)
    localStorage.setItem(KEY, JSON.stringify(tweaks))
  }, [tweaks])

  return [tweaks, setTweaks] as const
}

export function useClock() {
  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const i = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(i)
  }, [])
  return now.toLocaleTimeString("en-US", { hour12: false }) + " ET"
}
