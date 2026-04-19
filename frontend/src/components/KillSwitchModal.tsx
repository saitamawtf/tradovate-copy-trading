import { useEffect, useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api, type Group } from "../lib/api"
import { Dot } from "./atoms"

export function KillSwitchModal({
  open,
  onClose,
  groups,
  onDone,
}: {
  open: boolean
  onClose: () => void
  groups: Group[]
  onDone: (msg: string) => void
}) {
  const qc = useQueryClient()
  const [confirmText, setConfirmText] = useState("")

  useEffect(() => {
    if (!open) setConfirmText("")
  }, [open])

  useEffect(() => {
    if (!open) return
    const h = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
    }
    window.addEventListener("keydown", h)
    return () => window.removeEventListener("keydown", h)
  }, [open, onClose])

  const stopAll = useMutation({
    mutationFn: async () => {
      const active = groups.filter((g) => g.is_active)
      await Promise.allSettled(active.map((g) => api.stopGroup(g.id)))
      return active.length
    },
    onSuccess: (n) => {
      qc.invalidateQueries({ queryKey: ["groups"] })
      qc.invalidateQueries({ queryKey: ["stats"] })
      onDone(`Kill switch executed · ${n} group${n === 1 ? "" : "s"} stopped`)
      onClose()
    },
  })

  if (!open) return null

  const active = groups.filter((g) => g.is_active)
  const totalFollowers = active.reduce((s, g) => s + g.mappings.length, 0)
  const canConfirm = confirmText === "FLATTEN"

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1000,
        background: "rgba(5, 8, 10, 0.82)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 40,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 640,
          maxWidth: "100%",
          background: "var(--bg-1)",
          border: "1px solid var(--crit)",
          borderRadius: 2,
          boxShadow: "0 0 0 1px rgba(239, 68, 68, 0.3), 0 40px 80px rgba(0,0,0,0.5)",
        }}
      >
        <div
          style={{
            padding: "16px 20px",
            borderBottom: "1px solid var(--line)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "linear-gradient(90deg, rgba(239,68,68,0.12), transparent)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Dot color="#ef4444" pulse size={8} />
            <div
              className="mono"
              style={{
                fontSize: 12,
                fontWeight: 700,
                letterSpacing: "0.16em",
                color: "var(--crit)",
              }}
            >
              KILL SWITCH · STOP ALL RUNNING GROUPS
            </div>
          </div>
          <button
            onClick={onClose}
            className="mono"
            style={{
              fontSize: 11,
              color: "var(--fg-dim)",
              background: "transparent",
              border: "none",
              cursor: "pointer",
            }}
          >
            ESC
          </button>
        </div>

        <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 18 }}>
          <div
            style={{
              border: "1px solid var(--line)",
              borderRadius: 2,
              padding: 14,
              background: "var(--bg-2)",
            }}
          >
            <div
              className="mono"
              style={{
                fontSize: 10,
                color: "var(--fg-mute)",
                letterSpacing: "0.12em",
                marginBottom: 10,
              }}
            >
              IMPACT PREVIEW · IF CONFIRMED NOW
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
              <div>
                <div
                  className="mono"
                  style={{ fontSize: 9, color: "var(--fg-mute)", letterSpacing: "0.1em" }}
                >
                  GROUPS
                </div>
                <div className="num" style={{ fontSize: 22, fontWeight: 600, marginTop: 2 }}>
                  {active.length}
                </div>
              </div>
              <div>
                <div
                  className="mono"
                  style={{ fontSize: 9, color: "var(--fg-mute)", letterSpacing: "0.1em" }}
                >
                  FOLLOWERS
                </div>
                <div className="num" style={{ fontSize: 22, fontWeight: 600, marginTop: 2 }}>
                  {totalFollowers}
                </div>
              </div>
              <div>
                <div
                  className="mono"
                  style={{ fontSize: 9, color: "var(--fg-mute)", letterSpacing: "0.1em" }}
                >
                  ACTION
                </div>
                <div
                  className="num"
                  style={{
                    fontSize: 14,
                    fontWeight: 600,
                    marginTop: 6,
                    color: "var(--crit)",
                    letterSpacing: "0.08em",
                  }}
                >
                  STOP COPY
                </div>
              </div>
            </div>

            <div
              style={{
                marginTop: 12,
                borderTop: "1px solid var(--line)",
                paddingTop: 10,
                display: "flex",
                flexDirection: "column",
                gap: 5,
              }}
            >
              {active.length === 0 && (
                <div
                  className="mono"
                  style={{ fontSize: 10, color: "var(--fg-mute)" }}
                >
                  NOTHING IS RUNNING · NOTHING TO STOP
                </div>
              )}
              {active.slice(0, 5).map((g) => (
                <div
                  key={g.id}
                  className="mono"
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: 10,
                    color: "var(--fg-dim)",
                  }}
                >
                  <span>→ STOP {g.name}</span>
                  <span>{g.mappings.length} followers</span>
                </div>
              ))}
              {active.length > 5 && (
                <div className="mono" style={{ fontSize: 10, color: "var(--fg-mute)" }}>
                  ... + {active.length - 5} more
                </div>
              )}
            </div>
          </div>

          <div>
            <div
              className="mono"
              style={{
                fontSize: 10,
                color: "var(--fg-mute)",
                letterSpacing: "0.12em",
                marginBottom: 6,
              }}
            >
              TYPE <span style={{ color: "var(--crit)" }}>FLATTEN</span> TO CONFIRM
            </div>
            <input
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value.toUpperCase())}
              autoFocus
              className="mono"
              style={{
                width: "100%",
                padding: "10px 12px",
                fontSize: 14,
                background: "var(--bg-2)",
                border: `1px solid ${canConfirm ? "var(--crit)" : "var(--line-2)"}`,
                color: "var(--fg)",
                letterSpacing: "0.2em",
                outline: "none",
                boxSizing: "border-box",
              }}
              placeholder="FLATTEN"
            />
          </div>

          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <button
              onClick={onClose}
              className="mono"
              style={{
                padding: "10px 18px",
                fontSize: 11,
                letterSpacing: "0.12em",
                color: "var(--fg-dim)",
                background: "transparent",
                border: "1px solid var(--line)",
                borderRadius: 2,
                cursor: "pointer",
              }}
            >
              CANCEL
            </button>
            <button
              disabled={!canConfirm || active.length === 0 || stopAll.isPending}
              onClick={() => stopAll.mutate()}
              className="mono"
              style={{
                padding: "10px 24px",
                fontSize: 11,
                letterSpacing: "0.12em",
                fontWeight: 700,
                color: "#fff",
                background: canConfirm && active.length > 0 ? "var(--crit)" : "var(--bg-3)",
                opacity: canConfirm && active.length > 0 ? 1 : 0.5,
                cursor: canConfirm && active.length > 0 ? "pointer" : "not-allowed",
                borderRadius: 2,
                border: "none",
              }}
            >
              {stopAll.isPending ? "EXECUTING..." : "EXECUTE STOP"}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
