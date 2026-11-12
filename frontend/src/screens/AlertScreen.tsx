import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'

import { api } from '../api/client'
import { DraftBanner } from '../components/DraftBanner'
import { BottomBar, Button, Card, Screen } from '../components/ui'
import { UrgencyBand } from '../components/UrgencyBand'
import { WhyPanel } from '../components/WhyPanel'
import { useBundle } from '../content/bundle'
import { useLocalized } from '../hooks/useLocalized'

export function AlertScreen() {
  const bundle = useBundle()
  const { t } = useTranslation()
  const loc = useLocalized()
  const navigate = useNavigate()
  const { encounterId = '' } = useParams()
  const enc = useQuery({ queryKey: ['encounter', encounterId], queryFn: () => api.encounter(encounterId) })
  const r = enc.data?.triage?.result
  if (!r) return <p>{t('common.loading')}</p>

  const sentence = r.fired.length > 0 ? loc(r.fired[0]!.text) : t(`alert.reason.${r.reason}`)
  return (
    <Screen title={t('alert.title')} step="result">
      <UrgencyBand level={r.urgency} />
      {r.review_status === 'draft' && <DraftBanner />}
      <Card>
        <p data-testid="alert-reason" className="text-xl leading-relaxed">
          {sentence}
        </p>
      </Card>
      {r.urgency === 'INCOMPLETE' && r.minimum_level && <p className="font-bold">{t('alert.minimum', { level: t(`urgency.${r.minimum_level}`) })}</p>}
      {r.missing_fact_keys.length > 0 && (
        <section aria-labelledby="missing" className="rounded-2xl border border-ink/10 bg-paper p-4 shadow-sm">
          <h2 id="missing" className="font-bold">
            {t('alert.missing')}
          </h2>
          <ul className="list-disc pl-6" data-testid="missing-list">
            {r.missing_fact_keys.map((k) => (
              <li key={k}>{loc(bundle.facts[k]?.label)}</li>
            ))}
          </ul>
          <p>{t('alert.missing_advice')}</p>
        </section>
      )}
      <WhyPanel items={r.fired.map((f) => ({ id: f.id, sources: f.sources }))} />
      <BottomBar>
        {r.urgency === 'EMERGENCY' ? (
          <Button variant="danger" onClick={() => navigate(`/emergency?${r.fired.map((f) => `sign=${f.id}`).join('&')}&visit=${encounterId}`)}>
            {t('alert.to_emergency')}
          </Button>
        ) : (
          <Button data-testid="to-plan" onClick={() => navigate(`/visit/${encounterId}/plan`)}>
            {t('alert.to_plan')}
          </Button>
        )}
      </BottomBar>
    </Screen>
  )
}
