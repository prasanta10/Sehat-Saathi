import { describe, expect, it } from 'vitest'

import { evaluate, fittingPathways } from '../../src/content/conditions'

describe('condition evaluation (mirrors the server)', () => {
  it('is undetermined when a needed fact is unknown, never false', () => {
    expect(evaluate({ age_years: { gte: 18 } }, {})).toBeNull()
    expect(evaluate({ age_years: { gte: 18 }, cough_present: 'yes' }, { age_years: 40 })).toBeNull()
  })
  it('is false as soon as one known fact rules it out', () => {
    expect(evaluate({ age_years: { gte: 18 }, cough_present: 'yes' }, { age_years: 3 })).toBe(false)
  })
  it('handles all / any / not', () => {
    const c = { all: [{ age_years: { lt: 5 } }, { age_months: { gte: 2 } }] }
    expect(evaluate(c, { age_years: 1, age_months: 14 })).toBe(true)
    expect(evaluate(c, { age_years: 0, age_months: 1 })).toBe(false)
    expect(evaluate(c, { age_years: 30 })).toBe(false)
    expect(evaluate({ any: [{ sex: 'female' }, { pregnant: 'yes' }] }, { sex: 'male' })).toBeNull()
    expect(evaluate({ not: { sex: 'male' } }, { sex: 'female' })).toBe(true)
  })
})

describe('fittingPathways', () => {
  const pathways = [
    { id: 'adult', applies_when: { age_years: { gte: 18 }, cough_present: 'yes' } },
    { id: 'child', applies_when: { all: [{ age_years: { lt: 5 } }, { age_months: { gte: 2 } }] } },
    { id: 'pregnancy', applies_when: { sex: 'female', pregnant: 'yes' } },
  ]
  const ids = (p: { age_years?: number | null; age_months?: number | null; sex?: string | null; pregnant?: string | null }) =>
    fittingPathways(pathways, p).map((x) => x.id)

  it('offers only what the person record does not rule out', () => {
    expect(ids({ age_years: 45, sex: 'male', pregnant: 'unknown' })).toEqual(['adult'])
    expect(ids({ age_years: 2, age_months: 26, sex: 'male' })).toEqual(['child'])
    expect(ids({ age_years: 24, sex: 'female', pregnant: 'yes' })).toEqual(['adult', 'pregnancy'])
  })
  it('keeps a pathway when the record cannot decide', () => {
    expect(ids({})).toEqual(['adult', 'child', 'pregnancy'])
  })
})
