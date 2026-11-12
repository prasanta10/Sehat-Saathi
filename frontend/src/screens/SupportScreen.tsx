import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'

import { api, type SchemeCard } from '../api/client'
import { BottomBar, Button, Screen } from '../components/ui'
import { useBundle } from '../content/bundle'
import { useLocalized } from '../hooks/useLocalized'

const STATUS_STYLE: Record<SchemeCard['status'], { cls: string; icon: string }> = {
  possibly_relevant: { cls: 'bg-brand-soft border-brand', icon: '✓' },
  needs_confirmation: { cls: 'bg-medium-bg border-medium', icon: '?' },
  not_applicable: { cls: 'bg-incomplete-bg border-incomplete', icon: '✗' },
}

function Card({ card }: { card: SchemeCard }) {
  const { t, i18n } = useTranslation()
  const bundle = useBundle()
  const loc = useLocalized()
  const [more, setMore] = useState(false)
  const lang = i18n.language === 'en' ? 'en' : 'hi'
  const list = (x: Record<string, string[]> | null | undefined) => (x ? (x[lang] ?? []) : [])
  const style = STATUS_STYLE[card.status]
  return (
    <li data-testid={`scheme-${card.id}`} data-status={card.status} className={`flex flex-col gap-2 rounded-lg border-2 p-3 ${style.cls}`}>
      <h2 className="text-xl font-bold">{card.name[lang] ?? card.name.en}</h2>
      <p className="font-bold">
        <span aria-hidden="true">{style.icon} </span>
        {t(`support.status.${card.status}`)}
      </p>
      {card.status === 'not_applicable' && card.not_applicable_note && <p>{card.not_applicable_note[lang]}</p>}
      {card.status !== 'not_applicable' && (
        <>
          <Section title={t('support.may_cover')} items={list(card.may_cover)} />
          <Section title={t('support.does_not_cover')} items={list(card.does_not_cover)} />
          <Section title={t('support.to_confirm')} items={list(card.to_confirm)} />
          <Section title={t('support.unknown')} items={card.unknown_facts.map((k) => loc(bundle.facts[k]?.label))} />
          <Section title={t('support.documents')} items={card.documents.map((d) => t(`document.${d}`))} />
          {card.amounts.map((a) => (
            <p key={a.text.en} data-testid="scheme-amount">
              {t('support.amount')}: <strong>{a.text[lang]}</strong> ({t('support.as_of', { date: a.as_of })}; {a.source.publisher})
            </p>
          ))}
          <div>
            <h3 className="font-bold">{t('support.where')}</h3>
            <p>{card.where_to_confirm[lang]}</p>
            {card.helpline && (
              <a href={`tel:${card.helpline.replace(/\D/g, '')}`} className="inline-flex min-h-12 items-center font-semibold text-brand underline">
                {t('support.call', { number: card.helpline })}
              </a>
            )}
          </div>
        </>
      )}
      <button type="button" aria-expanded={more} onClick={() => setMore(!more)} className="min-h-12 self-start font-semibold underline">
        {t('support.more')}
      </button>
      {more && (
        <ul className="flex flex-col gap-2 text-base" lang="en">
          {card.sources.map((s) => (
            <li key={`${s.ref}${s.locator}`} className="rounded bg-paper p-2">
              <p className="font-semibold">{s.title}</p>
              <p>{t('support.source', { publisher: s.publisher, date: s.retrieved_on })} · {s.locator}</p>
              {s.excerpt && <blockquote className="border-l-4 border-ink/40 pl-2">{s.excerpt}</blockquote>}
              <a href={s.url} target="_blank" rel="noreferrer" className="font-semibold text-brand underline">
                {t('alert.open_source')}
              </a>
            </li>
          ))}
        </ul>
      )}
      <p className="text-base">
        {t('support.source', { publisher: card.sources[0]?.publisher ?? '', date: card.sources[0]?.retrieved_on ?? '' })}
      </p>
    </li>
  )
}

function Section({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null
  return (
    <div>
      <h3 className="font-bold">{title}</h3>
      <ul className="list-disc pl-6">
        {items.map((x) => (
          <li key={x}>{x}</li>
        ))}
      </ul>
    </div>
  )
}

export function SupportScreen() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { encounterId = '' } = useParams()
  const schemes = useQuery({ queryKey: ['schemes', encounterId], queryFn: () => api.schemes(encounterId) })
  const enc = useQuery({ queryKey: ['encounter', encounterId], queryFn: () => api.encounter(encounterId) })
  const setCard = useMutation({
    mutationFn: (v: 'yes' | 'no' | 'unknown') => api.patchPerson(enc.data!.person.id, { ayushman_card_held: v }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['schemes', encounterId] })
      void qc.invalidateQueries({ queryKey: ['encounter', encounterId] })
    },
  })
  const asksCard = schemes.data?.cards.some((c) => c.unknown_facts.includes('ayushman_card_held'))

  return (
    <Screen title={t('support.title')}>
      <p>{t('support.lead')}</p>
      {schemes.isPending && <p role="status">{t('common.loading')}</p>}
      {schemes.isError && <p role="alert">{t('common.error')}</p>}
      {schemes.data?.pregnancy_unknown && <p className="rounded-lg bg-incomplete-bg p-3">{t('support.pregnancy_hint')}</p>}
      {asksCard && (
        <fieldset className="flex flex-col gap-2">
          <legend className="font-bold">{t('support.ayushman_q')}</legend>
          <div className="flex gap-2">
            {(['yes', 'no', 'unknown'] as const).map((v) => (
              <button key={v} type="button" data-testid={`ayushman-${v}`} onClick={() => setCard.mutate(v)} className="min-h-12 flex-1 rounded-lg border-2 border-brand font-semibold">
                {t(`common.${v}`)}
              </button>
            ))}
          </div>
        </fieldset>
      )}
      {schemes.data && schemes.data.cards.length === 0 && <p>{t('support.none')}</p>}
      <ul className="flex flex-col gap-3" data-testid="scheme-list">
        {schemes.data?.cards.map((c) => (
          <Card key={c.id} card={c} />
        ))}
      </ul>
      {schemes.data && schemes.data.unparsed_concerns.length > 0 && (
        <section>
          <h2 className="font-bold">{t('support.concerns')}</h2>
          <ul className="list-disc pl-6">
            {schemes.data.unparsed_concerns.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </section>
      )}
      <p data-testid="scheme-footer" className="rounded-lg border-2 border-ink/40 p-3 font-bold">
        {t('support.footer')}
      </p>
      <BottomBar>
        <Button variant="secondary" onClick={() => navigate('/')}>
          {t('plan.done')}
        </Button>
      </BottomBar>
    </Screen>
  )
}
