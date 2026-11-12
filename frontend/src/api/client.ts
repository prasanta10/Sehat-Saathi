// Typed API client. Types are generated from the backend's OpenAPI document (`make api-types`).
import { getTokens, setTokens, type Tokens } from '../state/auth'
import type { components } from './schema'

export type Schemas = components['schemas']
export type Encounter = Schemas['EncounterOut']
export type EncounterSummary = Schemas['EncounterSummary']
export type Person = Schemas['PersonOut']
export type PersonIn = Schemas['PersonIn']
export type NextQuestion = Schemas['NextQuestionOut']
export type TriageResult = Schemas['TriageResult']
export type Urgency = TriageResult['urgency']
export type ExtractOut = Schemas['ExtractOut']
export type ParseAnswerOut = Schemas['ParseAnswerOut']
export type AudioCaptureOut = Schemas['AudioCaptureOut']
export type SpokenAnswerOut = Schemas['SpokenAnswerOut']
export type PlanOut = Schemas['PlanOut']
export type OutputOut = Schemas['OutputOut']
export type SchemesOut = Schemas['SchemesOut']
export type SchemeCard = Schemas['SchemeCardOut']
export type ExcerptOut = Schemas['ExcerptOut']

export const API_BASE = '/api/v1'

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
  ) {
    super(`${status} ${code}`)
  }
}

let refreshing: Promise<boolean> | null = null

async function refreshTokens(): Promise<boolean> {
  const t = getTokens()
  if (!t) return false
  refreshing ??= fetch(`${API_BASE}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: t.refresh_token }),
  })
    .then(async (r) => {
      if (!r.ok) throw new Error('refresh failed')
      setTokens((await r.json()) as Tokens)
      return true
    })
    .catch(() => {
      setTokens(null) // back to the login screen; the danger-sign check still works
      return false
    })
    .finally(() => {
      refreshing = null
    })
  return refreshing
}

async function request<T>(method: string, path: string, body?: unknown, signal?: AbortSignal, retried = false): Promise<T> {
  const isForm = body instanceof FormData
  const headers: Record<string, string> = {}
  if (body !== undefined && !isForm) headers['Content-Type'] = 'application/json'
  const token = getTokens()?.access_token
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    signal,
    headers,
    body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
  })
  if (res.status === 401 && !retried && !path.startsWith('/auth/') && (await refreshTokens())) {
    return request<T>(method, path, body, signal, true)
  }
  if (!res.ok) {
    let code = 'http_error'
    try {
      code = ((await res.json()) as { code?: string }).code ?? code
    } catch {
      // not JSON
    }
    throw new ApiError(res.status, code)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export interface Health {
  status: string
  version: string
}

export const api = {
  login: (phone: string, pin: string) => request<Tokens>('POST', '/auth/login', { phone, pin }),
  logout: () => request<void>('POST', '/auth/logout').catch(() => undefined),
  health: (signal?: AbortSignal) => request<Health>('GET', '/healthz', undefined, signal),
  persons: () => request<Person[]>('GET', '/persons'),
  createPerson: (body: PersonIn) => request<Person>('POST', '/persons', body),
  encounters: () => request<EncounterSummary[]>('GET', '/encounters'),
  encounter: (id: string) => request<Encounter>('GET', `/encounters/${id}`),
  createEncounter: (body: Schemas['EncounterCreate']) => request<Encounter>('POST', '/encounters', body),
  patchEncounter: (id: string, body: Schemas['EncounterPatch']) =>
    request<Encounter>('PATCH', `/encounters/${id}`, body),
  captureText: (id: string, text: string) =>
    request<Encounter>('POST', `/encounters/${id}/capture/text`, { text }),
  nextQuestion: (id: string) => request<NextQuestion>('GET', `/encounters/${id}/next-question`),
  answer: (id: string, body: Schemas['AnswerIn']) => request<Encounter>('POST', `/encounters/${id}/answers`, body),
  editFacts: (id: string, body: Schemas['FactsPatch']) => request<Encounter>('PATCH', `/encounters/${id}/facts`, body),
  confirm: (id: string) => request<Encounter>('POST', `/encounters/${id}/confirm`, { checked_with_family: true }),
  triage: (id: string) => request<Encounter>('POST', `/encounters/${id}/triage`),
  extract: (id: string) => request<ExtractOut>('POST', `/encounters/${id}/extract`),
  rejectFact: (id: string, key: string) => request<Encounter>('POST', `/encounters/${id}/facts/${key}/reject`),
  parseAnswer: (id: string, factKey: string, text: string) =>
    request<ParseAnswerOut>('POST', `/encounters/${id}/parse-answer`, { fact_key: factKey, text }),
  consent: (id: string, kind: 'record_audio' | 'store_record' | 'share_handoff', granted: boolean) =>
    request<Schemas['ConsentOut']>('POST', `/encounters/${id}/consents`, { kind, granted }),
  captureAudio: (id: string, blob: Blob) => request<AudioCaptureOut>('POST', `/encounters/${id}/capture/audio`, audioForm(blob)),
  spokenAnswer: (id: string, blob: Blob) => request<SpokenAnswerOut>('POST', `/encounters/${id}/spoken-answer`, audioForm(blob)),
  editTranscript: (id: string, captureId: string, transcript: string) =>
    request<Encounter>('PATCH', `/encounters/${id}/captures/${captureId}`, { transcript }),
  plan: (id: string) => request<PlanOut>('GET', `/encounters/${id}/plan`),
  outputs: (id: string) => request<OutputOut[]>('GET', `/encounters/${id}/outputs`),
  generateOutputs: (id: string) => request<OutputOut[]>('POST', `/encounters/${id}/outputs`),
  editOutput: (id: string, outputId: string, body: string) =>
    request<OutputOut>('PATCH', `/encounters/${id}/outputs/${outputId}`, { body }),
  schemes: (id: string) => request<SchemesOut>('GET', `/encounters/${id}/schemes`),
  searchExcerpts: (q: string) => request<ExcerptOut[]>('GET', `/schemes/search?q=${encodeURIComponent(q)}`),
  patchPerson: (id: string, body: Schemas['PersonPatch']) => request<Person>('PATCH', `/persons/${id}`, body),
  emergency: (id: string, ids: string[]) =>
    request<Encounter>('POST', `/encounters/${id}/emergency`, { danger_sign_ids: ids }),
}

function audioForm(blob: Blob): FormData {
  const form = new FormData()
  const ext = blob.type.includes('mp4') ? 'm4a' : blob.type.includes('ogg') ? 'ogg' : 'webm'
  form.append('audio', blob, `recording.${ext}`)
  return form
}
