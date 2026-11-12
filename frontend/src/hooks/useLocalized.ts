import { useTranslation } from 'react-i18next'

import type { I18nText } from '../content/bundle'

/** Pick the current language from a content-file string ({en, hi}). */
export function useLocalized(): (text: I18nText | null | undefined) => string {
  const { i18n } = useTranslation()
  return (text) => (text ? (i18n.language === 'en' ? text.en : text.hi) : '')
}
