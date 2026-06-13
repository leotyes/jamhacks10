import { useEffect, useState, useRef, useCallback } from "react"
import gsap from "gsap"

interface ScrambleTextProps {
  text: string
  className?: string
  delayMs?: number
  duration?: number
}

interface ScrambleTextOnHoverProps {
  text: string
  className?: string
  duration?: number
  as?: "span" | "button" | "div"
  onClick?: () => void
}

const GLYPHS = "!@#$%^&*()_+-=<>?/\\[]{}Xx"

function runScrambleAnimation(
  text: string,
  duration: number,
  setDisplayText: (text: string) => void,
  onComplete?: () => void,
): gsap.core.Tween {
  const lockedIndices = new Set<number>()
  const finalChars = text.split("")
  const totalChars = finalChars.length
  const scrambleObj = { progress: 0 }

  return gsap.to(scrambleObj, {
    progress: 1,
    duration,
    ease: "power2.out",
    onUpdate: () => {
      const numLocked = Math.floor(scrambleObj.progress * totalChars)
      for (let i = 0; i < numLocked; i++) lockedIndices.add(i)
      const newDisplay = finalChars
        .map((char, i) => (lockedIndices.has(i) ? char : GLYPHS[Math.floor(Math.random() * GLYPHS.length)]))
        .join("")
      setDisplayText(newDisplay)
    },
    onComplete: () => {
      setDisplayText(text)
      onComplete?.()
    },
  })
}

export function ScrambleText({ text, className, delayMs = 0, duration = 0.9 }: ScrambleTextProps) {
  const [displayText, setDisplayText] = useState(text)
  const [hasAnimated, setHasAnimated] = useState(false)
  const animationRef = useRef<gsap.core.Tween | null>(null)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (hasAnimated || !text) return
    const scrambledStart = text.split("").map(() => GLYPHS[Math.floor(Math.random() * GLYPHS.length)]).join("")
    setDisplayText(scrambledStart)
    timeoutRef.current = setTimeout(() => {
      animationRef.current = runScrambleAnimation(text, duration, setDisplayText, () => setHasAnimated(true))
    }, delayMs)
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
      if (animationRef.current) animationRef.current.kill()
    }
  }, [])

  useEffect(() => {
    if (hasAnimated && displayText !== text) setDisplayText(text)
  }, [text, hasAnimated, displayText])

  return <span className={className}>{displayText || text}</span>
}

export function ScrambleTextOnHover({ text, className, duration = 0.4, as: Component = "span", onClick }: ScrambleTextOnHoverProps) {
  const [displayText, setDisplayText] = useState(text)
  const isAnimating = useRef(false)
  const tweenRef = useRef<gsap.core.Tween | null>(null)

  const handleMouseEnter = useCallback(() => {
    if (isAnimating.current) return
    isAnimating.current = true
    if (tweenRef.current) tweenRef.current.kill()
    const scrambledStart = text.split("").map(() => GLYPHS[Math.floor(Math.random() * GLYPHS.length)]).join("")
    setDisplayText(scrambledStart)
    tweenRef.current = runScrambleAnimation(text, duration, setDisplayText, () => { isAnimating.current = false })
  }, [text, duration])

  useEffect(() => {
    if (!isAnimating.current) setDisplayText(text)
  }, [text])

  return <Component className={className} onMouseEnter={handleMouseEnter} onClick={onClick}>{displayText}</Component>
}
