import { useTranslation } from 'react-i18next'

import { Screen } from '../components/ui'
import { useBundle } from '../content/bundle'
import { useLocalized } from '../hooks/useLocalized'

/** Every official source behind the app, and the review status of clinical content. */
export function AboutScreen() {
  const bundle = useBundle()
  const { t } = useTranslation()
  const loc = useLocalized()
  const status = (s: string) => (s === 'clinician_reviewed' ? t('about.reviewed') : t('about.draft'))
  return (
    <Screen title={t('about.title')}>
      <p>{t('about.lead')}</p>
      <ul className="flex flex-col gap-1" data-testid="review-status">
        <li>
          {t('about.danger_signs')}: <strong>{status(bundle.danger_signs.review.status)}</strong>
        </li>
        {Object.values(bundle.pathways).map((p) => (
          <li key={p.id}>
            {t('about.pathway')} “{loc(p.title)}”: <strong>{status(p.review.status)}</strong>
          </li>
        ))}
      </ul>
      <h2 className="text-xl font-bold">{t('about.references')}</h2>
      <ul className="flex flex-col gap-3" data-testid="reference-list" lang="en">
        {Object.values(bundle.references).map((r) => (
          <li key={r.id} className="rounded-lg border-2 border-ink/20 p-3 text-base">
            <p className="font-bold">{r.title}</p>
            <p>
              {r.publisher} · {r.version_or_date} · {t('about.checked', { date: r.retrieved_on })}
            </p>
            <a href={r.url} target="_blank" rel="noreferrer" className="font-semibold text-brand underline">
              {t('alert.open_source')}
            </a>
          </li>
        ))}
      </ul>
    </Screen>
  )
}
