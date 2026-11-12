import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { type Recording, useRecorder } from '../hooks/useRecorder'

/** Record button. The full version is a large round microphone (main capture); `compact` is a slim button (answers). */
export function Recorder({ onDone, compact = false, label }: { onDone: (r: Recording) => void; compact?: boolean; label?: string }) {
  const { t } = useTranslation()
  const rec = useRecorder()
  const [warning, setWarning] = useState<string | null>(null)

  async function toggle() {
    if (!rec.recording) {
      setWarning(null)
      await rec.start()
      return
    }
    const r = await rec.stop()
    if (!r) return
    if (r.seconds < 1.5) setWarning('too_short')
    else if (r.peak < 0.05) setWarning('too_quiet')
    onDone(r)
  }

  const status = (
    <>
      {rec.recording && (
        <div role="status" className="flex w-full items-center gap-3">
          <span className="flex items-center gap-2 font-semibold whitespace-nowrap">
            <span aria-hidden="true" className="size-3 animate-pulse rounded-full bg-emergency" />
            {t('speech.recording', { seconds: rec.seconds })}
          </span>
          <meter aria-label={t('speech.level')} min={0} max={1} value={rec.level} className="h-4 flex-1" />
        </div>
      )}
      {rec.error && <p role="alert">{t(`speech.${rec.error}`)}</p>}
      {warning && <p role="status">{t(`speech.${warning}`)}</p>}
    </>
  )

  if (compact) {
    return (
      <div className="flex flex-col gap-2">
        <button
          type="button"
          data-testid="speak-answer"
          aria-pressed={rec.recording}
          onClick={() => void toggle()}
          className={`flex min-h-14 items-center justify-center gap-2 rounded-xl px-4 text-xl font-bold ${rec.recording ? 'bg-emergency text-white' : 'border-2 border-brand text-brand'}`}
        >
          <span aria-hidden="true">{rec.recording ? '■' : '🎤'}</span>
          {rec.recording ? t('speech.stop') : (label ?? t('speech.record'))}
        </button>
        {status}
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center gap-3">
      <button
        type="button"
        data-testid="record"
        aria-pressed={rec.recording}
        onClick={() => void toggle()}
        className={`relative flex size-32 flex-col items-center justify-center rounded-full text-lg font-bold text-white shadow-lg transition ${rec.recording ? 'bg-emergency ring-8 ring-emergency/20' : 'bg-brand ring-8 ring-brand/15'}`}
      >
        <span aria-hidden="true" className="text-4xl">
          {rec.recording ? '■' : '🎤'}
        </span>
        {rec.recording ? t('speech.stop') : (label ?? t('speech.record'))}
      </button>
      {!rec.recording && <p className="text-center text-base text-ink/70">{t('capture.record_hint')}</p>}
      {status}
    </div>
  )
}
