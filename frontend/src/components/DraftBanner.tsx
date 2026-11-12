import { useTranslation } from 'react-i18next'

export function DraftBanner() {
  const { t } = useTranslation()
  return (
    <p role="note" data-testid="draft-banner" className="rounded-lg border-2 border-medium bg-medium-bg px-3 py-2 font-semibold">
      <span aria-hidden="true">⚠ </span>
      {t('draft_banner')}
    </p>
  )
}
