import { useTranslation } from 'react-i18next'

import type { Urgency } from '../api/client'

// Colour is never the only signal: each level has colour + icon + word.
export const URGENCY_STYLE: Record<Urgency, { cls: string; chip: string; icon: string }> = {
  EMERGENCY: { cls: 'bg-emergency text-white', chip: 'bg-emergency text-white', icon: '🚨' },
  HIGH: { cls: 'bg-high text-white', chip: 'bg-high text-white', icon: '⏰' },
  MEDIUM: { cls: 'bg-medium-bg text-medium border-2 border-medium', chip: 'bg-medium-bg text-medium', icon: '🩺' },
  LOW: { cls: 'bg-low text-white', chip: 'bg-low text-white', icon: '🏠' },
  INCOMPLETE: { cls: 'bg-incomplete-bg text-incomplete border-2 border-incomplete', chip: 'bg-incomplete-bg text-incomplete', icon: '❓' },
}

export function UrgencyBand({ level }: { level: Urgency }) {
  const { t } = useTranslation()
  const s = URGENCY_STYLE[level]
  return (
    <div data-testid="urgency-band" data-level={level} className={`flex items-center gap-3 rounded-2xl p-4 text-2xl font-bold shadow-sm ${s.cls}`}>
      <span aria-hidden="true" className="text-3xl">
        {s.icon}
      </span>
      <span>{t(`urgency.${level}`)}</span>
    </div>
  )
}
