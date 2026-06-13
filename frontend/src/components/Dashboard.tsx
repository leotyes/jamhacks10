import { useEffect, useRef } from "react"
import { Cpu, RefreshCcw } from "lucide-react"
import { useReconciliation } from "../hooks/useReconciliation"
import { UploadPanel } from "./UploadPanel"
import { DiagnosticsPanel } from "./DiagnosticsPanel"
import { OutputTabs } from "./OutputTabs"
import { AnimatedNoise } from "./AnimatedNoise"
import { SplitFlapAudioProvider, SplitFlapMuteToggle } from "./SplitFlapText"
import { ScrambleTextOnHover } from "./ScrambleText"
import gsap from "gsap"
import { ScrollTrigger } from "gsap/ScrollTrigger"

import { CircuitText } from "./CircuitText"

gsap.registerPlugin(ScrollTrigger)

export function Dashboard() {
  const {
    iocFile, setIocFile,
    imageFile, setImageFile,
    parts, setParts,
    isProcessing, statusText,
    result, runReconciliation, reset
  } = useReconciliation()

  const headerRef = useRef<HTMLElement>(null)
  const mainRef = useRef<HTMLDivElement>(null)

  // Entrance animation
  useEffect(() => {
    if (!headerRef.current || !mainRef.current) return
    const ctx = gsap.context(() => {
      gsap.from(headerRef.current, {
        y: -20, opacity: 0, duration: 0.8, ease: "power3.out"
      })
      gsap.from(mainRef.current, {
        y: 30, opacity: 0, duration: 1, delay: 0.2, ease: "power3.out"
      })
    })
    return () => ctx.revert()
  }, [])

  return (
    <SplitFlapAudioProvider>
      <div className="min-h-screen bg-background text-foreground relative">
        {/* Animated canvas noise overlay */}
        <AnimatedNoise opacity={0.04} />

        {/* Grid background */}
        <div className="grid-bg fixed inset-0 opacity-20 pointer-events-none" aria-hidden="true" />

        {/* Header / Nav */}
        <header
          ref={headerRef}
          className="relative z-20 flex items-center justify-between border-b border-border px-6 lg:px-10 h-14"
          style={{ background: "oklch(0.08 0 0 / 0.9)", backdropFilter: "blur(12px)" }}
        >
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 border border-accent flex items-center justify-center">
              <Cpu className="w-3.5 h-3.5 text-accent" />
            </div>
            <span className="font-[family-name:var(--font-bebas)] text-xl tracking-widest text-foreground">
              HARDWARE RECON AI
            </span>
          </div>

          <div className="flex items-center gap-6">
            <SplitFlapMuteToggle />
            {result && (
              <button
                onClick={reset}
                className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground hover:text-foreground transition-colors"
              >
                <RefreshCcw className="w-3.5 h-3.5" />
                <ScrambleTextOnHover text="New Session" />
              </button>
            )}
          </div>
        </header>

        {/* Hero title band — only shown before results */}
        {!result && !isProcessing && (
          <div className="relative border-b border-border px-6 lg:px-10 py-12 overflow-hidden flex flex-col items-center justify-center">
            <CircuitText
              text="CIRCUITSYNC"
              fontSize={130}
              className="w-full max-w-4xl"
            />
            <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground mt-4 text-center">
              STM32 .ioc ↔ Breadboard Photo — AI Reconciliation Engine
            </p>
          </div>
        )}

        {/* Main content */}
        <main ref={mainRef} className="relative z-10 max-w-7xl mx-auto px-6 lg:px-10 py-10">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">

            {/* Left Panel — always visible */}
            <div className="lg:col-span-4">
              <UploadPanel
                iocFile={iocFile} setIocFile={setIocFile}
                imageFile={imageFile} setImageFile={setImageFile}
                parts={parts} setParts={setParts}
                onRun={runReconciliation}
                isProcessing={isProcessing}
                statusText={statusText}
              />
            </div>

            {/* Right Panel — results or placeholder */}
            <div className="lg:col-span-8">
              {result ? (
                <div className="flex flex-col gap-10">
                  <DiagnosticsPanel confidence={result.confidence} log={result.log} />

                  <div>
                    <div className="h-px bg-border mb-8" />
                    <span className="font-mono text-[10px] uppercase tracking-[0.3em] text-accent block mb-2">03 / Output</span>
                    <h2 className="font-[family-name:var(--font-bebas)] text-4xl tracking-tight text-foreground mb-6">
                      GENERATED ARTIFACTS
                    </h2>
                    <OutputTabs netlist={result.netlist} schematicUrl={result.schematicUrl} />
                  </div>
                </div>
              ) : (
                <div className="flex flex-col h-full min-h-[500px] border border-dashed border-border/40 items-center justify-center gap-6">
                  {/* Animated scan line */}
                  {isProcessing ? (
                    <div className="text-center space-y-6 px-8">
                      <div className="relative w-24 h-24 mx-auto border border-accent/30">
                        <div className="absolute inset-0 border border-accent animate-ping opacity-20" />
                        <div className="absolute inset-0 flex items-center justify-center">
                          <Cpu className="w-8 h-8 text-accent animate-pulse" />
                        </div>
                      </div>
                      <div>
                        <p className="font-[family-name:var(--font-bebas)] text-2xl text-foreground tracking-tight">
                          PROCESSING
                        </p>
                        <p className="font-mono text-xs uppercase tracking-widest text-accent mt-2">
                          {statusText}
                        </p>
                      </div>
                      {/* Animated progress bar */}
                      <div className="w-48 h-px bg-border mx-auto overflow-hidden">
                        <div className="h-full bg-accent animate-[scan_2s_ease-in-out_infinite]" style={{
                          animation: "scan 2s ease-in-out infinite",
                        }} />
                      </div>
                    </div>
                  ) : (
                    <div className="text-center space-y-4 px-8 opacity-60">
                      <div className="w-16 h-16 border border-border mx-auto flex items-center justify-center">
                        <Cpu className="w-7 h-7 text-muted-foreground" />
                      </div>
                      <div>
                        <p className="font-[family-name:var(--font-bebas)] text-3xl text-foreground tracking-tight">
                          AWAITING INPUT
                        </p>
                        <p className="font-mono text-xs text-muted-foreground mt-2 uppercase tracking-widest max-w-xs mx-auto leading-relaxed">
                          Upload your .ioc file, breadboard photo, and component list to begin
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </main>

        {/* Bottom status bar */}
        <footer className="relative z-10 border-t border-border/30 px-6 lg:px-10 py-3 flex items-center justify-between mt-10">
          <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground/60">
            Hardware Recon AI — JamHacks 10
          </span>
          <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground/60">
            {result ? "● ANALYSIS COMPLETE" : isProcessing ? "● RUNNING" : "○ IDLE"}
          </span>
        </footer>

        <style>{`
          @keyframes scan {
            0% { transform: translateX(-100%); width: 30%; }
            50% { width: 60%; }
            100% { transform: translateX(400%); width: 30%; }
          }
        `}</style>
      </div>
    </SplitFlapAudioProvider>
  )
}
