import { useState } from "react"
import { Code2, Cpu, Network } from "lucide-react"
import { ScrambleTextOnHover } from "./ScrambleText"

interface OutputTabsProps {
  netlist: any
  schematicUrl?: string
}

const TABS = [
  { id: "netlist", label: "Validated Netlist", icon: Code2 },
  { id: "schematic", label: "Schematic Viewer", icon: Cpu },
  { id: "graph", label: "Graph Explorer", icon: Network },
] as const

type TabId = typeof TABS[number]["id"]

export function OutputTabs({ netlist }: OutputTabsProps) {
  const [activeTab, setActiveTab] = useState<TabId>("netlist")

  return (
    <div className="flex flex-col border border-border bg-background overflow-hidden">
      {/* Tab Bar */}
      <div className="flex border-b border-border bg-card">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex-1 py-3 px-4 flex items-center justify-center gap-2 font-mono text-xs uppercase tracking-widest transition-all duration-200 border-r border-border last:border-r-0 ${
              activeTab === id
                ? "text-accent bg-accent/5 border-b-0 relative after:absolute after:bottom-0 after:left-0 after:right-0 after:h-px after:bg-accent"
                : "text-muted-foreground hover:text-foreground hover:bg-background"
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">{label}</span>
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="relative min-h-[380px] flex flex-col">
        {activeTab === "netlist" && (
          <div className="flex-1 p-4 overflow-auto">
            <div className="flex items-center gap-2 mb-4">
              <div className="h-px bg-border flex-1" />
              <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">JSON Output</span>
              <div className="h-px bg-border flex-1" />
            </div>
            <pre className="font-mono text-xs text-foreground/80 leading-relaxed">
              <code>{JSON.stringify(netlist, null, 2)}</code>
            </pre>
          </div>
        )}

        {activeTab === "schematic" && (
          <div className="flex-1 flex flex-col items-center justify-center p-8 gap-6">
            <div className="w-full max-w-lg border border-border bg-card relative overflow-hidden group">
              {/* Mock circuit SVG */}
              <svg viewBox="0 0 200 120" className="w-full opacity-25 text-accent" fill="none" stroke="currentColor" strokeWidth="1.5">
                <line x1="10" y1="60" x2="40" y2="60" />
                <rect x="40" y="45" width="30" height="30" />
                <text x="55" y="64" fill="currentColor" fontSize="8" textAnchor="middle" stroke="none">U1</text>
                <line x1="70" y1="60" x2="100" y2="60" />
                <circle cx="107" cy="60" r="7" />
                <line x1="114" y1="60" x2="144" y2="60" />
                <rect x="144" y="50" width="10" height="20" />
                <line x1="154" y1="60" x2="190" y2="60" />
                <line x1="190" y1="60" x2="190" y2="100" />
                <line x1="10" y1="100" x2="190" y2="100" />
                <line x1="10" y1="60" x2="10" y2="100" />
              </svg>
              {/* Hover download overlay */}
              <div className="absolute inset-0 bg-background/80 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300 backdrop-blur-sm">
                <button className="border border-accent text-accent font-mono text-[10px] uppercase tracking-widest px-6 py-3 hover:bg-accent hover:text-accent-foreground transition-colors">
                  <ScrambleTextOnHover text="Download .kicad_sch" />
                </button>
              </div>
            </div>
            <p className="font-mono text-xs text-muted-foreground text-center uppercase tracking-widest max-w-sm">
              Generated KiCad schematic. Hover to download source file.
            </p>
          </div>
        )}

        {activeTab === "graph" && (
          <div className="flex-1 flex flex-col items-center justify-center gap-6">
            {/* Animated node graph placeholder */}
            <svg viewBox="0 0 200 140" className="w-64 opacity-20 text-foreground" fill="none">
              <circle cx="100" cy="70" r="8" fill="currentColor" />
              <circle cx="40" cy="30" r="5" fill="currentColor" />
              <circle cx="160" cy="30" r="5" fill="currentColor" />
              <circle cx="40" cy="110" r="5" fill="currentColor" />
              <circle cx="160" cy="110" r="5" fill="currentColor" />
              <line x1="100" y1="70" x2="40" y2="30" stroke="currentColor" strokeWidth="1" />
              <line x1="100" y1="70" x2="160" y2="30" stroke="currentColor" strokeWidth="1" />
              <line x1="100" y1="70" x2="40" y2="110" stroke="currentColor" strokeWidth="1" />
              <line x1="100" y1="70" x2="160" y2="110" stroke="currentColor" strokeWidth="1" />
            </svg>
            <div className="text-center">
              <p className="font-[family-name:var(--font-bebas)] text-2xl text-foreground tracking-tight">NETWORKX GRAPH</p>
              <p className="font-mono text-xs text-muted-foreground mt-2 uppercase tracking-widest">
                Interactive node graph explorer — coming soon
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
