import { useQuery } from '@tanstack/react-query'

import { api, type OutputOut } from '../api/client'

/** Current outputs for the visit, generated on first use (templates always work). */
export function useOutputs(encounterId: string) {
  return useQuery({
    queryKey: ['outputs', encounterId],
    queryFn: async (): Promise<OutputOut[]> => {
      const existing = await api.outputs(encounterId)
      return existing.length > 0 ? existing : api.generateOutputs(encounterId)
    },
  })
}
