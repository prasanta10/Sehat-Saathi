import { expect, test } from '../fixtures'

import { createVisit } from '../helpers'

test('record with consent → editable transcript → suggested facts (mock ASR)', async ({ page, api }) => {
  const id = await createVisit(api, 'adult_cough')
  await page.goto(`/visit/${id}/capture`)
  await page.getByTestId('consent-yes').click()
  await page.getByTestId('record').click()
  await expect(page.getByRole('meter')).toBeVisible()
  await page.waitForTimeout(2000)
  await page.getByTestId('record').click()
  const transcript = page.getByTestId('capture-text')
  await expect(transcript).toHaveValue(/\[mock ASR\]/)
  await transcript.fill('तीन हफ़्ते से खांसी है, बुखार नहीं है।') // worker corrects the transcript
  await page.getByTestId('capture-continue').click()
  await expect(page.getByTestId('suggested-cough_duration_days')).toContainText('21')
  const enc = await (await api.get(`/api/v1/encounters/${id}`)).json()
  expect(enc.captures[0].kind).toBe('audio')
  expect(enc.captures[0].transcript_original).toMatch(/\[mock ASR\]/)
  expect(enc.captures[0].transcript).toBe('तीन हफ़्ते से खांसी है, बुखार नहीं है।')
})

test('declining audio consent leads cleanly to typing', async ({ page, api }) => {
  const id = await createVisit(api, 'adult_cough')
  await page.goto(`/visit/${id}/capture`)
  await page.getByTestId('consent-no').click()
  await expect(page.getByTestId('record')).toHaveCount(0)
  await page.getByTestId('capture-text').fill('khansi do din se')
  await page.getByTestId('capture-continue').click()
  await expect(page.getByTestId('suggested-cough_duration_days')).toContainText('2')
})

test('a spoken answer is transcribed, parsed and shown back before use', async ({ page, api }) => {
  const id = await createVisit(api, 'adult_cough')
  await api.post(`/api/v1/encounters/${id}/consents`, { data: { kind: 'record_audio', granted: true } })
  await page.goto(`/visit/${id}/questions`)
  await page.getByTestId('other-way').locator('summary').click()
  await page.getByTestId('speak-answer').click()
  await page.waitForTimeout(1500)
  await page.getByTestId('speak-answer').click()
  // The mock transcript is a full sentence, not a yes/no: shown in the box, not silently used.
  await expect(page.getByTestId('free-answer')).toHaveValue(/\[mock ASR\]/)
})
