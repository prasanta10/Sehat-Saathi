import { expect, test } from '../fixtures'

import { answerQuestions, confirmFacts, createVisit } from '../helpers'

async function mediumVisit(page: import('@playwright/test').Page, api: import('@playwright/test').APIRequestContext) {
  const id = await createVisit(api, 'adult_cough', { name: 'Synthetic Kamla Devi', village: 'Rampur', sex: 'female', age_years: 62 })
  await page.goto(`/visit/${id}/capture`)
  await page.getByTestId('consent-no').click()
  await page.getByTestId('capture-continue').click()
  await answerQuestions(page, { cough_present: 'yes', cough_duration_days: 21 })
  await confirmFacts(page)
  await page.getByTestId('to-plan').click()
  return id
}

test('plan shows family instructions in Hindi and the clinician note, both from templates', async ({ page, api }) => {
  await mediumVisit(page, api)
  const family = page.getByTestId('output-family_instructions')
  await expect(family).toContainText('प्राथमिक स्वास्थ्य केंद्र')
  await expect(family).toContainText('24 घंटे के अंदर')
  await expect(family).toContainText('यह निदान नहीं है')
  await expect(page.getByTestId('read-aloud')).toBeVisible()
  const note = page.getByTestId('output-clinician_handoff')
  await expect(note).toContainText('Synthetic Kamla Devi')
  await expect(note).toContainText('cough.two_weeks_or_more')
  await expect(note).toContainText('Demonstration pathway — not clinically validated')
})

test('clinician handoff prints on one page', async ({ page, api }) => {
  const id = await mediumVisit(page, api)
  await page.goto(`/visit/${id}/handoff`)
  await expect(page.getByTestId('handoff-print')).toContainText('Referral note')
  const pdf = await page.pdf({ format: 'A4', margin: { top: '12mm', bottom: '12mm', left: '12mm', right: '12mm' } })
  const pages = (pdf.toString('latin1').match(/\/Type\s*\/Page[^s]/g) ?? []).length
  expect(pages).toBe(1)
})

test('worker can edit the family instructions', async ({ page, api }) => {
  await mediumVisit(page, api)
  const family = page.getByTestId('output-family_instructions')
  await family.getByRole('button', { name: 'लिखी बात बदलें' }).click()
  await family.locator('textarea').fill('आज ही प्राथमिक स्वास्थ्य केंद्र जाएँ। (संपादित)')
  await family.getByRole('button', { name: 'बदलाव सहेजें' }).click()
  await expect(family).toContainText('(संपादित)')
  await expect(family).toContainText('आपने बदला')
})

test('pre-generated emergency audio is served with the app', async ({ api }) => {
  for (const lang of ['hi', 'en']) {
    const r = await api.get(`/audio/emergency_${lang}.mp3`)
    expect(r.status()).toBe(200)
    expect((await r.body()).length).toBeGreaterThan(10_000)
  }
})
