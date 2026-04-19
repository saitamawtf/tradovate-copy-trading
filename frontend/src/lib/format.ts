export function fmtUSD(
  n: number,
  opts: { privacy?: boolean; sign?: boolean; compact?: boolean } = {},
): string {
  const { privacy = false, sign = false, compact = false } = opts
  if (privacy) return "$ ● ● ●"
  const abs = Math.abs(n)
  let body: string
  if (compact && abs >= 1_000_000) body = (abs / 1_000_000).toFixed(2) + "M"
  else if (compact && abs >= 1_000) body = (abs / 1_000).toFixed(1) + "k"
  else body = abs.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 })
  const s = n < 0 ? "−" : sign ? "+" : ""
  return s + "$" + body
}

export function fmtPct(n: number, opts: { sign?: boolean; digits?: number } = {}): string {
  const { sign = true, digits = 1 } = opts
  const s = n > 0 && sign ? "+" : ""
  return s + n.toFixed(digits) + "%"
}

export const MASTER_COLORS = [
  "#2dd4bf",
  "#a78bfa",
  "#f59e0b",
  "#fb7185",
  "#34d399",
  "#60a5fa",
  "#f472b6",
  "#facc15",
]

export function colorForGroup(groupId: number): string {
  return MASTER_COLORS[(groupId - 1) % MASTER_COLORS.length]
}
