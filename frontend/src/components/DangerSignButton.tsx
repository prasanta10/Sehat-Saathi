import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'

import { api } from '../api/client'
import { DANGER_GROUPS, useBundle } from '../content/bundle'
import { useLocalized } from '../hooks/useLocalized'
import { setRecordStatus } from '../state/emergencyRecord'

/**
 * Always-visible danger-sign check. The checklist comes from the bundled content and the
 * emergency screen is shown immediately on tap: no login, model call or network request sits
 * between the tap and the instructions. Recording on the server happens in the background.
 */
export function DangerSignButton() {
  const bundle = useBundle()
  const { t } = useTranslation()
  const loc = useLocalized()
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  const { encounterId } = useParams()

  function choose(signId: string) {
    setOpen(false)
    // Navigate first; record in the background. The instructions never wait for the network.
    navigate(`/emergency?sign=${encodeURIComponent(signId)}${encounterId ? `&visit=${encounterId}` : ''}`)
    if (encounterId) {
      setRecordStatus('pending')
      api.emergency(encounterId, [signId]).then(
        () => setRecordStatus('ok'),
        () => setRecordStatus('failed'),
      )
    } else {
      setRecordStatus('none')
    }
  }

  return (
    <>
      <button
        type="button"
        data-testid="danger-button"
        onClick={() => setOpen(true)}
        className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-emergency px-3 text-lg font-bold text-white shadow-sm"
      >
        <span aria-hidden="true">⚠</span>
        {t('danger.button')}
      </button>
      {open && (
        <div role="dialog" aria-modal="true" aria-labelledby="danger-title" className="fixed inset-0 z-50 overflow-y-auto bg-paper px-4 py-4">
          <div className="mx-auto flex max-w-md flex-col gap-4">
            <div className="flex items-start justify-between gap-2">
              <h2 id="danger-title" className="text-2xl font-bold text-emergency">
                {t('danger.title')}
              </h2>
              <button type="button" onClick={() => setOpen(false)} className="min-h-12 rounded-lg border-2 border-ink px-3 font-semibold">
                {t('danger.close')}
              </button>
            </div>
            <p>{t('danger.hint')}</p>
            {DANGER_GROUPS.map((group) => (
              <section key={group} aria-labelledby={`dg-${group}`}>
                <h3 id={`dg-${group}`} className="mb-2 text-xl font-bold">
                  {t(`danger.group.${group}`)}
                </h3>
                <ul className="flex flex-col gap-2">
                  {bundle.danger_signs.signs
                    .filter((s) => s.group === group)
                    .map((s) => (
                      <li key={s.id}>
                        <button
                          type="button"
                          data-testid={`sign-${s.id}`}
                          onClick={() => choose(s.id)}
                          className="min-h-12 w-full rounded-lg border-2 border-emergency px-3 py-2 text-left font-semibold"
                        >
                          {loc(s.label)}
                        </button>
                      </li>
                    ))}
                </ul>
              </section>
            ))}
          </div>
        </div>
      )}
    </>
  )
}
