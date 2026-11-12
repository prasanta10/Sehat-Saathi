import { useMutation } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { api, ApiError } from '../api/client'
import { Button, Screen } from '../components/ui'
import { setTokens } from '../state/auth'

export function LoginScreen() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [phone, setPhone] = useState('')
  const [pin, setPin] = useState('')
  const login = useMutation({
    mutationFn: () => api.login(phone, pin),
    onSuccess: (tokens) => {
      setTokens(tokens)
      const next = params.get('next')
      navigate(next && next.startsWith('/') ? next : '/', { replace: true })
    },
  })
  const field = 'min-h-12 w-full rounded-lg border-2 border-ink/40 px-3 text-xl'
  const error = login.error instanceof ApiError ? (login.error.code === 'locked' ? 'login.locked' : 'login.invalid') : login.isError ? 'common.error' : null

  function submit(e: FormEvent) {
    e.preventDefault()
    login.mutate()
  }

  return (
    <Screen title={t('login.title')}>
      <form onSubmit={submit} className="flex flex-col gap-3">
        <label className="flex flex-col gap-1">
          {t('login.phone')}
          <input className={field} inputMode="numeric" autoComplete="tel" pattern="[0-9]{10}" required value={phone} onChange={(e) => setPhone(e.target.value.trim())} />
        </label>
        <label className="flex flex-col gap-1">
          {t('login.pin')}
          <input className={field} type="password" inputMode="numeric" autoComplete="current-password" required minLength={4} maxLength={8} value={pin} onChange={(e) => setPin(e.target.value)} />
        </label>
        {error && <p role="alert">{t(error)}</p>}
        <Button type="submit" data-testid="login-submit" disabled={login.isPending}>
          {t('login.submit')}
        </Button>
      </form>
      <p className="text-base">{t('login.danger_note')}</p>
    </Screen>
  )
}
