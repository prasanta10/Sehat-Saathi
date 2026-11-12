import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import type { FactSpec } from '../content/bundle'
import { useLocalized } from '../hooks/useLocalized'

export type FactValue = string | number | null
type OnAnswer = (v: FactValue | 'unknown') => void

const big = 'min-h-14 w-full rounded-2xl border-2 px-4 text-xl font-bold disabled:opacity-50'

function UnknownButton({ onAnswer, disabled }: { onAnswer: OnAnswer; disabled?: boolean }) {
  const { t } = useTranslation()
  return (
    <button
      type="button"
      disabled={disabled}
      data-testid="answer-unknown"
      className="min-h-12 w-full rounded-2xl border-2 border-dashed border-ink/30 bg-paper px-4 text-lg font-semibold text-ink/80 disabled:opacity-50"
      onClick={() => onAnswer('unknown')}
    >
      {t('common.unknown')}
    </button>
  )
}

/** Large answer buttons for yes/no and choice facts; a duration picker or stepper for numbers. Always offers "Don't know". */
export function FactInput({ spec, onAnswer, disabled }: { spec: FactSpec; onAnswer: OnAnswer; disabled?: boolean }) {
  const { t } = useTranslation()
  const loc = useLocalized()

  if (spec.type === 'number') return <NumberInput spec={spec} onAnswer={onAnswer} disabled={disabled} />

  if (spec.type === 'tristate') {
    return (
      <div className="flex flex-col gap-3">
        <div className="grid grid-cols-2 gap-3">
          {(['yes', 'no'] as const).map((o) => (
            <button
              key={o}
              type="button"
              disabled={disabled}
              data-testid={`answer-${o}`}
              onClick={() => onAnswer(o)}
              className="flex min-h-24 flex-col items-center justify-center gap-1 rounded-2xl border-2 border-ink/15 bg-paper text-2xl font-bold shadow-sm active:border-brand active:bg-brand-soft disabled:opacity-50"
            >
              <span aria-hidden="true" className={`flex size-10 items-center justify-center rounded-full text-xl text-white ${o === 'yes' ? 'bg-brand' : 'bg-ink/60'}`}>
                {o === 'yes' ? '✓' : '✕'}
              </span>
              {t(`common.${o}`)}
            </button>
          ))}
        </div>
        <UnknownButton onAnswer={onAnswer} disabled={disabled} />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      {spec.values.map((o) => (
        <button key={o} type="button" disabled={disabled} data-testid={`answer-${o}`} className={`${big} border-ink/15 bg-paper shadow-sm`} onClick={() => onAnswer(o)}>
          {loc(spec.value_labels[o])}
        </button>
      ))}
      <UnknownButton onAnswer={onAnswer} disabled={disabled} />
    </div>
  )
}

type Unit = 'days' | 'weeks' | 'months'
const FACTOR: Record<Unit, number> = { days: 1, weeks: 7, months: 30 }
const UNIT_KEY: Record<Unit, string> = { days: 'day', weeks: 'week', months: 'month' }
/** Common answers, as the family says them. */
const QUICK: [number, Unit][] = [
  [1, 'days'],
  [2, 'days'],
  [3, 'days'],
  [5, 'days'],
  [1, 'weeks'],
  [2, 'weeks'],
  [3, 'weeks'],
  [1, 'months'],
]

function NumberInput({ spec, onAnswer, disabled }: { spec: FactSpec; onAnswer: OnAnswer; disabled?: boolean }) {
  const { t } = useTranslation()
  const isDuration = spec.unit === 'days'
  const [amount, setAmount] = useState('')
  const [unit, setUnit] = useState<Unit>('days')
  const n = Number(amount)
  const total = amount === '' || !Number.isFinite(n) ? null : n * (isDuration ? FACTOR[unit] : 1)
  const valid = total != null && (spec.min == null || total >= spec.min) && (spec.max == null || total <= spec.max)
  const say = (count: number, u: Unit) => t(`duration.${UNIT_KEY[u]}`, { count })
  const step = (d: number) => setAmount(String(Math.max(spec.min ?? 0, (amount === '' ? 0 : n) + d)))
  const stepBtn = 'flex size-14 shrink-0 items-center justify-center rounded-2xl border-2 border-brand bg-paper text-3xl font-bold text-brand disabled:opacity-40'

  return (
    <div className="flex flex-col gap-4">
      {isDuration && (
        <div className="flex flex-col gap-2">
          <p className="font-semibold">{t('questions.quick')}</p>
          <div className="grid grid-cols-4 gap-2">
            {QUICK.map(([a, u]) => {
              const on = amount === String(a) && unit === u
              return (
                <button
                  key={`${a}${u}`}
                  type="button"
                  disabled={disabled}
                  aria-pressed={on}
                  data-testid={`quick-${a * FACTOR[u]}`}
                  onClick={() => {
                    setAmount(String(a))
                    setUnit(u)
                  }}
                  className="min-h-14 rounded-xl border-2 border-ink/15 bg-paper px-1 text-base leading-tight font-bold shadow-sm aria-pressed:border-brand aria-pressed:bg-brand aria-pressed:text-white"
                >
                  {say(a, u)}
                </button>
              )
            })}
          </div>
        </div>
      )}
      <div className="flex flex-col gap-2">
        {isDuration && <p className="font-semibold">{t('questions.exact')}</p>}
        <div className="flex items-center gap-2">
          <button type="button" aria-label={t('questions.less')} disabled={disabled || amount === '' || n <= (spec.min ?? 0)} className={stepBtn} onClick={() => step(-1)}>
            −
          </button>
          <label className="flex-1">
            <span className="sr-only">{t('questions.number_label')}</span>
            <input
              data-testid="answer-number"
              type="number"
              inputMode="numeric"
              min={spec.min ?? undefined}
              max={spec.max ?? undefined}
              className="min-h-14 w-full rounded-2xl border-2 border-ink/30 bg-paper px-3 text-center text-3xl font-bold"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
          </label>
          <button type="button" aria-label={t('questions.more')} disabled={disabled} className={stepBtn} onClick={() => step(1)}>
            +
          </button>
          {!isDuration && spec.unit && spec.unit !== 'count' && <span className="text-xl">{t(`questions.unit.${spec.unit}`)}</span>}
        </div>
        {isDuration && (
          <div role="group" aria-label={t('questions.number_label')} className="grid grid-cols-3 gap-1 rounded-2xl bg-ink/5 p-1">
            {(['days', 'weeks', 'months'] as const).map((u) => (
              <button
                key={u}
                type="button"
                aria-pressed={unit === u}
                data-testid={`unit-${u}`}
                onClick={() => setUnit(u)}
                className="min-h-11 rounded-xl text-lg font-semibold aria-pressed:bg-paper aria-pressed:text-brand aria-pressed:shadow-sm"
              >
                {t(`questions.unit.${u}`)}
              </button>
            ))}
          </div>
        )}
        {isDuration && unit !== 'days' && total != null && amount !== '' && (
          <p className="text-center text-lg" data-testid="total-days">
            {t('questions.total_days', { count: total })}
            {unit === 'months' && <span className="block text-base text-ink/70">{t('questions.month_note')}</span>}
          </p>
        )}
      </div>
      <button
        type="button"
        data-testid="answer-submit"
        disabled={!valid || disabled}
        className={`${big} border-brand bg-brand text-white shadow-sm`}
        onClick={() => total != null && onAnswer(total)}
      >
        {t('common.next')}
        {valid && isDuration && ` · ${say(n, unit)}`}
      </button>
      <UnknownButton onAnswer={onAnswer} disabled={disabled} />
    </div>
  )
}

export function useFormatFact(): (spec: FactSpec | undefined, value: FactValue | undefined) => string {
  const { t } = useTranslation()
  const loc = useLocalized()
  return (spec, value) => {
    if (value == null || value === 'unknown' || !spec) return t('common.not_known')
    if (spec.type === 'tristate') return t(`common.${String(value)}`)
    if (spec.type === 'enum') return loc(spec.value_labels[String(value)]) || String(value)
    if (spec.unit === 'days' && typeof value === 'number') return t('duration.day', { count: value })
    const unit = spec.unit && spec.unit !== 'count' ? ` ${t(`questions.unit.${spec.unit}`)}` : ''
    return `${value}${unit}`
  }
}
