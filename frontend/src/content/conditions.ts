// Three-valued condition evaluation, mirroring backend/app/rules/conditions.py. Used only to
// suggest which pathways fit a person; the urgency itself always comes from the server's engine.

export type Tri = boolean | null
export type FactValues = Record<string, string | number | boolean | null | undefined>
export type Condition = Record<string, unknown>

function leaf(value: FactValues[string], spec: unknown): Tri {
  if (value === null || value === undefined) return null
  if (spec === null || typeof spec !== 'object' || Array.isArray(spec)) return value === spec
  const results: boolean[] = []
  for (const [op, arg] of Object.entries(spec as Record<string, unknown>)) {
    if (op === 'eq') results.push(value === arg)
    else if (op === 'in') results.push(Array.isArray(arg) && arg.includes(value))
    else if (typeof value !== 'number' || typeof arg !== 'number') return null
    else if (op === 'gte') results.push(value >= arg)
    else if (op === 'lte') results.push(value <= arg)
    else if (op === 'gt') results.push(value > arg)
    else if (op === 'lt') results.push(value < arg)
    else return null
  }
  return results.every(Boolean)
}

function triAll(values: Tri[]): Tri {
  if (values.some((v) => v === false)) return false
  if (values.some((v) => v === null)) return null
  return true
}

function triAny(values: Tri[]): Tri {
  if (values.some((v) => v === true)) return true
  if (values.some((v) => v === null)) return null
  return false
}

export function evaluate(cond: Condition, facts: FactValues): Tri {
  const parts: Tri[] = []
  for (const [key, spec] of Object.entries(cond)) {
    if (key === 'all') parts.push(triAll((spec as Condition[]).map((c) => evaluate(c, facts))))
    else if (key === 'any') parts.push(triAny((spec as Condition[]).map((c) => evaluate(c, facts))))
    else if (key === 'not') {
      const inner = evaluate(spec as Condition, facts)
      parts.push(inner === null ? null : !inner)
    } else parts.push(leaf(facts[key], spec))
  }
  return triAll(parts)
}

interface PersonLike {
  age_years?: number | null
  age_months?: number | null
  sex?: string | null
  pregnant?: string | null
}

/** Person-record facts as the server derives them (``person_fact_values``). */
export function personFacts(p: PersonLike | null | undefined): FactValues {
  if (!p) return {}
  return {
    age_years: p.age_years ?? null,
    age_months: p.age_months ?? null,
    sex: p.sex ?? null,
    pregnant: p.pregnant === 'yes' || p.pregnant === 'no' ? p.pregnant : null,
  }
}

/** Pathways that may fit this person: those whose ``applies_when`` is not ruled out by the
 * person record. Undetermined counts as "may fit" (the worker decides). */
export function fittingPathways<T extends { applies_when: Condition }>(pathways: T[], person: PersonLike | null | undefined): T[] {
  const facts = personFacts(person)
  return pathways.filter((p) => evaluate(p.applies_when, facts) !== false)
}
