// Session tokens. The access token is short-lived; the refresh token rotates on every use.
// Phase 8 moves them into encrypted IndexedDB with the offline store.
import { useSyncExternalStore } from 'react'

export interface Tokens {
  access_token: string
  refresh_token: string
}
const KEY = 'sehat.auth'
const listeners = new Set<() => void>()

function read(): Tokens | null {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? (JSON.parse(raw) as Tokens) : null
  } catch {
    return null
  }
}
let current: Tokens | null = read()

export function getTokens(): Tokens | null {
  return current
}

export function setTokens(t: Tokens | null): void {
  current = t
  try {
    if (t) localStorage.setItem(KEY, JSON.stringify(t))
    else localStorage.removeItem(KEY)
  } catch {
    // storage unavailable: tokens live in memory for this tab only
  }
  listeners.forEach((l) => l())
}

export function useLoggedIn(): boolean {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l)
      return () => listeners.delete(l)
    },
    () => current !== null,
  )
}
