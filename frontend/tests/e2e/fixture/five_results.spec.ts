import { expect, test } from '../fixtures'

import { answerQuestions, confirmFacts, createVisit } from '../helpers'

// Synthetic fixture content (backend/tests/fixtures/content): the real adult_cough pathway has no
// LOW rule because no official source defines home care for it, so LOW is shown on fixture rules.
const BASE = { fx_symptom: 'yes', fx_severe: 'no', fx_marker_high: 'no', fx_optional: 'no' }
const cases = [
  ['EMERGENCY', { ...BASE, fx_severe: 'yes' }],
  ['HIGH', { ...BASE, fx_marker_high: 'yes', fx_duration_days: 1 }],
  ['MEDIUM', { ...BASE, fx_duration_days: 12 }],
  ['LOW', { ...BASE, fx_duration_days: 2 }],
  ['INCOMPLETE', { ...BASE, fx_duration_days: 5 }],
] as const

for (const lang of ['hi', 'en'] as const) {
  for (const [level, answers] of cases) {
    test(`typed visit reaches ${level} (${lang})`, async ({ page, api }) => {
      const id = await createVisit(api, 'fx_with_low', { age_years: 40 })
      await page.goto(`/visit/${id}/capture`)
      if (lang === 'en') await page.getByRole('button', { name: 'English' }).click()
      await page.getByTestId('capture-text').fill('synthetic fixture account')
      await page.getByTestId('capture-continue').click()
      await answerQuestions(page, answers)
      await confirmFacts(page)
      await expect(page.getByTestId('urgency-band')).toHaveAttribute('data-level', level)
      await expect(page.getByTestId('draft-banner')).toBeVisible()
    })
  }
}
