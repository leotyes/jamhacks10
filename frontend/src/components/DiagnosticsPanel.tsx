import { useState } from "react"
import { Cpu, Network, ChevronDown, ChevronUp } from "lucide-react"

interface DiagnosticsPanelProps {
  netlist: any
}

export function DiagnosticsPanel({ netlist }: DiagnosticsPanelProps) {
  const [expandedNet, setExpandedNet] = useState<string | null>(null)

  const components = netlist?.components || []
  const nets = netlist?.nets || []

  return (
    <div className="flex flex-col gap-8">
      <div>
        <span className="font-mono text-xs uppercase tracking-widest text-accent">02 / Diagnostics</span>
        <h2 className="mt-2 font-[family-name:var(--font-bebas)] text-4xl tracking-tight text-foreground">
          RECONCILIATION SUMMARY
        </h2>
      </div>

      <div className="h-px bg-border" />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Components List */}
        <div className="border border-border bg-background flex flex-col h-[480px] overflow-hidden relative">
          {/* Top orange accent line */}
          <div className="absolute top-0 left-0 right-0 h-px bg-accent" />
          
          {/* Header */}
          <div className="border-b border-border px-4 py-3 flex items-center justify-between bg-card">
            <span className="font-mono text-sm uppercase tracking-widest text-accent font-bold">
              Components
            </span>
            <span className="font-mono text-[10px] uppercase text-muted-foreground/45 tracking-widest">
              board.components
            </span>
          </div>

          {/* List Content */}
          <div className="flex-1 overflow-y-auto" data-lenis-prevent>
            <div className="px-4 py-2 bg-accent/5 border-b border-border/40 flex justify-between font-mono text-[11px] text-accent/80">
              <span>TOTAL COMPONENTS</span>
              <span>{components.length}</span>
            </div>
            {components.length === 0 ? (
              <div className="p-4 text-center font-mono text-xs text-muted-foreground">
                No components found.
              </div>
            ) : (
              components.map((c: any) => {
                const pinCount = c.pins ? Object.keys(c.pins).length : 0
                return (
                  <div
                    key={c.id}
                    className="p-4 border-b border-border/30 hover:bg-card/40 transition-colors flex flex-col gap-1.5 font-mono"
                  >
                    <div className="flex justify-between items-start text-sm">
                      <span className="font-bold text-foreground text-sm tracking-wide flex items-center gap-1.5">
                        <Cpu className="w-4 h-4 text-accent/70" />
                        {c.id}
                      </span>
                      <span className="text-[10px] px-2 py-0.5 bg-border text-muted-foreground uppercase font-bold">
                        {pinCount} Pins
                      </span>
                    </div>
                    <div className="text-xs text-muted-foreground truncate ml-5">
                      {c.hardware_model || c.type}
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>

        {/* Nets List */}
        <div className="border border-border bg-background flex flex-col h-[480px] overflow-hidden relative">
          {/* Top orange accent line */}
          <div className="absolute top-0 left-0 right-0 h-px bg-accent" />
          
          {/* Header */}
          <div className="border-b border-border px-4 py-3 flex items-center justify-between bg-card">
            <span className="font-mono text-sm uppercase tracking-widest text-accent font-bold">
              Identified Nets
            </span>
            <span className="font-mono text-[10px] uppercase text-muted-foreground/45 tracking-widest">
              board.nets
            </span>
          </div>

          {/* List Content */}
          <div className="flex-1 overflow-y-auto" data-lenis-prevent>
            <div className="px-4 py-2 bg-accent/5 border-b border-border/40 flex justify-between font-mono text-[11px] text-accent/80">
              <span>TOTAL NETS</span>
              <span>{nets.length}</span>
            </div>
            {nets.length === 0 ? (
              <div className="p-4 text-center font-mono text-xs text-muted-foreground">
                No nets identified.
              </div>
            ) : (
              nets.map((n: any) => {
                const isExpanded = expandedNet === n.name
                const pinCount = n.connections ? n.connections.length : 0
                return (
                  <div
                    key={n.name}
                    className="border-b border-border/30 hover:bg-card/40 transition-colors flex flex-col font-mono"
                  >
                    <button
                      onClick={() => setExpandedNet(isExpanded ? null : n.name)}
                      className="w-full text-left p-4 flex justify-between items-center text-sm"
                    >
                      <div className="flex flex-col gap-0.5 max-w-[70%]">
                        <span className="font-bold text-accent text-sm tracking-wide flex items-center gap-1.5">
                          <Network className="w-4 h-4 text-accent/70" />
                          {n.name}
                        </span>
                        {n.description && (
                          <span className="text-[11px] text-muted-foreground truncate ml-5.5">
                            {n.description}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] px-2 py-0.5 bg-border text-muted-foreground font-bold">
                          {pinCount} Pins
                        </span>
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4 text-muted-foreground/60" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-muted-foreground/60" />
                        )}
                      </div>
                    </button>
                    {isExpanded && (
                      <div className="px-5 pb-4 pt-1.5 bg-background/40 border-t border-border/20 text-xs text-muted-foreground space-y-1.5">
                        {n.connections.map((conn: string, idx: number) => (
                          <div key={idx} className="flex items-center gap-2">
                            <span className="text-accent/60">↳</span>
                            <span className="text-foreground/90 font-mono">{conn}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
