import { Activity, AlertTriangle, ShieldCheck } from "lucide-react"

interface DiagnosticsPanelProps {
  confidence: number
  log: string
}

export function DiagnosticsPanel({ confidence, log }: DiagnosticsPanelProps) {
  const percentage = Math.round(confidence * 100)

  let Icon = ShieldCheck
  let accentClass = "text-accent"
  if (percentage < 80) { Icon = AlertTriangle; accentClass = "text-yellow-400" }
  if (percentage < 60) { Icon = Activity; accentClass = "text-red-400" }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <span className="font-mono text-xs uppercase tracking-widest text-accent">02 / Diagnostics</span>
        <h2 className="mt-2 font-[family-name:var(--font-bebas)] text-4xl tracking-tight text-foreground">
          AI ANALYSIS
        </h2>
      </div>

      <div className="h-px bg-border" />

      <div className="grid grid-cols-3 gap-6">
        {/* Confidence Score */}
        <div className="col-span-1 border border-border bg-card p-6 flex flex-col items-center gap-4 relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-px bg-accent/60" />
          <div className="flex items-center gap-2">
            <Icon className={`w-4 h-4 ${accentClass}`} />
            <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">Confidence</span>
          </div>
          <div className="relative w-24 h-24">
            <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
              <circle cx="50" cy="50" r="42" stroke="currentColor" strokeWidth="6" fill="transparent" className="text-border" />
              <circle
                cx="50" cy="50" r="42"
                stroke="currentColor" strokeWidth="6" fill="transparent"
                strokeDasharray="263.9"
                strokeDashoffset={263.9 - (263.9 * percentage) / 100}
                className={`${accentClass} transition-all duration-1000 ease-out`}
                strokeLinecap="square"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className={`font-[family-name:var(--font-bebas)] text-3xl ${accentClass}`}>{percentage}%</span>
            </div>
          </div>
        </div>

        {/* AI Log Terminal */}
        <div className="col-span-2 border border-border bg-background flex flex-col overflow-hidden">
          <div className="border-b border-border px-4 py-2 flex items-center justify-between bg-card">
            <div className="flex gap-1.5">
              <div className="w-2 h-2 bg-border" />
              <div className="w-2 h-2 bg-border" />
              <div className="w-2 h-2 bg-accent" />
            </div>
            <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">system.log</span>
          </div>
          <div className="p-4 overflow-y-auto max-h-44 flex-1 relative">
            {log.split("\n").map((line, i) => (
              <div key={i} className="flex gap-3 mb-1.5">
                <span className="font-mono text-xs text-muted-foreground/60 select-none w-5 shrink-0 text-right">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="font-mono text-xs text-foreground/80 leading-relaxed">{line}</span>
              </div>
            ))}
            <div className="absolute bottom-0 left-0 right-0 h-6 bg-gradient-to-t from-background to-transparent pointer-events-none" />
          </div>
        </div>
      </div>
    </div>
  )
}
