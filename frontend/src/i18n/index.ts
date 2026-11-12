import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import en from './en.json'
import hi from './hi.json'

export const LANGUAGES = ['hi', 'en'] as const
export type Language = (typeof LANGUAGES)[number]

const STORAGE_KEY = 'sehat.language'

function initialLanguage(): Language {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === 'hi' || stored === 'en') return stored
  } catch {
    // storage unavailable (private mode); fall back to Hindi
  }
  return 'hi'
}

export function setLanguage(lang: Language): void {
  void i18n.changeLanguage(lang)
  try {
    localStorage.setItem(STORAGE_KEY, lang)
  } catch {
    // ignore
  }
}

i18n.on('languageChanged', (lng) => {
  document.documentElement.lang = lng
})

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, hi: { translation: hi } },
  lng: initialLanguage(),
  fallbackLng: false,
  interpolation: { escapeValue: false },
  returnNull: false,
})

export default i18n
