import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'

import { api } from '../api/client'
import { useFormatFact } from '../components/FactInput'
import { BottomBar, Button, Card, Screen } from '../components/ui'
import { useBundle } from '../content/bundle'
import { useLocalized } from '../hooks/useLocalized'

/** The transcript with each piece of evidence marked, so the worker sees where every suggestion came from. */
export function highlight(text: string, spans: string[]): ReactNode[] {
  const lower = text.toLowerCase()
  const marks: [number, number][] = []
  for (const s of spans) {
    const i = s.trim() ? lower.indexOf(s.trim().toLowerCase()) : -1
    if (i >= 0) marks.push([i, i + s.trim().length])
  }
  marks.sort((a, b) => a[0] - b[0])
  const out: ReactNode[] = []
  let at = 0
  for (const [a, b] of marks) {
    if (b <= at) continue
    const from = Math.max(a, at)
    if (from > at) out.push(text.slice(at, from))
    out.push(
      <mark key={from} className="rounded bg-medium-bg px-0.5 text-ink">
        {text.slice(from, b)}
      </mark>,
    )
    at = b
  }
  if (at < text.length) out.push(text.slice(at))
  return out
}

/** Screen 4: what the app understood, each with the words it came from. Nothing here is confirmed. */
export function SuggestedFactsScreen() {
  const bundle = useBundle()
  const { t } = useTranslation()
  const loc = useLocalized()
  const fmt = useFormatFact()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { encounterId = '' } = useParams()
  const enc = useQuery({ queryKey: ['encounter', encounterId], queryFn: () => api.encounter(encounterId) })
  const reject = useMutation({ mutationFn: (key: string) => api.rejectFact(encounterId, key), onSuccess: (data) => qc.setQueryData(['encounter', encounterId], data) })
  if (!enc.data) return <p>{t('common.loading')}</p>
  const suggested = enc.data.facts.filter((f) => f.origin === 'extracted' && f.status === 'suggested')
  const transcript = enc.data.captures.at(-1)?.transcript ?? ''

  return (
    <Screen title={t('extract.title')} step="concern">
      {transcript && (
        <Card data-testid="heard">
          <h2 className="mb-1 text-base font-semibold text-ink/70">
            <span aria-hidden="true">🗣 </span>
            {t('extract.heard')}
          </h2>
          <p className="text-xl leading-relaxed">
            {highlight(
              transcript,
              suggested.map((f) => f.evidence ?? ''),
            )}
          </p>
        </Card>
      )}
      {suggested.length === 0 ? (
        <p className="rounded-xl bg-incomplete-bg p-3">{t('extract.none_scope')}</p>
      ) : (
        <>
          <p className="text-base text-ink/80">{t('extract.lead')}</p>
          <h2 className="text-lg font-bold">{t('extract.found', { count: suggested.length })}</h2>
        </>
      )}
      <ul className="flex flex-col gap-3" data-testid="suggested-list">
        {suggested.map((f) => {
          const spec = bundle.facts[f.key]
          return (
            <li key={f.key} data-testid={`suggested-${f.key}`} className="flex flex-col gap-2 rounded-2xl border border-ink/10 bg-paper p-4 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <span className="text-lg">{loc(spec?.label)}</span>
                <span className="rounded-full bg-brand-soft px-3 py-0.5 text-lg font-bold whitespace-nowrap text-brand">{fmt(spec, f.value)}</span>
              </div>
              {f.evidence && (
                <p className="border-l-4 border-medium/40 pl-3 text-base text-ink/80">
                  <span className="font-semibold">{t('extract.heard_from')}</span> <span className="italic">{f.evidence}</span>
                </p>
              )}
              <div className="flex items-center justify-between gap-2">
                <span className="rounded-full bg-medium-bg px-2 text-sm font-semibold text-medium">{t('extract.suggested')}</span>
                <button
                  type="button"
                  disabled={reject.isPending}
                  onClick={() => reject.mutate(f.key)}
                  className="min-h-11 rounded-xl border-2 border-ink/20 px-3 font-semibold text-ink/80"
                >
                  <span aria-hidden="true">✕ </span>
                  {t('extract.remove')}
                </button>
              </div>
            </li>
          )
        })}
      </ul>
      {enc.data.unparsed_concerns.length > 0 && (
        <Card>
          <h2 className="font-bold">{t('extract.concerns')}</h2>
          <ul className="list-disc pl-6" data-testid="concerns-list">
            {enc.data.unparsed_concerns.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </Card>
      )}
      <BottomBar>
        <Button data-testid="suggested-continue" onClick={() => navigate(`/visit/${encounterId}/questions`)}>
          {t('extract.continue')}
        </Button>
      </BottomBar>
    </Screen>
  )
}
