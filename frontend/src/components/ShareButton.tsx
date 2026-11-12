import { useState } from 'react'
import { useTranslation } from 'react-i18next'

/** Opens the system share sheet (or copies). It never claims the text was sent. */
export function ShareButton({ text, title }: { text: string; title: string }) {
  const { t } = useTranslation()
  const [copied, setCopied] = useState(false)
  async function share() {
    try {
      if (navigator.share) return await navigator.share({ title, text })
      await navigator.clipboard.writeText(text)
      setCopied(true)
    } catch {
      // user cancelled
    }
  }
  return (
    <div className="flex flex-col gap-1">
      <button type="button" onClick={() => void share()} className="min-h-12 rounded-xl border-2 border-brand px-4 font-bold text-brand">
        {t('outputs.share')}
      </button>
      {copied && <p role="status">{t('outputs.copied')}</p>}
    </div>
  )
}
