import { expect, test } from '../fixtures'
import { answerQuestions, confirmFacts, createVisit } from '../helpers'

async function mediumVisit(page: import('@playwright/test').Page, api: import('@playwright/test').APIRequestContext) {
  const id = await createVisit(api, 'adult_cough')
  await page.goto(`/visit/${id}/capture`)
  await page.getByRole('button', { name: 'English' }).click()
  await page.getByTestId('consent-no').click()
  await page.getByTestId('capture-continue').click()
  await answerQuestions(page, { cough_present: 'yes', cough_duration_days: 21 })
  await confirmFacts(page)
  return id
}

test('support screen: honest scheme cards with sources, after the result', async ({ page, api }) => {
  await mediumVisit(page, api)
  await page.getByTestId('to-plan').click()
  await page.getByTestId('to-support').click()
  const tb = page.getByTestId('scheme-ntep_free_tb_care')
  await expect(tb).toHaveAttribute('data-status', 'possibly_relevant')
  await expect(tb).toContainText('May help')
  await expect(page.getByTestId('scheme-pmjay')).toHaveAttribute('data-status', 'not_applicable')
  await expect(page.getByTestId('scheme-pmjay')).toContainText('does not pay for an ordinary out-patient visit')
  const npy = page.getByTestId('scheme-nikshay_poshan_yojana')
  await expect(npy).toContainText('Needs checking')
  await expect(npy).toContainText('Only if TB is diagnosed and notified')
  await expect(npy.getByTestId('scheme-amount')).toContainText('2024-11-01')
  await tb.getByRole('button', { name: 'Tell me more' }).click()
  await expect(tb).toContainText('free screening and treatment services')
  await expect(page.getByTestId('scheme-footer')).toContainText('Eligibility is decided by the scheme authorities')
  await expect(page.locator('body')).not.toContainText(/approved|you are eligible|guaranteed/i)
})

test('a hung scheme service never delays the alert or the plan', async ({ page, api }) => {
  await page.route('**/schemes**', () => {
    /* never answers */
  })
  await mediumVisit(page, api)
  await expect(page.getByTestId('urgency-band')).toHaveAttribute('data-level', 'MEDIUM')
  await page.getByTestId('to-plan').click()
  await expect(page.getByTestId('plan')).toBeVisible()
})

test('after an emergency, support information appears only once help has been called', async ({ page, api }) => {
  const id = await createVisit(api, 'adult_cough')
  await page.goto(`/visit/${id}/questions`)
  await page.getByTestId('danger-button').click()
  await page.getByTestId('sign-general.unconscious').click()
  await expect(page.getByTestId('emergency-screen')).toBeVisible()
  await expect(page.getByTestId('emergency-support')).toHaveCount(0)
  await page.getByRole('button', { name: 'मैंने मदद बुला ली है' }).click()
  await page.getByTestId('emergency-support').click()
  await expect(page.getByTestId('scheme-ambulance_108_102')).toBeVisible()
})

test('sources and review status are listed', async ({ page }) => {
  await page.goto('/about')
  await expect(page.getByTestId('reference-list')).toContainText('National Ambulance Service')
  await expect(page.getByTestId('review-status')).toContainText('मसौदा')
})
