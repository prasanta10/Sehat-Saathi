import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'

import { api } from '../api/client'
import { FactInput, useFormatFact } from '../components/FactInput'
import { BottomBar, Button, Card, Screen } from '../components/ui'
import { useBundle } from '../content/bundle'
import { useLocalized } from '../hooks/useLocalized'

export function ConfirmScreen() {
  const bundle = useBundle()
  const { t } = useTranslation()
  const loc = useLocalized()
  const fmt = useFormatFact()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { encounterId = '' } = useParams()
  const enc = useQuery({ queryKey: ['encounter', encounterId], queryFn: () => api.encounter(encounterId) })
  const [checked, setChecked] = useState(false)
  const [editing, setEditing] = useState<string | null>(null)

  const edit = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string | number | null }) => api.editFacts(encounterId, { facts: [{ key, value }] }),
    onSuccess: (data) => {
      qc.setQueryData(['encounter', encounterId], data)
      setEditing(null)
      setChecked(false)
    },
  })
  const submit = useMutation({
    mutationFn: async () => {
      await api.confirm(encounterId)
      return api.triage(encounterId)
    },
    onSuccess: (data) => {
      qc.setQueryData(['encounter', encounterId], data)
      navigate(`/visit/${encounterId}/alert`)
    },
  })

  if (!enc.data) return <p>{t('common.loading')}</p>
  const facts = enc.data.facts.filter((f) => f.status !== 'rejected')
  const person = facts.filter((f) => bundle.facts[f.key]?.group === 'person')
  const rest = facts.filter((f) => bundle.facts[f.key]?.group !== 'person')
  const kind = (v: unknown) => (v == null || v === 'unknown' ? 'not_known' : v === 'no' ? 'absent' : 'present')
  const sections = (['present', 'absent', 'not_known'] as const).map((k) => [k, rest.filter((f) => kind(f.value) === k)] as const)
  const CHIP = { present: 'bg-yes-bg text-yes', absent: 'bg-no-bg text-ink/80', not_known: 'bg-incomplete-bg text-incomplete' }
  const ICON = { present: '✓', absent: '✕', not_known: '?' }

  const row = (f: (typeof facts)[number]) => {
    const spec = bundle.facts[f.key]
    const k = kind(f.value)
    const isPerson = spec?.group === 'person'
    return (
      <li key={f.key} className="py-1">
        <button
          type="button"
          aria-expanded={editing === f.key}
          onClick={() => setEditing(editing === f.key ? null : f.key)}
          className="flex min-h-12 w-full items-center justify-between gap-3 text-left"
        >
          <span className="flex flex-col">
            <span>{loc(spec?.label)}</span>
            {f.status === 'suggested' && f.origin === 'extracted' && (
              <span className="w-fit rounded-full bg-medium-bg px-2 text-sm font-semibold text-medium">{t('confirm.suggested')}</span>
            )}
          </span>
          <span className={`flex items-center gap-1 rounded-full px-3 py-0.5 font-bold whitespace-nowrap ${isPerson ? 'bg-ink/5' : CHIP[k]}`}>
            {!isPerson && <span aria-hidden="true">{ICON[k]}</span>}
            {fmt(spec, f.value)}
          </span>
        </button>
        {editing === f.key && spec && (
          <div className="mt-2 mb-2 rounded-2xl bg-canvas p-3">
            <FactInput spec={spec} disabled={edit.isPending} onAnswer={(value) => edit.mutate({ key: f.key, value })} />
          </div>
        )}
      </li>
    )
  }

  return (
    <Screen title={t('confirm.title')} step="check">
      <p>{t('confirm.lead')}</p>
      <div className="flex flex-col gap-3" data-testid="fact-list">
        {person.length > 0 && (
          <Card>
            <h2 className="text-base font-semibold text-ink/70">{t('confirm.person')}</h2>
            <ul className="flex flex-col divide-y divide-ink/10">{person.map(row)}</ul>
          </Card>
        )}
        {sections.map(
          ([k, list]) =>
            list.length > 0 && (
              <Card key={k}>
                <h2 className="flex items-center gap-2 text-lg font-bold">
                  <span aria-hidden="true" className={`flex size-7 items-center justify-center rounded-full text-base ${CHIP[k]}`}>
                    {ICON[k]}
                  </span>
                  {t(`confirm.${k}`)} <span className="font-normal text-ink/60">({list.length})</span>
                </h2>
                <ul className="flex flex-col divide-y divide-ink/10">{list.map(row)}</ul>
              </Card>
            ),
        )}
      </div>
      {(edit.isError || submit.isError) && <p role="alert">{t('common.error')}</p>}
      <BottomBar>
        <label className="flex min-h-12 items-center gap-3 text-lg font-semibold">
          <input data-testid="checked-with-family" type="checkbox" className="size-6 accent-brand" checked={checked} onChange={(e) => setChecked(e.target.checked)} />
          {t('confirm.checked')}
        </label>
        <Button data-testid="confirm-submit" disabled={!checked || submit.isPending} onClick={() => submit.mutate()}>
          {t('confirm.submit')}
        </Button>
      </BottomBar>
    </Screen>
  )
}
