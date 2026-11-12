import { useCallback, useEffect, useRef, useState } from 'react'

export interface Recording {
  blob: Blob
  seconds: number
  peak: number // 0..1, loudest level seen
}

function pickMimeType(): string | undefined {
  const options = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus']
  return options.find((t) => typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(t))
}

/** Microphone recording with a live input level, so the worker can see it is hearing. */
export function useRecorder() {
  const [recording, setRecording] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const [level, setLevel] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const stopRef = useRef<() => Promise<Recording>>(undefined)
  const cleanupRef = useRef<() => void>(undefined)

  useEffect(() => () => cleanupRef.current?.(), [])

  const start = useCallback(async () => {
    setError(null)
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      setError('no_mic')
      return
    }
    const mimeType = pickMimeType()
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
    const chunks: Blob[] = []
    recorder.ondataavailable = (e) => e.data.size > 0 && chunks.push(e.data)
    const ctx = new AudioContext()
    const analyser = ctx.createAnalyser()
    analyser.fftSize = 512
    ctx.createMediaStreamSource(stream).connect(analyser)
    const buf = new Float32Array(analyser.fftSize)
    let peak = 0
    let raf = 0
    const tick = () => {
      analyser.getFloatTimeDomainData(buf)
      const rms = Math.sqrt(buf.reduce((s, x) => s + x * x, 0) / buf.length)
      const lvl = Math.min(1, rms * 4)
      peak = Math.max(peak, lvl)
      setLevel(lvl)
      raf = requestAnimationFrame(tick)
    }
    tick()
    const t0 = Date.now()
    const timer = setInterval(() => setSeconds(Math.round((Date.now() - t0) / 1000)), 250)
    const cleanup = () => {
      cancelAnimationFrame(raf)
      clearInterval(timer)
      stream.getTracks().forEach((tr) => tr.stop())
      void ctx.close()
    }
    cleanupRef.current = cleanup
    stopRef.current = () =>
      new Promise<Recording>((resolve) => {
        recorder.onstop = () => {
          cleanup()
          setRecording(false)
          setLevel(0)
          resolve({ blob: new Blob(chunks, { type: recorder.mimeType }), seconds: (Date.now() - t0) / 1000, peak })
        }
        recorder.stop()
      })
    recorder.start(250)
    setSeconds(0)
    setRecording(true)
  }, [])

  const stop = useCallback(async () => (stopRef.current ? stopRef.current() : null), [])
  return { recording, seconds, level, error, start, stop }
}
