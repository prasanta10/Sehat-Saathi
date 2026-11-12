import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import en from '../../src/i18n/en.json'
import { setLanguage } from '../../src/i18n'
import { renderAt, stubFetch } from './render'

const LEVELS = ['EMERGENCY', 'HIGH', 'MEDIUM', 'LOW', 'INCOMPLETE'] as const

function encounter(urgency: string, review = 'draft') {
  return {
    id: 'e1',
    status: 'triaged',
    language: 'en',
    pathway_id: 'adult_cough',
    pathway_version: '0.1.0',
    created_at: '2026-01-01T00:00:00Z',
    person: { id: 'p', name: 'Synthetic', age_years: 40, age_months: null, sex: 'female', village: null, pregnant: 'unknown', synthetic: true },
    facts: [],
    captures: [],
    triage: {
      id: 't',
      created_at: '2026-01-01T00:00:00Z',
      result: {
        urgency,
        reason: urgency === 'INCOMPLETE' ? 'missing_facts' : 'rule',
        fired:
          urgency === 'INCOMPLETE'
            ? []
            : [
                {
                  id: 'cough.two_weeks_or_more',
                  kind: 'rule',
                  level: urgency,
                  text: { en: 'Cough for 2 weeks or more needs a TB test.', hi: 'x' },
                  sources: [{ ref: 'ntep_training_modules_1to4', locator: 'Module 2, p. 23 (pdf 39), Definitions: Presumptive Pulmonary TB' }],
                },
              ],
        missing_fact_keys: urgency === 'INCOMPLETE' ? ['night_sweats'] : [],
        minimum_level: null,
        facility_level: 'PHC',
        target_window: 'within_24_hours',
        return_precautions: null,
        pathway_id: 'adult_cough',
        pathway_version: '0.1.0',
        ruleset_version: 'sha256:x',
        review_status: review,
      },
    },
  }
}

describe('alert screen', () => {
  afterEach(() => vi.unstubAllGlobals())

  it.each(LEVELS)('%s shows colour, icon and word', async (level) => {
    setLanguage('en')
    stubFetch(() => encounter(level))
    renderAt('/visit/e1/alert')
    const band = await screen.findByTestId('urgency-band')
    expect(band).toHaveAttribute('data-level', level)
    expect(band).toHaveTextContent(en.urgency[level])
    expect(band.querySelector('[aria-hidden="true"]')?.textContent).toBeTruthy()
  })

  it('shows the demonstration banner for draft content, and the source on Why?', async () => {
    setLanguage('en')
    stubFetch(() => encounter('MEDIUM'))
    renderAt('/visit/e1/alert')
    expect(await screen.findByTestId('draft-banner')).toHaveTextContent(en.draft_banner)
    expect(screen.getByTestId('why')).toHaveTextContent('Training Modules (1-4)')
    expect(screen.getByTestId('why')).toHaveTextContent('cough for 2 weeks or more')
  })

  it('hides the banner only for reviewed content', async () => {
    setLanguage('en')
    stubFetch(() => encounter('MEDIUM', 'clinician_reviewed'))
    renderAt('/visit/e1/alert')
    await screen.findByTestId('urgency-band')
    expect(screen.queryByTestId('draft-banner')).toBeNull()
  })

  it('lists missing facts for INCOMPLETE', async () => {
    setLanguage('en')
    stubFetch(() => encounter('INCOMPLETE'))
    renderAt('/visit/e1/alert')
    expect(await screen.findByTestId('missing-list')).toHaveTextContent('Sweating at night')
  })
})
