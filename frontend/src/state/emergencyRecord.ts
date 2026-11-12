// Status of recording an emergency on the server. The emergency screen never waits for it.
import { useSyncExternalStore } from 'react'

export type RecordStatus = 'none' | 'pending' | 'ok' | 'failed'
let status: RecordStatus = 'none'
const listeners = new Set<() => void>()

export function setRecordStatus(s: RecordStatus): void {
  status = s
  listeners.forEach((l) => l())
}

export function useRecordStatus(): RecordStatus {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l)
      return () => listeners.delete(l)
    },
    () => status,
  )
}
