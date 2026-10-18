import { useEffect, useRef, useState } from 'react'
import { reducedMotion } from './ui.jsx'

// Aurora dusk, behind every page: aurora colors drift through the upper sky, a dusk glow rises
// from the bottom, violet bridges the two. One fragment shader; colors are the DESIGN.md tokens.
const FRAGMENT = `
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
uniform vec2 res;
uniform float time;      // seconds of drift (only advances while drawing)
uniform float intensity; // 0..1, per screen

const vec3 SKY = vec3(7.0, 7.0, 26.0) / 255.0;        // --sky: the base
const vec3 TEAL = vec3(15.0, 94.0, 115.0) / 255.0;    // --teal
const vec3 VIOLET = vec3(91.0, 63.0, 209.0) / 255.0;  // --violet
const vec3 MAGENTA = vec3(194.0, 48.0, 107.0) / 255.0; // --magenta
const vec3 SAFFRON = vec3(243.0, 154.0, 43.0) / 255.0; // --saffron
const vec3 LUMA = vec3(0.2126, 0.7152, 0.0722);
// The brightest the sky may get (relative luminance). Mist text (DESIGN.md) keeps 4.5:1 up to
// 0.079; this leaves room for the grain on top.
const float CEILING = 0.06;
const float TAU = 6.2831853;

float hash(vec2 p) {
  return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

// Smooth value noise, 0..1.
float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x),
             mix(hash(i + vec2(0.0, 1.0)), hash(i + 1.0), f.x), f.y);
}

// A soft color area: 1 at its center, gaussian falloff, wider than tall (radius r).
float field(vec2 p, vec2 center, vec2 r) {
  vec2 d = (p - center) / r;
  return exp(-dot(d, d));
}

// A lissajous path: each axis is a sine with its own period (seconds) and phase.
vec2 path(vec2 amp, vec2 period, vec2 phase) {
  return amp * sin(TAU * time / period + phase);
}

void main() {
  vec2 uv = gl_FragCoord.xy / res;
  float aspect = res.x / res.y;
  vec2 p = (uv - 0.5) * vec2(aspect, 1.0); // centered, 1 unit = screen height; y is up

  // Domain warp: slow, low-frequency noise bends the space before the fields are sampled,
  // so the edges between colors swirl like aurora curtains.
  vec2 warp = vec2(noise(p * 1.4 + vec2(0.0, time * 0.031)),
                   noise(p * 1.4 + vec2(5.2, -time * 0.023))) - 0.5;
  vec2 q = p + warp * 0.35;

  // Each field drifts on its own path (20-40s periods) and stays in its band:
  // cool on top, warm at the bottom, violet in between.
  float w = 0.5 * aspect;
  vec2 teal = vec2(0.0, 0.34) + path(vec2(w * 0.5, 0.05), vec2(37.0, 29.0), vec2(0.0, 1.1));
  vec2 violet = vec2(0.0, 0.12) + path(vec2(w * 0.6, 0.06), vec2(31.0, 23.0), vec2(2.0, 0.3));
  vec2 magenta = vec2(0.0, -0.24) + path(vec2(w * 0.55, 0.04), vec2(27.0, 34.0), vec2(4.1, 2.2));
  vec2 saffron = vec2(0.0, -0.6) + path(vec2(w * 0.3, 0.04), vec2(39.0, 21.0), vec2(1.3, 0.0));

  vec3 light = TEAL * 1.3 * field(q, teal, vec2(w + 0.35, 0.34))
             + VIOLET * 0.6 * field(q, violet, vec2(w * 0.8 + 0.2, 0.26))
             + MAGENTA * 0.55 * field(q, magenta, vec2(w * 0.6 + 0.2, 0.22))
             + SAFFRON * 1.1 * field(q, saffron, vec2(w * 0.45 + 0.15, 0.22));

  // Soft blend: overlaps saturate per channel instead of clipping.
  vec3 color = SKY + (1.0 - exp(-light * intensity));

  // Tone-map the luminance under the ceiling, keeping the hue, so text stays readable everywhere.
  float lum = dot(pow(color, vec3(2.2)), LUMA);
  color *= pow(CEILING * (1.0 - exp(-lum / CEILING)) / lum, 1.0 / 2.2);

  // Film grain, about +-3%, new every frame.
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
// `veil` (0..0.5) is a layer of the sky base between the light and the content.
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
