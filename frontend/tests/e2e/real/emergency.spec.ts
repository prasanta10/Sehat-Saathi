import { expect, test } from '../fixtures'

import { createVisit } from '../helpers'

// One tap after opening the checklist reaches the emergency screen, from every screen.
const screens: [string, (id: string) => string][] = [
  ['home', () => '/'],
  ['person', () => '/person'],
  ['capture', (id) => `/visit/${id}/capture`],
  ['questions', (id) => `/visit/${id}/questions`],
  ['confirm', (id) => `/visit/${id}/confirm`],
  ['alert', (id) => `/visit/${id}/alert`],
  ['plan', (id) => `/visit/${id}/plan`],
]

for (const lang of ['hi', 'en'] as const) {
  for (const [name, path] of screens) {
    test(`emergency from ${name} (${lang})`, async ({ page, api }) => {
      const id = await createVisit(api, 'adult_cough')
      await page.goto(path(id))
      if (lang === 'en') await page.getByRole('button', { name: 'English' }).click()
      await page.getByTestId('danger-button').click()
      await page.getByTestId('sign-child.convulsions').click()
      await expect(page.getByTestId('emergency-screen')).toBeVisible()
      await expect(page.getByTestId('call-108')).toHaveAttribute('href', 'tel:108')
      await expect(page.getByTestId('emergency-sign')).toContainText(lang === 'en' ? 'convulsions' : 'दौरे')
    })
  }
}

test('emergency check works with the network cut', async ({ page, context }) => {
  await page.goto('/')
  await expect(page.getByTestId('health-status')).toHaveAttribute('data-state', 'ok')
  await context.setOffline(true)
  await page.getByTestId('danger-button').click()
  await page.getByTestId('sign-pregnancy.bleeding').click()
  await expect(page.getByTestId('emergency-sign')).toContainText('गर्भावस्था के दौरान रक्तस्राव')
  await context.setOffline(false)
})

test('the emergency is recorded on the visit', async ({ page, api }) => {
  const id = await createVisit(api, 'adult_cough')
  await page.goto(`/visit/${id}/questions`)
  await page.getByTestId('danger-button').click()
  await page.getByTestId('sign-general.unconscious').click()
  await expect(page.getByTestId('emergency-screen')).toBeVisible()
  await expect
    .poll(async () => (await (await api.get(`/api/v1/encounters/${id}`)).json()).triage?.result?.urgency)
    .toBe('EMERGENCY')
})
