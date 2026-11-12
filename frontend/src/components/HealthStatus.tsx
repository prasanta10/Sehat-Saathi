import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'

import { api } from '../api/client'

export function HealthStatus() {
  const { t } = useTranslation()
  const { data, isPending, isError } = useQuery({ queryKey: ['healthz'], queryFn: ({ signal }) => api.health(signal), retry: false })

  let text: string
  if (isPending) text = t('health.checking')
  else if (isError) text = t('health.down')
  else text = t('health.ok', { version: data.version })

  const state = isPending ? 'pending' : isError ? 'down' : 'ok'
  const dot = { pending: 'bg-ink/30', down: 'bg-emergency', ok: 'bg-low' }[state]
  return (
    <section aria-labelledby="health-title" className="flex items-start gap-2 rounded-xl px-1 text-base text-ink/70">
      <span aria-hidden="true" className={`mt-2 size-2.5 shrink-0 rounded-full ${dot}`} />
      <div>
        <h2 id="health-title" className="sr-only">
          {t('health.title')}
        </h2>
        <p data-testid="health-status" data-state={state}>
          {text}
        </p>
      </div>
    </section>
  )
}
