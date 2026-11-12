import { useTranslation } from 'react-i18next'
import { Link, Outlet } from 'react-router-dom'

import { DangerSignButton } from './DangerSignButton'
import { LanguageSwitch } from './LanguageSwitch'

export function Layout() {
  const { t } = useTranslation()
  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col gap-4 px-4 py-3">
      <header className="flex flex-col gap-2 print:hidden">
        <div className="flex items-center justify-between gap-2">
          <Link to="/" className="flex items-center gap-2 text-xl font-bold text-brand">
            <span aria-hidden="true" className="flex size-9 items-center justify-center rounded-xl bg-brand text-lg text-white">
              ✚
            </span>
            {t('app.name')}
          </Link>
          <LanguageSwitch />
        </div>
        <DangerSignButton />
      </header>
      <Outlet />
    </div>
  )
}
