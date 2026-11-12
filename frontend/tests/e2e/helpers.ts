import { expect, type APIRequestContext, type Page } from '@playwright/test'

export type Answers = Record<string, string | number>

/** Answer every question until the confirm screen, from `answers` or the default. */
export async function answerQuestions(page: Page, answers: Answers, fallback: string | number = 'no') {
  for (let i = 0; i < 60; i++) {
    const question = page.getByTestId('question-text')
    const confirm = page.getByTestId('fact-list')
    const suggested = page.getByTestId('suggested-continue')
    await expect(question.or(confirm).or(suggested)).toBeVisible()
    if (await confirm.isVisible()) return
    if (await suggested.isVisible()) {
      await suggested.click()
      continue
    }
    const fact = (await question.getAttribute('data-fact')) ?? ''
    const value = answers[fact] ?? fallback
    const number = page.getByTestId('answer-number')
    if (await number.isVisible()) {
      if (value === 'unknown') await page.getByTestId('answer-unknown').click()
      else {
        await number.fill(String(typeof value === 'number' ? value : 0))
        await page.getByTestId('answer-submit').click()
      }
    } else {
      await page.getByTestId(`answer-${value}`).click()
    }
    await expect(question.and(page.locator(`[data-fact="${fact}"]`))).toHaveCount(0)
  }
  throw new Error('too many questions')
}

export async function confirmFacts(page: Page) {
  await page.getByTestId('checked-with-family').check()
  await page.getByTestId('confirm-submit').click()
}

export async function createVisit(request: APIRequestContext, pathway: string | null, person: Record<string, unknown> = {}) {
  const p = await (
    await request.post('/api/v1/persons', { data: { name: 'E2E Synthetic', age_years: 45, sex: 'male', synthetic: true, ...person } })
  ).json()
  const e = await (await request.post('/api/v1/encounters', { data: { person_id: p.id, language: 'hi', pathway_id: pathway } })).json()
  return e.id as string
}
