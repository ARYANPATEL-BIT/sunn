import { useEffect, useRef, useState } from 'react'
import { reducedMotion } from './ui.jsx'

// The night sea: three soft lights drifting through dark water, drawn by one fragment shader.
// Colors are the DESIGN.md tokens; nothing else is drawn.
const FRAGMENT = `
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
uniform vec2 res;
uniform float time;      // seconds of drift (only advances while drawing)
uniform float intensity; // 0..1, per screen

const vec3 ABYSS = vec3(0.0, 10.0, 20.0) / 255.0;
const vec3 LIFT = vec3(2.0, 22.0, 36.0) / 255.0;
const vec3 DEEP = vec3(6.0, 65.0, 90.0) / 255.0;
const vec3 TIDE = vec3(68.0, 165.0, 187.0) / 255.0;
const vec3 MIST = vec3(181.0, 218.0, 226.0) / 255.0;
const float TAU = 6.2831853;

// A soft round light: 1 at its center, gaussian falloff with radius r.
float glow(vec2 p, vec2 center, float r) {
  vec2 d = p - center;
  return exp(-dot(d, d) / (r * r));
}

// A lissajous path: each axis is a sine with its own period (seconds) and phase.
vec2 path(vec2 amp, vec2 period, vec2 phase) {
  return amp * sin(TAU * time / period + phase);
}

float hash(vec2 p) {
  return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

void main() {
  vec2 uv = gl_FragCoord.xy / res;
  float aspect = res.x / res.y;
  vec2 p = (uv - 0.5) * vec2(aspect, 1.0); // centered, 1 unit = screen height, so lights stay round

  // The sea itself: abyss, lifted a little toward the top-left corner.
  vec3 sea = mix(LIFT, ABYSS, clamp(length(uv - vec2(0.0, 1.0)) * 0.9, 0.0, 1.0));

  // Each light sweeps the screen on its own slow path; the periods share no common beat.
  vec2 swing = vec2(0.36 * aspect + 0.12, 0.34);
  vec2 tide = path(swing, vec2(37.0, 29.0), vec2(0.0, 1.3));
  vec2 deep = path(swing * 0.8, vec2(43.0, 31.0), vec2(2.1, 0.4));
  // The bright core leans to one edge of the cyan body, circling it slowly.
  vec2 lean = 0.14 * vec2(cos(TAU * time / 41.0 + 0.7), sin(TAU * time / 26.0));
  vec2 mist = tide + lean;

  vec3 light = DEEP * 0.8 * glow(p, deep, 0.95)
             + TIDE * 1.0 * glow(p, tide, 0.40)
             + MIST * 0.8 * glow(p, mist, 0.16);

  // Soft tone-map: bright overlaps saturate toward mist instead of clipping to white.
  vec3 color = sea + (1.0 - exp(-light * intensity));

  // Film grain, about +-3% luminance, new every frame.
  color += (hash(gl_FragCoord.xy + fract(time * 7.13) * vec2(97.0, 41.0)) - 0.5) * 0.06;
  gl_FragColor = vec4(color, 1.0);
}`

const VERTEX = 'attribute vec2 corner; void main() { gl_Position = vec4(corner, 0.0, 1.0); }'
const FPS = 30
const EASE_MS = 270 // time constant: an intensity change is ~95% done after ~800ms

function createProgram(gl) {
  const program = gl.createProgram()
  for (const [type, source] of [
    [gl.VERTEX_SHADER, VERTEX],
    [gl.FRAGMENT_SHADER, FRAGMENT],
  ]) {
    const shader = gl.createShader(type)
    gl.shaderSource(shader, source)
    gl.compileShader(shader)
    gl.attachShader(program, shader)
  }
  gl.linkProgram(program)
  return gl.getProgramParameter(program, gl.LINK_STATUS) ? program : null
}

// Fixed, full-viewport background. Mounted once at the app root, so it never restarts.
// `veil` (0..0.5) is the abyss layer between the light and the content.
export default function SeaLight({ intensity, veil }) {
  const canvas = useRef(null)
  const target = useRef(intensity)
  const redraw = useRef(null)
  const [webgl, setWebgl] = useState(true)
  target.current = intensity

  useEffect(() => {
    const el = canvas.current
    const gl = el.getContext('webgl', { alpha: false, antialias: false, depth: false, powerPreference: 'low-power' })
    const program = gl && createProgram(gl)
    if (!program) return setWebgl(false)

    gl.useProgram(program)
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer())
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW) // one big triangle
    const corner = gl.getAttribLocation(program, 'corner')
    gl.enableVertexAttribArray(corner)
    gl.vertexAttribPointer(corner, 2, gl.FLOAT, false, 0, 0)
    const uniform = (name) => gl.getUniformLocation(program, name)
    const [res, time, strength] = ['res', 'time', 'intensity'].map(uniform)

    const still = reducedMotion()
    let drift = 140 // seconds into the drift; a nice composition for the frozen frame
    let current = target.current
    let frame = 0
    let last = 0

    function draw() {
      gl.uniform2f(res, el.width, el.height)
      gl.uniform1f(time, drift)
      gl.uniform1f(strength, current)
      gl.drawArrays(gl.TRIANGLES, 0, 3)
    }

    // Half resolution, ignoring devicePixelRatio: the light is soft, CSS scales it up.
    function resize() {
      el.width = Math.max(1, Math.round(innerWidth / 2))
      el.height = Math.max(1, Math.round(innerHeight / 2))
      gl.viewport(0, 0, el.width, el.height)
      if (still) draw()
    }

    function tick(now) {
      frame = requestAnimationFrame(tick)
      const dt = now - last
      if (dt < 1000 / FPS - 2) return
      last = now
      drift += Math.min(dt, 100) / 1000
      current += (target.current - current) * (1 - Math.exp(-dt / EASE_MS))
      draw()
    }

    function play() {
      cancelAnimationFrame(frame)
      if (!document.hidden) frame = requestAnimationFrame((now) => ((last = now), tick(now)))
    }

    // Reduced motion: one frame, redrawn only when the size or the screen's intensity changes.
    redraw.current = still ? () => ((current = target.current), draw()) : null
    resize()
    addEventListener('resize', resize)
    if (!still) {
      play()
      document.addEventListener('visibilitychange', play)
    }
    el.addEventListener('webglcontextlost', () => {
      cancelAnimationFrame(frame)
      document.removeEventListener('visibilitychange', play)
      setWebgl(false)
    })
    return () => {
      cancelAnimationFrame(frame)
      removeEventListener('resize', resize)
      document.removeEventListener('visibilitychange', play)
    }
  }, [])

  useEffect(() => redraw.current?.(), [intensity])

  return (
    <div className="sea" aria-hidden="true">
      {webgl ? <canvas ref={canvas} /> : <div className="sea-fallback" style={{ opacity: intensity }} />}
      <div className="sea-veil" style={{ opacity: veil }} />
    </div>
  )
}
