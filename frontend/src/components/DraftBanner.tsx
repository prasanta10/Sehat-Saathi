import { useTranslation } from 'react-i18next'

export function DraftBanner() {
  const { t } = useTranslation()
  return (
    <p role="note" data-testid="draft-banner" className="text-sm text-ink/60">
      <span aria-hidden="true">ⓘ </span>
      {t('draft_banner')}
    </p>
  )
}
