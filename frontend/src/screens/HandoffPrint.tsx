import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'

import { useOutputs } from '../hooks/useOutputs'

/** One-page printable clinician handoff (browser print / save as PDF). */
export function HandoffPrint() {
  const { t } = useTranslation()
  const { encounterId = '' } = useParams()
  const outputs = useOutputs(encounterId)
  const handoff = outputs.data?.find((o) => o.kind === 'clinician_handoff')
  if (!handoff) return <p>{t('common.loading')}</p>
  return (
    <main className="flex flex-col gap-3">
      <div className="flex gap-2 print:hidden">
        <button type="button" onClick={() => window.print()} className="min-h-12 rounded-xl bg-brand px-4 font-bold text-white">
          {t('outputs.print')}
        </button>
        <Link to={`/visit/${encounterId}/plan`} className="flex min-h-12 items-center rounded-xl border-2 border-brand px-4 font-bold text-brand">
          {t('outputs.print_back')}
        </Link>
      </div>
      <article data-testid="handoff-print" lang={handoff.language} className="whitespace-pre-line text-base leading-snug print:text-[11pt]">
        {handoff.body}
      </article>
    </main>
  )
}
