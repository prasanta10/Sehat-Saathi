import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router-dom'

import { SourceList } from '../components/WhyPanel'
import { useBundle } from '../content/bundle'
import { useLocalized } from '../hooks/useLocalized'
import { useRecordStatus } from '../state/emergencyRecord'

/**
 * Full-screen emergency instructions. Works with no network: everything here comes from the
 * bundled content and i18n. It prompts the worker to call; it never says a call was made.
 */
export function EmergencyScreen() {
  const bundle = useBundle()
  const { t, i18n } = useTranslation()
  const loc = useLocalized()
  const [params] = useSearchParams()
  const record = useRecordStatus()
  const [ack, setAck] = useState(false)
  const signs = params
    .getAll('sign')
    .map((id) => bundle.danger_signs.signs.find((s) => s.id === id))
    .filter((s) => s !== undefined)

  return (
    <main data-testid="emergency-screen" className="-mx-4 flex flex-1 flex-col gap-4 bg-emergency px-4 py-4 text-white">
      <h1 className="text-3xl font-bold">
        <span aria-hidden="true">🚨 </span>
        {t('emergency.title')}
      </h1>
      <p className="text-2xl font-bold">{t('emergency.lead')}</p>
      <a href="tel:108" data-testid="call-108" className="flex min-h-16 items-center justify-center rounded-xl bg-white text-2xl font-bold text-emergency">
        {t('emergency.call_108')}
      </a>
      <a href="tel:112" className="flex min-h-14 items-center justify-center rounded-xl border-2 border-white text-xl font-bold">
        {t('emergency.call_112')}
      </a>
      <p className="text-base">{t('emergency.number_note')}</p>
      <details className="text-ink">
        <summary className="min-h-12 cursor-pointer py-2 font-semibold text-white">{t('emergency_src.numbers')}</summary>
        <SourceList sources={[{ ref: 'nhm_nas_guidelines_2026', locator: 'p20, numbers to call' }]} />
      </details>
      {/* Pre-generated audio: plays with no network and no device voice. */}
      <button
        type="button"
        data-testid="emergency-audio"
        onClick={() => void new Audio(`/audio/emergency_${i18n.language === 'en' ? 'en' : 'hi'}.mp3`).play().catch(() => undefined)}
        className="min-h-12 rounded-xl border-2 border-white text-lg font-bold"
      >
        <span aria-hidden="true">🔊 </span>
        {t('emergency_audio.play')}
      </button>
      <section>
        <h2 className="text-xl font-bold">{t('emergency.tell_title')}</h2>
        <ul className="list-disc pl-6 text-lg">
          <li>{t('emergency.tell_what')}</li>
          <li>{t('emergency.tell_who')}</li>
          <li>{t('emergency.tell_where')}</li>
        </ul>
      </section>
      <p className="text-lg font-bold">{t('emergency.no_wait')}</p>
      {signs.length > 0 && (
        <section className="text-ink">
          <h2 className="text-xl font-bold text-white">{t('emergency.signs_title')}</h2>
          <ul className="flex flex-col gap-2">
            {signs.map((s) => (
              <li key={s.id} className="rounded-lg bg-white p-3">
                <p className="text-lg font-bold" data-testid="emergency-sign">
                  {loc(s.label)}
                </p>
                <details>
                  <summary className="min-h-12 cursor-pointer py-2 font-semibold">{t('alert.why')}</summary>
                  <SourceList sources={s.sources} />
                </details>
              </li>
            ))}
          </ul>
        </section>
      )}
      {record === 'failed' && <p role="status">{t('emergency.record_failed')}</p>}
      {ack ? (
        <div className="flex flex-col gap-2">
          <p role="status" className="text-lg font-bold">
            {t('emergency.ack_done')}
          </p>
          {/* Scheme information only after the call-for-help step has been acknowledged. */}
          {params.get('visit') && (
            <Link to={`/visit/${params.get('visit')}/support`} data-testid="emergency-support" className="flex min-h-12 items-center justify-center rounded-xl bg-white font-bold text-emergency">
              {t('support.open')}
            </Link>
          )}
        </div>
      ) : (
        <button type="button" onClick={() => setAck(true)} className="min-h-12 rounded-xl border-2 border-white text-lg font-bold">
          {t('emergency.ack')}
        </button>
      )}
    </main>
  )
}
