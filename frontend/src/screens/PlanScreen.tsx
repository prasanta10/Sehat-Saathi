import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { api } from '../api/client'
import { DraftBanner } from '../components/DraftBanner'
import { OutputCard } from '../components/OutputCard'
import { ReadAloud } from '../components/ReadAloud'
import { ShareButton } from '../components/ShareButton'
import { BottomBar, Button, Card, Screen } from '../components/ui'
import { UrgencyBand } from '../components/UrgencyBand'
import { useOutputs } from '../hooks/useOutputs'

export function PlanScreen() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { encounterId = '' } = useParams()
  const plan = useQuery({ queryKey: ['plan', encounterId], queryFn: () => api.plan(encounterId) })
  const outputs = useOutputs(encounterId)
  if (!plan.data) return <p>{plan.isError ? t('common.error') : t('common.loading')}</p>
  const p = plan.data
  const precautions = (p.return_precautions ? (i18n.language === 'en' ? p.return_precautions.en : p.return_precautions.hi) : []) ?? []
  const family = outputs.data?.find((o) => o.kind === 'family_instructions')
  const handoff = outputs.data?.find((o) => o.kind === 'clinician_handoff')

  return (
    <Screen title={t('plan.title')} step="plan">
      <UrgencyBand level={p.urgency as 'EMERGENCY' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INCOMPLETE'} />
      {p.review_status === 'draft' && <DraftBanner />}
      {p.facility_level ? (
        <dl className="flex flex-col gap-3 text-lg" data-testid="plan">
          <div className="grid grid-cols-2 gap-3">
            <Card className="flex flex-col gap-1">
              <dt className="flex items-center gap-1 text-base font-semibold text-ink/70">
                <span aria-hidden="true">🏥</span>
                {t('plan.where')}
              </dt>
              <dd className="text-lg leading-snug font-bold">{t(`facility.${p.facility_level}`)}</dd>
            </Card>
            {p.target_window && (
              <Card className="flex flex-col gap-1">
                <dt className="flex items-center gap-1 text-base font-semibold text-ink/70">
                  <span aria-hidden="true">⏰</span>
                  {t('plan.when')}
                </dt>
                <dd className="text-lg leading-snug font-bold">{t(`window.${p.target_window}`)}</dd>
              </Card>
            )}
          </div>
          {p.facility_names.length > 0 ? (
            <dd>
              <ul className="list-disc pl-6">
                {p.facility_names.map((n) => (
                  <li key={n}>{n}</li>
                ))}
              </ul>
            </dd>
          ) : (
            <dd className="text-base text-ink/70">{t('plan.facility_note')}</dd>
          )}
          {p.bring_list.length > 0 && (
            <Card>
              <dt className="mb-1 flex items-center gap-1 font-bold">
                <span aria-hidden="true">🎒</span>
                {t('plan.bring')}
              </dt>
              <dd>
                <ul className="flex flex-col gap-1">
                  {p.bring_list.map((b) => (
                    <li key={b} className="flex gap-2">
                      <span aria-hidden="true" className="text-brand">
                        ✓
                      </span>
                      {t(`bring.${b}`)}
                    </li>
                  ))}
                </ul>
              </dd>
            </Card>
          )}
        </dl>
      ) : (
        p.urgency !== 'LOW' && <p>{t('plan.no_referral')}</p>
      )}
      {precautions.length > 0 && (
        <section className="rounded-2xl border-2 border-high/40 bg-paper p-4 shadow-sm">
          <h2 className="mb-1 flex items-center gap-1 font-bold text-high">
            <span aria-hidden="true">⚠</span>
            {t('plan.precautions')}
          </h2>
          <ul className="list-disc pl-6">
            {precautions.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </section>
      )}
      {outputs.isPending && <p role="status">{t('outputs.generating')}</p>}
      {family && <OutputCard encounterId={encounterId} output={family} title={t('outputs.family_title')} actions={<ReadAloud text={family.body} lang={family.language} />} />}
      {handoff && (
        <details className="group rounded-2xl border border-ink/10 bg-paper shadow-sm">
          <summary className="flex min-h-14 cursor-pointer items-center gap-2 px-4 text-lg font-bold text-brand">
            <span aria-hidden="true">📄</span>
            {t('plan.show_note')}
          </summary>
          <div className="p-2 pt-0">
            <OutputCard
              encounterId={encounterId}
              output={handoff}
              title={t('outputs.handoff_title')}
              actions={
                <>
                  <Link
                    to={`/visit/${encounterId}/handoff`}
                    data-testid="print-link"
                    className="flex min-h-12 items-center justify-center rounded-xl border-2 border-brand px-4 font-bold text-brand"
                  >
                    {t('outputs.print')}
                  </Link>
                  <ShareButton text={handoff.body} title={t('outputs.handoff_title')} />
                </>
              }
            />
          </div>
        </details>
      )}
      <p className="font-semibold">{t('plan.not_diagnosis')}</p>
      <BottomBar>
        <Button data-testid="to-support" onClick={() => navigate(`/visit/${encounterId}/support`)}>
          {t('support.open')}
        </Button>
        <Button variant="secondary" onClick={() => navigate('/')}>
          {t('plan.done')}
        </Button>
      </BottomBar>
    </Screen>
  )
}
