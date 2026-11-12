import { type APIRequestContext, test as base } from '@playwright/test'

// Demo accounts are created by `python -m app.seed` when the e2e API starts (synthetic only).
export const DEMO = { phone: '9000000001', pin: '1234' }

interface Fixtures {
  api: APIRequestContext
}

/** Logged-in page and an authenticated API client, for every e2e test. */
export const test = base.extend<Fixtures>({
  api: async ({ playwright, baseURL }, provide) => {
    const anon = await playwright.request.newContext({ baseURL })
    const tokens = await (await anon.post('/api/v1/auth/login', { data: DEMO })).json()
    await anon.dispose()
    const api = await playwright.request.newContext({ baseURL, extraHTTPHeaders: { Authorization: `Bearer ${tokens.access_token}` } })
    ;(api as unknown as { tokens: unknown }).tokens = tokens
    await provide(api)
    await api.dispose()
  },
  page: async ({ page, api }, provide) => {
    const tokens = (api as unknown as { tokens: unknown }).tokens
    await page.addInitScript((t) => {
      if (!sessionStorage.getItem('e2e-logged-out')) localStorage.setItem('sehat.auth', JSON.stringify(t))
    }, tokens)
    await provide(page)
  },
})

export { expect } from '@playwright/test'
