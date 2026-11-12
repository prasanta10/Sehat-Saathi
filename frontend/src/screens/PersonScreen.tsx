import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

import { api, type PersonIn } from '../api/client'
import { Button, Screen } from '../components/ui'
import { useBundle } from '../content/bundle'

export function PersonScreen() {
  const bundle = useBundle()
  const DEFAULT_PATHWAY = Object.keys(bundle.pathways)[0] ?? null
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const persons = useQuery({ queryKey: ['persons'], queryFn: api.persons })
  const [tab, setTab] = useState<'new' | 'existing'>('new')
  const [search, setSearch] = useState('')
  const [form, setForm] = useState<PersonIn>({ name: '', pregnant: 'unknown', ayushman_card_held: 'unknown', synthetic: true })

  const start = useMutation({
    mutationFn: (personId: string) => api.createEncounter({ person_id: personId, language: i18n.language === 'en' ? 'en' : 'hi', pathway_id: DEFAULT_PATHWAY }),
    onSuccess: (enc) => {
      void qc.invalidateQueries({ queryKey: ['encounters'] })
      navigate(`/visit/${enc.id}/capture`)
    },
  })
  const add = useMutation({ mutationFn: api.createPerson, onSuccess: (p) => start.mutate(p.id) })

  function submit(e: FormEvent) {
    e.preventDefault()
    add.mutate(form)
  }
  const num = (v: string) => (v === '' ? null : Number(v))
  const field = 'min-h-12 w-full rounded-xl border-2 border-ink/20 bg-paper px-3 text-lg'

  const all = persons.data ?? []
  const found = all.filter((p) => p.name.toLowerCase().includes(search.trim().toLowerCase()))
  const tabBtn = 'min-h-11 flex-1 rounded-xl text-lg font-semibold aria-selected:bg-paper aria-selected:text-brand aria-selected:shadow-sm'

  return (
    <Screen title={t('person.title')}>
      <div role="tablist" className="grid grid-cols-2 gap-1 rounded-2xl bg-ink/5 p-1">
        <button type="button" role="tab" aria-selected={tab === 'new'} className={tabBtn} onClick={() => setTab('new')}>
          {t('person.tab_new')}
        </button>
        <button type="button" role="tab" data-testid="tab-existing" aria-selected={tab === 'existing'} className={tabBtn} onClick={() => setTab('existing')}>
          {t('person.tab_existing', { count: all.length })}
        </button>
      </div>
      {tab === 'existing' && (
        <section aria-labelledby="pick" className="flex flex-col gap-2">
          <h2 id="pick" className="sr-only">
            {t('person.pick')}
          </h2>
          <label className="flex flex-col gap-1">
            <span className="sr-only">{t('person.search')}</span>
            <input type="search" placeholder={`🔍 ${t('person.search')}`} className={field} value={search} onChange={(e) => setSearch(e.target.value)} />
          </label>
          {found.length === 0 && <p className="text-ink/70">{t('person.none_found')}</p>}
          <ul className="flex flex-col gap-2">
            {found.map((p) => (
              <li key={p.id}>
                <button
                  type="button"
                  onClick={() => start.mutate(p.id)}
                  disabled={start.isPending}
                  className="flex min-h-14 w-full items-center justify-between gap-2 rounded-2xl border border-ink/10 bg-paper px-4 py-2 text-left shadow-sm"
                >
                  <span className="flex flex-col">
                    <span className="font-semibold">{p.name}</span>
                    {p.village && <span className="text-sm text-ink/60">{p.village}</span>}
                  </span>
                  <span className="text-ink/70">
                    {p.age_years != null ? t('person.years', { count: p.age_years }) : ''}
                    {p.sex ? ` · ${t(`person.sex_${p.sex}`)}` : ''}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
      {tab === 'new' && (
        <form onSubmit={submit} aria-labelledby="add" className="flex flex-col gap-3 rounded-2xl border border-ink/10 bg-paper p-4 shadow-sm">
          <h2 id="add" className="sr-only">
            {t('person.add')}
          </h2>
          <label className="flex flex-col gap-1">
            {t('person.name')}
            <input required className={field} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </label>
          <label className="flex flex-col gap-1">
            {t('person.age_years')}
            <input
              className={field}
              inputMode="numeric"
              type="number"
              min={0}
              max={120}
              value={form.age_years ?? ''}
              onChange={(e) => setForm({ ...form, age_years: num(e.target.value) })}
            />
          </label>
          {form.age_years != null && form.age_years < 5 && (
            <label className="flex flex-col gap-1">
              {t('person.age_months')}
              <input
                className={field}
                inputMode="numeric"
                type="number"
                min={0}
                max={59}
                value={form.age_months ?? ''}
                onChange={(e) => setForm({ ...form, age_months: num(e.target.value) })}
              />
            </label>
          )}
          <fieldset className="flex flex-col gap-1">
            <legend>{t('person.sex')}</legend>
            <div className="flex gap-2">
              {(['female', 'male', 'other'] as const).map((s) => (
                <button
                  key={s}
                  type="button"
                  aria-pressed={form.sex === s}
                  onClick={() => setForm({ ...form, sex: s })}
                  className="min-h-12 flex-1 rounded-xl border-2 border-brand bg-paper font-semibold aria-pressed:bg-brand aria-pressed:text-white"
                >
                  {t(`person.sex_${s}`)}
                </button>
              ))}
            </div>
          </fieldset>
          <label className="flex flex-col gap-1">
            {t('person.village')}
            <input className={field} value={form.village ?? ''} onChange={(e) => setForm({ ...form, village: e.target.value })} />
          </label>
          {form.sex === 'female' && (
            <fieldset className="flex flex-col gap-1">
              <legend>{t('person.pregnant')}</legend>
              <div className="flex gap-2">
                {(['yes', 'no', 'unknown'] as const).map((v) => (
                  <button
                    key={v}
                    type="button"
                    aria-pressed={form.pregnant === v}
                    onClick={() => setForm({ ...form, pregnant: v })}
                    className="min-h-12 flex-1 rounded-xl border-2 border-brand bg-paper font-semibold aria-pressed:bg-brand aria-pressed:text-white"
                  >
                    {t(`common.${v}`)}
                  </button>
                ))}
              </div>
            </fieldset>
          )}
          <Button type="submit" data-testid="person-start" disabled={add.isPending || start.isPending}>
            {t('person.start')}
          </Button>
          {(add.isError || start.isError) && <p role="alert">{t('common.error')}</p>}
        </form>
      )}
    </Screen>
  )
}
