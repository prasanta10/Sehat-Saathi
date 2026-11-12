import { useMutation, useQueryClient } from '@tanstack/react-query'
import { type ReactNode, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type OutputOut } from '../api/client'

export function OutputCard({ encounterId, output, title, actions }: { encounterId: string; output: OutputOut; title: string; actions?: ReactNode }) {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(output.body)
  const save = useMutation({
    mutationFn: () => api.editOutput(encounterId, output.id, draft),
    onSuccess: () => {
      setEditing(false)
      return qc.invalidateQueries({ queryKey: ['outputs', encounterId] })
    },
  })
  return (
    <section className="flex flex-col gap-2 rounded-2xl border border-ink/10 bg-paper p-4 shadow-sm" data-testid={`output-${output.kind}`}>
      <h2 className="text-xl font-bold">
        {title}
        {output.edited_by_worker && <span className="ml-2 text-base font-normal">({t('outputs.edited')})</span>}
      </h2>
      {editing ? (
        <textarea className="min-h-48 w-full rounded-lg border-2 border-ink/40 p-2 text-lg" value={draft} onChange={(e) => setDraft(e.target.value)} />
      ) : (
        <p lang={output.language} className="whitespace-pre-line">
          {output.body}
        </p>
      )}
      <div className="flex flex-col gap-2">
        {actions}
        {editing ? (
          <button type="button" onClick={() => save.mutate()} className="min-h-12 rounded-xl bg-brand px-4 font-bold text-white">
            {t('outputs.save')}
          </button>
        ) : (
          <button type="button" onClick={() => setEditing(true)} className="min-h-12 rounded-xl border-2 border-ink/40 px-4 font-semibold">
            {t('outputs.edit')}
          </button>
        )}
      </div>
    </section>
  )
}
