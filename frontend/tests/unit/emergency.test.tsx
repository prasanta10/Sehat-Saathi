import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { bundle, DANGER_GROUPS } from '../../src/content/bundle'
import en from '../../src/i18n/en.json'
import hi from '../../src/i18n/hi.json'
import { setLanguage } from '../../src/i18n'
import { renderAt } from './render'

describe('danger-sign check (invariant 3)', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    setLanguage('hi')
  })

  it('shows emergency instructions on one tap even when the network never answers', async () => {
    const never = vi.fn(() => new Promise<Response>(() => {}))
    vi.stubGlobal('fetch', never)
    setLanguage('en')
    renderAt('/visit/abc/questions')
    await userEvent.click(screen.getByTestId('danger-button'))
    const dialog = screen.getByRole('dialog')
    for (const g of DANGER_GROUPS) {
      expect(within(dialog).getByRole('heading', { name: en.danger.group[g] })).toBeInTheDocument()
    }
    await userEvent.click(screen.getByTestId('sign-newborn.convulsion'))
    expect(screen.getByTestId('emergency-screen')).toBeInTheDocument()
    expect(screen.getByTestId('emergency-sign')).toHaveTextContent('Newborn has convulsions (fits)')
    expect(screen.getByTestId('call-108')).toHaveAttribute('href', 'tel:108')
    // the background recording request was made but not awaited
    expect(never).toHaveBeenCalledWith('/api/v1/encounters/abc/emergency', expect.anything())
  })

  it('works with no visit at all (no visit request made)', async () => {
    const fetch = vi.fn(async (url: string) => new Response(url.endsWith('bundle') ? '{}' : '[]'))
    vi.stubGlobal('fetch', fetch)
    renderAt('/emergency?sign=general.unconscious')
    expect(screen.getByTestId('emergency-sign')).toHaveTextContent(bundle.danger_signs.signs[0]!.label.hi)
    expect(fetch.mock.calls.every((c) => !String(c[0]).includes('/encounters'))).toBe(true)
  })

  it('works while logged out, from the login screen', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('{}', { status: 401 })))
    setLanguage('en')
    renderAt('/', { loggedIn: false })
    expect(await screen.findByTestId('login-submit')).toBeInTheDocument()
    await userEvent.click(screen.getByTestId('danger-button'))
    await userEvent.click(screen.getByTestId('sign-general.unconscious'))
    expect(screen.getByTestId('emergency-screen')).toBeInTheDocument()
    expect(screen.getByTestId('call-108')).toHaveAttribute('href', 'tel:108')
  })

  it('every bundled sign has a label in both languages and a source', () => {
    for (const s of bundle.danger_signs.signs) {
      expect(s.label.en && s.label.hi && s.sources.length).toBeTruthy()
    }
  })
})

describe('the app never claims an action it did not take (invariant 10)', () => {
  const claims = /dispatch|on (its|the) way|has been (called|sent|booked)|booked|applied for|approved|eligible|भेज दी गई|बुक|स्वीकृत|पात्र हैं/i
  const flat = (o: unknown): string[] =>
    typeof o === 'string' ? [o] : Object.values(o as Record<string, unknown>).flatMap(flat)

  it.each([
    ['en', en],
    ['hi', hi],
  ])('%s strings contain no claimed actions', (_lang, strings) => {
    const bad = flat(strings).filter((s) => claims.test(s))
    expect(bad).toEqual([])
  })
})
