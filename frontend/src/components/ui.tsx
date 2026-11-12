import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

type Variant = 'primary' | 'secondary' | 'danger'

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-brand text-white shadow-sm active:brightness-110',
  secondary: 'border-2 border-brand bg-white text-brand',
  danger: 'bg-emergency text-white shadow-sm',
}

export function Button({ variant = 'primary', className = '', ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return <button type="button" className={`min-h-12 w-full rounded-xl px-4 py-3 text-lg font-bold disabled:opacity-50 ${VARIANTS[variant]} ${className}`} {...props} />
}

/** White surface on the grey page. */
export function Card({ children, className = '', ...props }: { children: ReactNode; className?: string } & HTMLAttributes<HTMLElement>) {
  return (
    <section className={`rounded-2xl border border-ink/10 bg-paper p-4 shadow-sm ${className}`} {...props}>
      {children}
    </section>
  )
}

/** Primary action fixed at the bottom of the screen for one-handed use. */
export function BottomBar({ children }: { children: ReactNode }) {
  return <div className="sticky bottom-0 -mx-4 mt-auto flex flex-col gap-2 border-t border-ink/10 bg-canvas/95 px-4 py-3 backdrop-blur">{children}</div>
}

export type Step = 'concern' | 'questions' | 'check' | 'result' | 'plan'
const STEPS: Step[] = ['concern', 'questions', 'check', 'result', 'plan']

/** Where the worker is in the visit: five short steps, the current one highlighted. */
export function VisitSteps({ current }: { current: Step }) {
  const { t } = useTranslation()
  const at = STEPS.indexOf(current)
  return (
    <nav aria-label={t('steps.label')} data-testid="visit-steps">
      <ol className="flex gap-1">
        {STEPS.map((s, i) => (
          <li key={s} aria-current={i === at ? 'step' : undefined} className="flex flex-1 flex-col gap-1">
            <span className={`h-1.5 rounded-full ${i <= at ? 'bg-brand' : 'bg-ink/15'}`} />
            <span className={`text-center text-sm leading-tight ${i === at ? 'font-bold text-brand' : 'text-ink/60'}`}>{t(`steps.${s}`)}</span>
          </li>
        ))}
      </ol>
    </nav>
  )
}

export function Screen({ title, step, children }: { title: string; step?: Step; children: ReactNode }) {
  return (
    <main className="flex flex-1 flex-col gap-4">
      {step && <VisitSteps current={step} />}
      <h1 className="text-2xl font-bold">{title}</h1>
      {children}
    </main>
  )
}
