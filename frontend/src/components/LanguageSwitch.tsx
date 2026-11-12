import { useTranslation } from 'react-i18next'

import { LANGUAGES, setLanguage } from '../i18n'

/** Compact two-way switch; each option keeps its full name for screen readers and tests. */
export function LanguageSwitch() {
  const { t, i18n } = useTranslation()
  return (
    <div role="group" aria-label={t('language.label')} className="flex rounded-xl border-2 border-brand bg-paper p-0.5">
      {LANGUAGES.map((lang) => (
        <button
          key={lang}
          type="button"
          lang={lang}
          aria-pressed={i18n.language === lang}
          onClick={() => setLanguage(lang)}
          className="min-h-11 rounded-lg px-3 text-base font-semibold text-brand aria-pressed:bg-brand aria-pressed:text-white"
        >
          {t(`language.${lang}`)}
        </button>
      ))}
    </div>
  )
}
