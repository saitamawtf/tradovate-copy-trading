import React, { useEffect, useMemo, useRef, useState } from "react"
import ReactDOM from "react-dom/client"
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query"
import { BrowserRouter, Route, Routes } from "react-router-dom"
import "./index.css"
import Accounts from "./pages/Accounts"
import Groups from "./pages/Groups"
import Dashboard from "./pages/Dashboard"
import { Header } from "./components/Header"
import { KPIStrip } from "./components/KPIStrip"
import { Footer } from "./components/Footer"
import { KillSwitchModal } from "./components/KillSwitchModal"
import { TweaksPanel } from "./components/TweaksPanel"
import { Dot } from "./components/atoms"
import { useTweaks } from "./lib/useTweaks"
import { useEvents } from "./lib/useEvents"
import { api } from "./lib/api"

const qc = new QueryClient()

function Shell() {
  const [tweaks, setTweaks] = useTweaks()
  const [tweaksOpen, setTweaksOpen] = useState(false)
  const [killOpen, setKillOpen] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const events = useEvents(1)

  const { data: groups = [] } = useQuery({
    queryKey: ["groups"],
    queryFn: api.listGroups,
    refetchInterval: 5000,
  })

  const running = groups.filter((g) => g.is_active).length

  // Feed rate estimation (moving window)
  const feedRef = useRef<number[]>([])
  useEffect(() => {
    if (events.length === 0) return
    feedRef.current = [...feedRef.current, Date.now()].slice(-40)
  }, [events])
  const feedRate = useMemo(() => {
    const now = Date.now()
    const recent = feedRef.current.filter((t) => now - t < 10_000)
    return recent.length / 10
  }, [events])

  const lastEventAt = events[0] ? new Date(events[0].ts).getTime() : 0
  const connected = Date.now() - lastEventAt < 30_000 || running > 0

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT")) return
      if (e.key === "k" || e.key === "K") setKillOpen(true)
      if (e.key === "t" || e.key === "T") setTweaksOpen((v) => !v)
    }
    window.addEventListener("keydown", h)
    return () => window.removeEventListener("keydown", h)
  }, [])

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(null), 3000)
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        background: "var(--bg)",
      }}
    >
      <Header
        connected={connected}
        onKill={() => setKillOpen(true)}
        onTweaks={() => setTweaksOpen((v) => !v)}
      />
      <KPIStrip />

      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/accounts" element={<Accounts />} />
        <Route path="/groups" element={<Groups />} />
      </Routes>

      <Footer feedOk={connected} feedRate={feedRate} running={running} />

      <KillSwitchModal
        open={killOpen}
        onClose={() => setKillOpen(false)}
        groups={groups}
        onDone={showToast}
      />
      <TweaksPanel
        open={tweaksOpen}
        onClose={() => setTweaksOpen(false)}
        tweaks={tweaks}
        setTweaks={setTweaks}
      />

      {toast && (
        <div
          className="mono"
          style={{
            position: "fixed",
            bottom: 40,
            left: "50%",
            transform: "translateX(-50%)",
            background: "var(--bg-1)",
            border: "1px solid var(--accent)",
            padding: "10px 20px",
            borderRadius: 2,
            zIndex: 1100,
            fontSize: 12,
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <Dot color="var(--accent)" pulse size={6} />
          {toast}
        </div>
      )}
    </div>
  )
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Shell />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
