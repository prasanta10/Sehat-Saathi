import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'

import { api, type EncounterSummary } from '../api/client'
import { setTokens } from '../state/auth'
import { HealthStatus } from '../components/HealthStatus'
import { Button, Screen } from '../components/ui'
import { URGENCY_STYLE } from '../components/UrgencyBand'
import type { Urgency } from '../api/client'

export function visitPath(e: Pick<EncounterSummary, 'id' | 'status'>): string {
  switch (e.status) {
    case 'emergency':
      return `/visit/${e.id}/alert`
    case 'triaged':
    case 'plan_ready':
    case 'handed_off':
    case 'closed':
      return `/visit/${e.id}/alert`
    case 'confirmed':
      return `/visit/${e.id}/confirm`
    case 'clarifying':
      return `/visit/${e.id}/questions`
    default:
      return `/visit/${e.id}/capture`
  }
}

function useWhen(): (iso: string) => string {
  const { i18n } = useTranslation()
  const fmt = new Intl.DateTimeFormat(i18n.language === 'en' ? 'en-IN' : 'hi-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })
  return (iso) => {
    const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : `${iso}Z`)
    return Number.isNaN(d.getTime()) ? '' : fmt.format(d)
  }
}

export function Home() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const when = useWhen()
  const visits = useQuery({ queryKey: ['encounters'], queryFn: api.encounters, retry: false })
  return (
    <Screen title={t('app.tagline')}>
      <Button data-testid="start-visit" className="min-h-16 text-xl" onClick={() => navigate('/person')}>
        <span aria-hidden="true">＋ </span>
        {t('home.start')}
      </Button>
      <section aria-labelledby="recent">
        <h2 id="recent" className="mb-2 text-xl font-bold">
          {t('home.in_progress')}
        </h2>
        {visits.data?.length === 0 && <p>{t('home.none')}</p>}
        <ul className="flex flex-col gap-2">
          {visits.data?.slice(0, 10).map((v) => {
            const u = v.urgency as Urgency | null
            return (
              <li key={v.id}>
                <Link to={visitPath(v)} className="flex min-h-16 items-center justify-between gap-3 rounded-2xl border border-ink/10 bg-paper px-4 py-2 shadow-sm">
                  <span className="flex min-w-0 flex-col">
                    <span className="truncate font-semibold">{v.person_name}</span>
                    <span className="text-sm text-ink/60">{when(v.created_at)}</span>
                  </span>
                  {u ? (
                    <span className={`flex shrink-0 items-center gap-1 rounded-full px-3 py-1 text-sm font-bold ${URGENCY_STYLE[u].chip}`}>
                      <span aria-hidden="true">{URGENCY_STYLE[u].icon}</span>
                      {t(`urgency_short.${u}`)}
                    </span>
                  ) : (
                    <span className="shrink-0 rounded-full bg-ink/5 px-3 py-1 text-sm text-ink/70">{t(`status.${v.status}`)}</span>
                  )}
                </Link>
              </li>
            )
          })}
        </ul>
      </section>
      <HealthStatus />
      <div className="flex items-center justify-between gap-2">
        <Link to="/about" className="min-h-12 py-3 font-semibold text-brand underline">
          {t('about.open')}
        </Link>
        <button
          type="button"
          data-testid="logout"
          className="min-h-12 rounded-xl border-2 border-ink/20 px-4 font-semibold text-ink/80"
          onClick={() => {
            void api.logout().finally(() => {
              setTokens(null)
              navigate('/login')
            })
          }}
        >
          {t('login.logout')}
        </button>
      </div>
    </Screen>
  )
}
