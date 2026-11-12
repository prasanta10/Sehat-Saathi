import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { setLanguage } from '../../src/i18n'
import { renderAt, stubFetch } from './render'

describe('home', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    setLanguage('hi')
  })

  it('shows API health in Hindi by default and English after switching', async () => {
    stubFetch((url) => (url.endsWith('/healthz') ? { status: 'ok', version: '9.9.9' } : []))
    setLanguage('hi')
    renderAt('/')
    expect(await screen.findByText('सर्वर से जुड़ाव है (संस्करण 9.9.9)')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'English' }))
    expect(await screen.findByText('Server is reachable (version 9.9.9)')).toBeInTheDocument()
    expect(document.documentElement.lang).toBe('en')
  })

  it('says the server is down without blocking the page', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Promise.reject(new TypeError('offline'))))
    setLanguage('en')
    renderAt('/')
    expect(await screen.findByText('Server cannot be reached. You can still use the danger-sign check.')).toBeInTheDocument()
    expect(screen.getByTestId('start-visit')).toBeEnabled()
  })
})
