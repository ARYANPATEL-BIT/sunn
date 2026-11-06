import { useEffect, useLayoutEffect, useRef } from 'react'
import { reducedMotion } from './base.jsx'

// The voice shape in the readout (DESIGN.md: Blob). One SVG path: N points round a circle, each
// radius pushed by three sines with its own speeds and phases, closed with Catmull-Rom curves.
// One animation frame loop, alive only while there is something to show.
//
// state: 'rest' | 'listening' | 'thinking' | 'error'. Going to rest from listening or thinking
// springs back to the circle (the result); error snaps there.
// level: a ref whose .current is the mic loudness 0..1 (the recorder's own analyser). Missing = 0.

const N = 9
const R = 56 // the circle's radius in the -100..100 viewBox
const WAVES = Array.from({ length: N }, (_, i) => [
  [1.3 + ((i * 0.37) % 0.9), i * 1.7, 0.55],
  [2.2 + ((i * 0.53) % 1.1), i * 2.9 + 1, 0.3],
  [3.6 + ((i * 0.29) % 1.3), i * 0.8 + 2, 0.15],
])
const ANGLES = Array.from({ length: N }, (_, i) => (i / N) * Math.PI * 2 - Math.PI / 2)

const ATTACK = 0.06 // seconds
const RELEASE = 0.25
const SPRING_K = 180 // stiffness; with this damping the return overshoots a little and settles in ~0.7s
const SPRING_C = 14

function path(time, amp) {
  const pts = ANGLES.map((angle, i) => {
    let n = 0
    for (const [speed, phase, weight] of WAVES[i]) n += weight * Math.sin(time * speed + phase)
    const r = R * (1 + amp * n)
    return [r * Math.cos(angle), r * Math.sin(angle)]
  })
  const f = (v) => v.toFixed(1)
  let d = `M${f(pts[0][0])} ${f(pts[0][1])}`
  for (let i = 0; i < N; i++) {
    const p0 = pts[(i - 1 + N) % N]
    const p1 = pts[i]
    const p2 = pts[(i + 1) % N]
    const p3 = pts[(i + 2) % N]
    d += `C${f(p1[0] + (p2[0] - p0[0]) / 6)} ${f(p1[1] + (p2[1] - p0[1]) / 6)} ${f(p2[0] - (p3[0] - p1[0]) / 6)} ${f(p2[1] - (p3[1] - p1[1]) / 6)} ${f(p2[0])} ${f(p2[1])}`
  }
  return `${d}Z`
}

const CIRCLE = path(0, 0)

export function Blob({ state = 'rest', level, className = '' }) {
  const root = useRef(null)
  const group = useRef(null)
  const shape = useRef(null)
  const sim = useRef({ frame: 0, last: 0, time: 0, level: 0, amp: 0, ampV: 0, scale: 1, scaleV: 0 })
  const stateRef = useRef(state)
  const levelRef = useRef(level)
  levelRef.current = level

  // The glow follows --level only while listening; any other state shows none, at once.
  useLayoutEffect(() => {
    stateRef.current = state
    if (state !== 'listening') root.current?.style.setProperty('--level', '0')
  }, [state])

  useEffect(() => {
    const s = sim.current

    function draw() {
      shape.current?.setAttribute('d', s.amp === 0 ? CIRCLE : path(s.time, s.amp))
      group.current?.setAttribute('transform', `scale(${s.scale.toFixed(4)})`)
    }

    function settle() {
      s.amp = s.ampV = s.scaleV = s.level = 0
      s.scale = 1
      draw()
    }

    function step(now) {
      const dt = Math.min(0.05, s.last ? (now - s.last) / 1000 : 1 / 60)
      s.last = now
      const mode = stateRef.current
      const still = reducedMotion()
      const input = mode === 'listening' ? Math.max(0, Math.min(1, Number(levelRef.current?.current) || 0)) : 0
      s.level += (input - s.level) * (1 - Math.exp(-dt / (input > s.level ? ATTACK : RELEASE)))

      let keepGoing = true
      if (mode === 'error') {
        settle()
        keepGoing = false
      } else if (still) {
        // Reduced motion: the circle never changes shape; only its size follows the voice.
        s.amp = 0
        s.scale = mode === 'listening' ? 1 + 0.25 * s.level : 1
        keepGoing = mode === 'listening'
      } else if (mode === 'listening' || mode === 'thinking') {
        const ampTarget = mode === 'listening' ? 0.08 + 0.3 * s.level : 0.05
        const scaleTarget = mode === 'listening' ? 1 + 0.3 * s.level : 0.94
        const ease = 1 - Math.exp(-dt / 0.09)
        s.amp += (ampTarget - s.amp) * ease
        s.scale += (scaleTarget - s.scale) * ease
        s.ampV = s.scaleV = 0
        s.time += dt * (mode === 'listening' ? 1 + 1.6 * s.level : 0.45)
      } else {
        // The result: a spring back to the resting circle, with a slight overshoot.
        s.scaleV += (-SPRING_K * (s.scale - 1) - SPRING_C * s.scaleV) * dt
        s.scale += s.scaleV * dt
        s.ampV += (-SPRING_K * s.amp - SPRING_C * s.ampV) * dt
        s.amp += s.ampV * dt
        s.time += dt * 0.6
        if (Math.abs(s.scale - 1) < 0.0015 && Math.abs(s.scaleV) < 0.01 && Math.abs(s.amp) < 0.002 && Math.abs(s.ampV) < 0.01) {
          settle()
          keepGoing = false
        }
      }

      if (mode === 'listening') root.current?.style.setProperty('--level', s.level.toFixed(3))
      draw()
      if (keepGoing) {
        s.frame = requestAnimationFrame(step)
      } else {
        s.frame = 0
        s.last = 0
      }
    }

    function start() {
      if (s.frame || document.hidden) return
      const atRest = stateRef.current === 'rest' && s.amp === 0 && s.scale === 1 && s.scaleV === 0
      if (atRest) return
      s.last = 0
      s.frame = requestAnimationFrame(step)
    }

    function stop() {
      cancelAnimationFrame(s.frame)
      s.frame = 0
    }

    const onVisibility = () => (document.hidden ? stop() : start())
    document.addEventListener('visibilitychange', onVisibility)
    s.start = start
    start()
    return () => {
      document.removeEventListener('visibilitychange', onVisibility)
      stop()
    }
  }, [])

  // Every change of state may need the loop (listening, thinking, or the spring home).
  useEffect(() => {
    sim.current.start?.()
  }, [state])

  return (
    <div ref={root} className={`blob ${className}`} data-state={state} aria-hidden="true">
      <div className="blob-glow" />
      <svg className="blob-svg" viewBox="-100 -100 200 200" focusable="false">
        <g ref={group}>
          <path ref={shape} className="blob-shape" d={CIRCLE} />
        </g>
      </svg>
    </div>
  )
}
