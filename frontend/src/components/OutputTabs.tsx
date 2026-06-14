import { useState } from "react"
import { Code2, Cpu, ChevronDown, ChevronUp } from "lucide-react"
import { ScrambleTextOnHover } from "./ScrambleText"

interface OutputTabsProps {
  netlist: any
  schematicUrl?: string
}

const TABS = [
  { id: "netlist", label: "Validated Netlist", icon: Code2 },
  { id: "schematic", label: "Schematic Viewer", icon: Cpu },
] as const

type TabId = typeof TABS[number]["id"]

const PREVIEW_LINES = 12

function NetlistPanel({ netlist }: { netlist: any }) {
  const [expanded, setExpanded] = useState(false)
  const fullJson = JSON.stringify(netlist, null, 2)
  const lines = fullJson.split("\n")
  const previewJson = lines.slice(0, PREVIEW_LINES).join("\n")

  return (
    <div className="flex-1 p-4" data-lenis-prevent>
      <div className="flex items-center gap-2 mb-4">
        <div className="h-px bg-border flex-1" />
        <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">JSON Output</span>
        <div className="h-px bg-border flex-1" />
      </div>

      <div className="relative">
        <pre className="font-mono text-xs text-foreground/80 leading-relaxed overflow-x-auto">
          <code>{expanded ? fullJson : previewJson}</code>
        </pre>

        {/* Fade gradient when collapsed */}
        {!expanded && (
          <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-background to-transparent pointer-events-none" />
        )}
      </div>

      {/* Expand / collapse button */}
      <button
        onClick={() => setExpanded(v => !v)}
        className="mt-3 w-full flex items-center justify-center gap-2 py-2.5 border border-border/60 hover:border-accent/60 text-muted-foreground hover:text-accent font-mono text-[10px] uppercase tracking-widest transition-all duration-200 bg-card/40 hover:bg-accent/5"
      >
        {expanded ? (
          <>
            <ChevronUp className="w-3.5 h-3.5" />
            Collapse JSON
          </>
        ) : (
          <>
            <ChevronDown className="w-3.5 h-3.5" />
            Show Full Netlist ({lines.length} lines)
          </>
        )}
      </button>
    </div>
  )
}

export function OutputTabs({ netlist, schematicUrl }: OutputTabsProps) {
  const [activeTab, setActiveTab] = useState<TabId>("netlist")

  return (
    <div className="flex flex-col border border-border bg-background overflow-hidden">
      {/* Tab Bar */}
      <div className="flex border-b border-border bg-card">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex-1 py-3 px-4 flex items-center justify-center gap-2 font-mono text-xs uppercase tracking-widest transition-all duration-200 border-r border-border last:border-r-0 ${activeTab === id
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
          <NetlistPanel netlist={netlist} />
        )}

        {activeTab === "schematic" && (
          <div className="flex-1 flex flex-col items-center justify-center p-12 gap-4">
            <div className="w-16 h-16 border border-border flex items-center justify-center bg-card mb-2">
              <Cpu className="w-8 h-8 text-accent" />
            </div>
            
            {schematicUrl ? (
              <a
                href={schematicUrl}
                download="circuit.net"
                className="border border-accent text-accent font-mono text-[10px] uppercase tracking-widest px-8 py-3 hover:bg-accent hover:text-accent-foreground transition-all duration-200 text-center shadow-lg hover:shadow-accent/20"
              >
                <ScrambleTextOnHover text="Download KiCad .net File" />
              </a>
            ) : (
              <button className="border border-border text-muted-foreground font-mono text-[10px] uppercase tracking-widest px-8 py-3 cursor-not-allowed">
                No Netlist Generated
              </button>
            )}

            <p className="font-mono text-xs text-muted-foreground text-center uppercase tracking-widest max-w-sm mt-1">
              Generated KiCad Netlist. Ready for schematic routing.
            </p>
          </div>
        )}


      </div>
    </div>
  )
}
