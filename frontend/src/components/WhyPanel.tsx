import { useTranslation } from 'react-i18next'

import { type SourceRef, useBundle } from '../content/bundle'

/** Rule ID and the official source behind it: publisher, date checked, locator, verbatim excerpt. */
export function SourceList({ sources }: { sources: SourceRef[] }) {
  const bundle = useBundle()
  const { t } = useTranslation()
  return (
    <ul className="flex flex-col gap-3">
      {sources.map((s) => {
        const ref = bundle.references[s.ref]
        const excerpt = ref?.excerpts.find((e) => e.locator === s.locator)
        return (
          <li key={`${s.ref}|${s.locator}`} className="rounded-lg bg-incomplete-bg p-3 text-base" lang="en">
            <p className="font-bold">{ref?.title ?? s.ref}</p>
            <p>
              {ref?.publisher} · {ref?.version_or_date} · {t('alert.checked_on', { date: ref?.retrieved_on })}
            </p>
            <p className="italic">{s.locator}</p>
            {excerpt && <blockquote className="mt-1 border-l-4 border-ink/40 pl-2">{excerpt.text}</blockquote>}
            {ref && (
              <a href={ref.url} target="_blank" rel="noreferrer" className="mt-1 inline-block min-h-12 py-2 font-semibold text-brand underline">
                {t('alert.open_source')}
              </a>
            )}
          </li>
        )
      })}
    </ul>
  )
}

export function WhyPanel({ items }: { items: { id: string; sources: SourceRef[] }[] }) {
  const { t } = useTranslation()
  if (items.length === 0) return null
  return (
    <details data-testid="why" className="rounded-2xl border border-ink/10 bg-paper px-4 py-2 shadow-sm">
      <summary className="min-h-12 cursor-pointer py-2 text-lg font-bold text-brand">{t('alert.why')}</summary>
      {items.map((it) => (
        <div key={it.id} className="mt-2 flex flex-col gap-2">
          <p>
            {t('alert.rule')}: <code>{it.id}</code>
          </p>
          <SourceList sources={it.sources} />
        </div>
      ))}
    </details>
  )
}
