import { useEffect, useRef } from "react"

interface CircuitTextProps {
  text: string
  fontSize?: number
  className?: string
}

type Particle = {
  x: number
  y: number
  tx: number
  ty: number
  vx: number
  vy: number
  delay: number
  active: boolean
  settled: number  // 0→1 settle progress
}

type Connection = {
  a: number
  b: number
  via: "h" | "v" // route direction: horizontal-first or vertical-first
}

const ACCENT = "249,115,22"   // orange
const WHITE  = "248,248,248"

export function CircuitText({ text, fontSize = 130, className }: CircuitTextProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const container = containerRef.current
    const canvas = canvasRef.current
    if (!container || !canvas) return

    let raf: number
    let running = true

    const init = () => {
      if (!running) return
      const ctx = canvas.getContext("2d")!
      const W = container.clientWidth
      const H = Math.round(fontSize * 1.6)
      canvas.width = W
      canvas.height = H

      // ── 1. Rasterise the text onto an offscreen canvas ──
      const off = document.createElement("canvas")
      off.width = W
      off.height = H
      const oc = off.getContext("2d")!
      oc.fillStyle = "#fff"
      oc.font = `${fontSize}px "Bebas Neue", "Arial Black", sans-serif`
      oc.textBaseline = "middle"
      oc.textAlign = "center"
      oc.fillText(text, W / 2, H / 2)

      const { data } = oc.getImageData(0, 0, W, H)
      const GAP = 7  // pixel sampling grid

      const targets: { x: number; y: number }[] = []
      for (let y = 0; y < H; y += GAP) {
        for (let x = 0; x < W; x += GAP) {
          if (data[(y * W + x) * 4 + 3] > 100) targets.push({ x, y })
        }
      }

      if (targets.length === 0) {
        raf = requestAnimationFrame(init) // font might not be loaded yet – retry
        return
      }

      // ── 2. Create particles, staggered left-to-right (circuit "signal flow") ──
      // Sort roughly by x so particles converge like a signal sweep
      targets.sort((a, b) => a.x - b.x + (Math.random() - 0.5) * GAP * 2)

      const particles: Particle[] = targets.map((t, i) => {
        // Spawn from random edge positions
        const edge = Math.floor(Math.random() * 4)
        let sx = 0, sy = 0
        if (edge === 0) { sx = Math.random() * W; sy = 0 }
        else if (edge === 1) { sx = Math.random() * W; sy = H }
        else if (edge === 2) { sx = 0; sy = Math.random() * H }
        else { sx = W; sy = Math.random() * H }

        return {
          x: sx, y: sy,
          tx: t.x, ty: t.y,
          vx: (Math.random() - 0.5) * 3,
          vy: (Math.random() - 0.5) * 3,
          delay: i * 1.8,        // ms between particles
          active: false,
          settled: 0,
        }
      })

      // ── 3. Precompute PCB connections between adjacent letter pixels ──
      const CONN_DIST = GAP * 2.6
      const connections: Connection[] = []
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[j].tx - particles[i].tx
          const dy = particles[j].ty - particles[i].ty
          const d = Math.sqrt(dx * dx + dy * dy)
          if (d < CONN_DIST) {
            // Choose routing: go horizontal first for mostly-horizontal neighbours
            connections.push({ a: i, b: j, via: Math.abs(dx) >= Math.abs(dy) ? "h" : "v" })
          }
        }
      }

      // ── 4. Animation loop ──
      const startTime = performance.now()

      const draw = (now: number) => {
        if (!running) return
        const elapsed = now - startTime
        ctx.clearRect(0, 0, W, H)

        // Update physics
        for (const p of particles) {
          if (elapsed < p.delay) continue
          p.active = true

          const dx = p.tx - p.x
          const dy = p.ty - p.y
          p.vx = (p.vx + dx * 0.075) * 0.80
          p.vy = (p.vy + dy * 0.075) * 0.80
          p.x += p.vx
          p.y += p.vy

          if (Math.hypot(dx, dy) < 1.8 && Math.abs(p.vx) < 0.4) {
            p.settled = Math.min(1, p.settled + 0.035)
          }
        }

        // ── Draw PCB traces between settled neighbours ──
        for (const { a, b, via } of connections) {
          const pa = particles[a]
          const pb = particles[b]
          const prog = Math.min(pa.settled, pb.settled)
          if (prog < 0.05) continue

          const alpha = prog * 0.5
          ctx.lineWidth = 0.9
          ctx.lineJoin = "miter"
          ctx.strokeStyle = `rgba(${ACCENT},${alpha})`

          ctx.beginPath()
          ctx.moveTo(pa.x, pa.y)
          if (via === "h") {
            // horizontal then vertical
            ctx.lineTo(pb.x, pa.y)
            ctx.lineTo(pb.x, pb.y)
          } else {
            // vertical then horizontal
            ctx.lineTo(pa.x, pb.y)
            ctx.lineTo(pb.x, pb.y)
          }
          ctx.stroke()

          // Elbow junction dot
          if (prog > 0.6) {
            ctx.fillStyle = `rgba(${ACCENT},${prog * 0.7})`
            const jx = via === "h" ? pb.x : pa.x
            const jy = via === "h" ? pa.y : pb.y
            ctx.fillRect(jx - 1, jy - 1, 2, 2)
          }
        }

        // ── Draw particles ──
        for (const p of particles) {
          if (!p.active) continue

          if (p.settled > 0.15) {
            // Settled solder pad — white square + orange center pin
            const s = 2.5 + p.settled * 0.5
            ctx.fillStyle = `rgba(${WHITE},${0.55 + p.settled * 0.45})`
            ctx.fillRect(p.x - s / 2, p.y - s / 2, s, s)

            if (p.settled > 0.7) {
              // Small center pin (orange)
              ctx.fillStyle = `rgba(${ACCENT},${(p.settled - 0.7) / 0.3})`
              ctx.fillRect(p.x - 0.8, p.y - 0.8, 1.6, 1.6)
            }
          } else {
            // In-flight spark — glowing orange
            ctx.shadowBlur = 10
            ctx.shadowColor = `rgba(${ACCENT},0.9)`
            ctx.fillStyle = `rgba(${ACCENT},0.95)`
            ctx.fillRect(p.x - 1.5, p.y - 1.5, 3, 3)
            ctx.shadowBlur = 0

            // Trailing motion lines
            if (p.vx !== 0 || p.vy !== 0) {
              const speed = Math.hypot(p.vx, p.vy)
              const trailLen = Math.min(speed * 2.5, 14)
              const nx = p.vx / speed
              const ny = p.vy / speed
              ctx.strokeStyle = `rgba(${ACCENT},0.25)`
              ctx.lineWidth = 1
              ctx.beginPath()
              ctx.moveTo(p.x, p.y)
              ctx.lineTo(p.x - nx * trailLen, p.y - ny * trailLen)
              ctx.stroke()
            }
          }
        }

        raf = requestAnimationFrame(draw)
      }

      raf = requestAnimationFrame(draw)
    }

    // Wait for fonts before sampling
    document.fonts.ready.then(init)

    // Handle resize
    const ro = new ResizeObserver(() => {
      cancelAnimationFrame(raf)
      init()
    })
    ro.observe(container)

    return () => {
      running = false
      cancelAnimationFrame(raf)
      ro.disconnect()
    }
  }, [text, fontSize])

  return (
    <div ref={containerRef} className={className} style={{ width: "100%" }}>
      <canvas ref={canvasRef} style={{ display: "block", width: "100%" }} />
    </div>
  )
}
