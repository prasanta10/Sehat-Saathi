import { expect, test } from '../fixtures'

import { answerQuestions, confirmFacts, createVisit } from '../helpers'

const ACCOUNT = 'Synthetic: teen hafte se khansi hai, bukhar nahi hai. Raat ko pasina aata hai. Bus ka kiraya nahi hai.'

test('typed account gives suggested facts with their words; worker removes one; result after confirmation', async ({ page, api }) => {
  const id = await createVisit(api, 'adult_cough')
  await page.goto(`/visit/${id}/capture`)
  await page.getByRole('button', { name: 'English' }).click()
  await page.getByTestId('capture-text').fill(ACCOUNT)
  await page.getByTestId('capture-continue').click()
  const duration = page.getByTestId('suggested-cough_duration_days')
  await expect(duration).toContainText('21 days')
  await expect(duration).toContainText('teen hafte se khansi hai')
  await expect(duration).toContainText('suggested')
  await expect(page.getByTestId('suggested-list')).not.toContainText('Blood in sputum')
  await expect(page.getByTestId('concerns-list')).toContainText('Bus ka kiraya nahi hai')
  await expect(page.getByTestId('heard').locator('mark').first()).toBeVisible() // evidence is highlighted
  await page.getByTestId('suggested-night_sweats').getByRole('button', { name: 'Remove' }).click()
  await expect(page.getByTestId('suggested-night_sweats')).toHaveCount(0)
  await page.getByTestId('suggested-continue').click()
  const asked: string[] = []
  page.on('response', async (r) => {
    if (r.url().endsWith('/next-question')) asked.push(((await r.json()) as { fact_key?: string }).fact_key ?? '')
  })
  await answerQuestions(page, { cough_present: 'yes' })
  expect(asked).not.toContain('cough_duration_days')
  expect(asked).toContain('night_sweats') // removed suggestion is asked again
  await confirmFacts(page)
  await expect(page.getByTestId('urgency-band')).toHaveAttribute('data-level', 'MEDIUM')
})

test('when the model output is unusable the visit continues by hand, with no error screen', async ({ page, api }) => {
  const id = await createVisit(api, 'adult_cough')
  await page.goto(`/visit/${id}/capture`)
  await page.getByRole('button', { name: 'English' }).click()
  await page.getByTestId('capture-text').fill('FIXTURE: malformed output')
  await page.getByTestId('capture-continue').click()
  await expect(page.getByTestId('degraded-note')).toBeVisible()
  await answerQuestions(page, { cough_present: 'yes', cough_duration_days: 21 })
  await confirmFacts(page)
  await expect(page.getByTestId('urgency-band')).toHaveAttribute('data-level', 'MEDIUM')
})

test('a slow model offers "Do it by hand", which always works', async ({ page, api }) => {
  const id = await createVisit(api, 'adult_cough')
  await page.route('**/extract', () => {
    /* never answer: simulates a hung model server */
  })
  await page.goto(`/visit/${id}/capture`)
  await page.getByTestId('capture-text').fill('khansi hai')
  await page.getByTestId('capture-continue').click()
  await expect(page.getByTestId('extract-working')).toBeVisible()
  await page.getByTestId('by-hand').click({ timeout: 9000 })
  await expect(page.getByTestId('question-text')).toBeVisible()
})

test('free-text answer is parsed and shown back before it is used', async ({ page, api }) => {
  const id = await createVisit(api, 'adult_cough')
  await api.post(`/api/v1/encounters/${id}/answers`, { data: { fact_key: 'cough_present', value: 'yes' } })
  for (const k of ['rf_breathless', 'rf_altered_consciousness_convulsions_weakness', 'rf_coughing_blood_cup', 'rf_severe_chest_or_abdominal_pain', 'rf_confined_to_bed', 'rf_recurrent_vomiting_diarrhoea']) {
    await api.post(`/api/v1/encounters/${id}/answers`, { data: { fact_key: k, value: 'no' } })
  }
  await page.goto(`/visit/${id}/questions`)
  await page.getByRole('button', { name: 'English' }).click()
  await expect(page.getByTestId('question-text')).toHaveAttribute('data-fact', 'cough_duration_days')
  await page.getByTestId('other-way').locator('summary').click()
  await page.getByTestId('free-answer').fill('teen hafte')
  await page.getByRole('button', { name: 'Check' }).click()
  await expect(page.getByTestId('parsed-answer')).toContainText('21 days')
  await page.getByRole('button', { name: 'Use this answer' }).click()
  await expect(page.getByTestId('question-text')).not.toHaveAttribute('data-fact', 'cough_duration_days')
})
