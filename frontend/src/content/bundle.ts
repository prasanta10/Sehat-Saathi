// Typed access to the content bundle generated from rules/ and knowledge/ (`make bundle`).
// It ships inside the app so the danger-sign check works with no network.
import { useQuery } from '@tanstack/react-query'

import raw from './bundle.json'

export interface I18nText {
  en: string
  hi: string
}
export interface SourceRef {
  ref: string
  locator: string
}
export interface FactSpec {
  key: string
  type: 'tristate' | 'number' | 'enum'
  label: I18nText
  group: string
  unit: string | null
  min: number | null
  max: number | null
  integer: boolean
  values: string[]
  value_labels: Record<string, I18nText>
}
export interface DangerSign {
  id: string
  fact: string
  group: 'general' | 'child' | 'newborn' | 'pregnancy'
  label: I18nText
  pictogram: string
  sources: SourceRef[]
}
export interface Question {
  fact: string
  required: boolean
  ask: I18nText
  options: string[]
  input: string | null
}
export interface Pathway {
  id: string
  version: string
  title: I18nText
  review: { status: 'draft' | 'clinician_reviewed' }
  questions: Question[]
  referral: { bring: string[] }
}
export interface Reference {
  id: string
  title: string
  publisher: string
  url: string
  version_or_date: string
  retrieved_on: string
  excerpts: { locator: string; text: string }[]
}
export interface Bundle {
  ruleset_version: string
  facts: Record<string, FactSpec>
  danger_signs: { version: string; review: { status: string }; signs: DangerSign[] }
  pathways: Record<string, Pathway>
  references: Record<string, Reference>
}

export const bundle = raw as unknown as Bundle

export const DANGER_GROUPS = ['general', 'pregnancy', 'newborn', 'child'] as const

function isBundle(x: unknown): x is Bundle {
  const b = x as Bundle
  return !!b && typeof b === 'object' && Array.isArray(b.danger_signs?.signs) && !!b.facts && !!b.pathways
}

async function fetchBundle(): Promise<Bundle> {
  const res = await fetch('/api/v1/content/bundle')
  const data: unknown = await res.json()
  if (!res.ok || !isBundle(data)) throw new Error('invalid content bundle')
  return data
}

/**
 * Current content: the server's bundle when reachable, otherwise the copy compiled into the app.
 * The compiled copy is available immediately, so the danger-sign check never waits.
 */
export function useBundle(): Bundle {
  const { data } = useQuery({
    queryKey: ['content-bundle'],
    queryFn: fetchBundle,
    initialData: bundle,
    initialDataUpdatedAt: 0,
    staleTime: 5 * 60_000,
    retry: false,
  })
  return data
}
