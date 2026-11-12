import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate, useParams } from 'react-router-dom'

import { api } from '../api/client'
import { FactInput, useFormatFact } from '../components/FactInput'
import { Recorder } from '../components/Recorder'
import { Button, Card, Screen } from '../components/ui'
import { useBundle } from '../content/bundle'

const WARNING_GROUPS = new Set(['danger_sign', 'red_flag'])

export function QuestionsScreen() {
  const bundle = useBundle()
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { encounterId = '' } = useParams()
  const location = useLocation()
  const degraded = (location.state as { degraded?: boolean } | null)?.degraded
  const fmt = useFormatFact()
  const [freeText, setFreeText] = useState('')
  const [otherWay, setOtherWay] = useState(false)
  const q = useQuery({ queryKey: ['next-question', encounterId], queryFn: () => api.nextQuestion(encounterId), gcTime: 0 })
  // Progress: the most questions seen left (this one included) is the total for this visit.
  const [total, setTotal] = useState(0)
  const left = (q.data?.remaining.length ?? 0) + (q.data?.fact_key ? 1 : 0)
  if (left > total) setTotal(left)

  const answer = useMutation({
    mutationFn: (value: string | number | null) => api.answer(encounterId, { fact_key: q.data!.fact_key!, value, answered_via: 'option' }),
    onSuccess: () => {
      setFreeText('')
      setOtherWay(false)
      parse.reset()
      return qc.invalidateQueries({ queryKey: ['next-question', encounterId] })
    },
  })
  const parse = useMutation({ mutationFn: (text: string) => api.parseAnswer(encounterId, q.data!.fact_key!, text) })
  const enc = useQuery({ queryKey: ['encounter', encounterId], queryFn: () => api.encounter(encounterId) })
  const spoken = useMutation({
    mutationFn: (blob: Blob) => api.spokenAnswer(encounterId, blob),
    onSuccess: (r) => {
      if (r.text) {
        setFreeText(r.text)
        parse.mutate(r.text)
      }
    },
  })

  useEffect(() => {
    if (q.data?.done) navigate(`/visit/${encounterId}/confirm`, { replace: true })
    if (q.data?.needs_pathway) navigate(`/visit/${encounterId}/capture`, { replace: true })
  }, [q.data, encounterId, navigate])

  if (q.isError) {
    return (
      <Screen title={t('questions.title')} step="questions">
        <p role="alert">{t('common.error')}</p>
        <Button onClick={() => void q.refetch()}>{t('common.retry')}</Button>
      </Screen>
    )
  }
  if (!q.data || q.data.done || !q.data.fact_key) return <p>{t('common.loading')}</p>
  const spec = bundle.facts[q.data.fact_key]
  if (!spec) return <p role="alert">{t('common.error')}</p>
  const ask = q.data.ask ? (i18n.language === 'en' ? q.data.ask.en : q.data.ask.hi) : ''
  const done = total - left
  const warning = WARNING_GROUPS.has(spec.group)

  return (
    <Screen title={t('questions.title')} step="questions">
      <div className="flex flex-col gap-1">
        <div
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={total}
          aria-valuenow={done}
          aria-label={t('questions.progress', { count: q.data.remaining.length })}
          className="h-2 overflow-hidden rounded-full bg-ink/10"
        >
          <div className="h-full rounded-full bg-brand transition-all" style={{ width: `${total ? (100 * done) / total : 0}%` }} />
        </div>
        <p className="text-base text-ink/70">{t('questions.remaining', { count: q.data.remaining.length })}</p>
      </div>
      {degraded && (
        <p role="status" data-testid="degraded-note" className="rounded-xl bg-incomplete-bg p-3">
          {t('extract.degraded')}
        </p>
      )}
      <Card className={warning ? 'border-2 border-high/60' : ''}>
        {warning && (
          <p className="mb-2 inline-flex items-center gap-1 rounded-full bg-high/10 px-3 py-0.5 text-base font-bold text-high">
            <span aria-hidden="true">⚠</span>
            {t('questions.warning_sign')}
          </p>
        )}
        <h2 data-testid="question-text" data-fact={q.data.fact_key} className="text-2xl leading-snug font-bold">
          {ask}
        </h2>
      </Card>
      <FactInput key={q.data.fact_key} spec={spec} disabled={answer.isPending} onAnswer={(v) => answer.mutate(v)} />
      <details data-testid="other-way" className="rounded-2xl border border-ink/10 bg-paper p-3 shadow-sm" open={otherWay} onToggle={(e) => setOtherWay(e.currentTarget.open)}>
        <summary className="min-h-10 cursor-pointer text-lg font-semibold text-brand">{t('questions.other_way')}</summary>
        <form
          className="mt-3 flex flex-col gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            if (freeText.trim()) parse.mutate(freeText)
          }}
        >
          <label className="flex flex-col gap-1">
            {t('free_answer.label')}
            <div className="flex gap-2">
              <input
                data-testid="free-answer"
                className="min-h-12 flex-1 rounded-xl border-2 border-ink/30 px-3 text-lg"
                value={freeText}
                onChange={(e) => setFreeText(e.target.value)}
              />
              <button type="submit" className="min-h-12 rounded-xl border-2 border-brand px-3 font-semibold text-brand">
                {t('free_answer.check')}
              </button>
            </div>
          </label>
          {enc.data?.record_audio_consent && <Recorder compact label={t('speech.speak_answer')} onDone={(r) => spoken.mutate(r.blob)} />}
          {spoken.isPending && <p role="status">{t('speech.transcribing')}</p>}
          {spoken.data && !spoken.data.understood && <p role="status">{t('speech.asr_down')}</p>}
          {parse.data?.understood && parse.data.value != null && (
            <div className="flex flex-col gap-2 rounded-xl bg-brand-soft p-3" data-testid="parsed-answer">
              <p className="font-bold">
                {t('free_answer.understood', { value: fmt(spec, parse.data.value) })}
                {parse.data.approximate && ` (${t('extract.approximate')})`}
              </p>
              <Button onClick={() => answer.mutate(parse.data!.value as string | number)}>{t('free_answer.use')}</Button>
            </div>
          )}
          {parse.data && !parse.data.understood && <p role="status">{t('free_answer.not_understood')}</p>}
        </form>
      </details>
      {answer.isError && <p role="alert">{t('common.error')}</p>}
    </Screen>
  )
}
