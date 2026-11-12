import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'

import { api } from '../api/client'
import { Recorder } from '../components/Recorder'
import { BottomBar, Button, Card, Screen } from '../components/ui'
import { useBundle } from '../content/bundle'
import type { Recording } from '../hooks/useRecorder'
import { useLocalized } from '../hooks/useLocalized'

type Consent = 'unasked' | 'granted' | 'declined'

export function CaptureScreen() {
  const bundle = useBundle()
  const { t } = useTranslation()
  const loc = useLocalized()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { encounterId = '' } = useParams()
  const enc = useQuery({ queryKey: ['encounter', encounterId], queryFn: () => api.encounter(encounterId) })
  const [text, setText] = useState('')
  const [pathway, setPathway] = useState<string | null>(null)
  const [consent, setConsent] = useState<Consent>('unasked')
  const [audioCaptureId, setAudioCaptureId] = useState<string | null>(null)
  const [asrDown, setAsrDown] = useState(false)
  const pathways = Object.values(bundle.pathways)
  const chosen = pathway ?? enc.data?.pathway_id ?? (pathways.length === 1 ? pathways[0]!.id : null)

  const recordConsent = useMutation({
    mutationFn: (granted: boolean) => api.consent(encounterId, 'record_audio', granted),
    onSuccess: (c) => setConsent(c.granted ? 'granted' : 'declined'),
  })

  const transcribe = useMutation({
    mutationFn: (r: Recording) => api.captureAudio(encounterId, r.blob),
    onSuccess: (res) => {
      qc.setQueryData(['encounter', encounterId], res.encounter)
      if (res.degraded) {
        setAsrDown(true)
        return
      }
      const last = res.encounter.captures.at(-1)
      if (last) {
        setAudioCaptureId(last.id)
        setText(last.transcript)
      }
    },
  })

  const [slow, setSlow] = useState(false)
  const go = useMutation({
    mutationFn: async () => {
      if (chosen !== enc.data?.pathway_id) await api.patchEncounter(encounterId, { pathway_id: chosen })
      if (!text.trim()) return null
      const capture = enc.data?.captures.find((c) => c.id === audioCaptureId)
      if (capture) {
        if (capture.transcript !== text.trim()) await api.editTranscript(encounterId, capture.id, text)
      } else {
        await api.captureText(encounterId, text)
      }
      return api.extract(encounterId)
    },
    onSuccess: (result) => {
      if (result && !result.degraded) navigate(`/visit/${encounterId}/facts`)
      else navigate(`/visit/${encounterId}/questions`, { state: { degraded: !!result?.degraded } })
    },
  })
  // Waiting is honest: after a few seconds offer the manual path, which always works.
  useEffect(() => {
    if (!go.isPending) return
    const timer = setTimeout(() => setSlow(true), 6000)
    return () => {
      clearTimeout(timer)
      setSlow(false)
    }
  }, [go.isPending])

  return (
    <Screen title={t('capture.title')} step="concern">
      {consent === 'unasked' && (
        <Card className="flex flex-col gap-3" aria-labelledby="consent-q">
          <h2 id="consent-q" className="text-lg font-bold">
            <span aria-hidden="true">🎤 </span>
            {t('speech.consent_q')}
          </h2>
          <p className="text-base text-ink/80">{t('speech.consent_why')}</p>
          <div className="flex gap-2">
            <Button data-testid="consent-yes" disabled={recordConsent.isPending} onClick={() => recordConsent.mutate(true)}>
              {t('speech.consent_yes')}
            </Button>
            <Button variant="secondary" data-testid="consent-no" disabled={recordConsent.isPending} onClick={() => recordConsent.mutate(false)}>
              {t('speech.consent_no')}
            </Button>
          </div>
        </Card>
      )}
      {consent === 'granted' && !audioCaptureId && !asrDown && (
        <Card className="flex flex-col items-center gap-2 py-6">
          <Recorder onDone={(r) => transcribe.mutate(r)} />
          {transcribe.isPending && (
            <p role="status" className="font-semibold">
              {t('speech.transcribing')}
            </p>
          )}
          {transcribe.isError && <p role="alert">{t('common.error')}</p>}
          <p className="text-sm text-ink/60">{t('speech.mic_note')}</p>
        </Card>
      )}
      {asrDown && (
        <p role="status" data-testid="asr-down" className="rounded-lg bg-incomplete-bg p-3">
          {t('speech.asr_down')}
        </p>
      )}
      <label className="flex flex-col gap-1 font-semibold">
        {audioCaptureId ? t('speech.transcript_label') : consent === 'granted' ? t('capture.or_type') : t('capture.type_label')}
        <textarea
          data-testid="capture-text"
          rows={4}
          placeholder={t('capture.placeholder')}
          className="w-full rounded-2xl border-2 border-ink/20 bg-paper p-3 text-lg font-normal shadow-sm placeholder:text-ink/40"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
      </label>
      {pathways.length === 1 ? (
        <p data-testid="concern-fixed" className="flex items-center gap-2 rounded-xl bg-brand-soft px-3 py-2 text-base">
          <span aria-hidden="true">ℹ</span>
          {t('capture.concern_fixed', { name: loc(pathways[0]!.title) })}
        </p>
      ) : (
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-1 font-bold">{t('capture.pathway')}</legend>
          {pathways.map((p) => (
            <button
              key={p.id}
              type="button"
              aria-pressed={chosen === p.id}
              onClick={() => setPathway(p.id)}
              className="min-h-12 rounded-xl border-2 border-brand bg-paper px-3 text-left aria-pressed:bg-brand aria-pressed:text-white"
            >
              {loc(p.title)}
            </button>
          ))}
        </fieldset>
      )}
      {go.isError && <p role="alert">{t('common.error')}</p>}
      {go.isPending && text.trim() && (
        <p role="status" data-testid="extract-working" className="flex items-center gap-2 font-semibold">
          <span aria-hidden="true" className="size-4 animate-spin rounded-full border-2 border-brand border-t-transparent" />
          {t('extract.working')}
        </p>
      )}
      {slow && go.isPending && (
        <Button variant="secondary" data-testid="by-hand" onClick={() => navigate(`/visit/${encounterId}/questions`)}>
          {t('extract.by_hand')}
        </Button>
      )}
      <BottomBar>
        <Button data-testid="capture-continue" disabled={!chosen || go.isPending || transcribe.isPending} onClick={() => go.mutate()}>
          {t('capture.continue')}
        </Button>
      </BottomBar>
    </Screen>
  )
}
