'use client'

import type { FormEvent } from 'react'

type DeleteAction = (formData: FormData) => Promise<void>

export function AdminDeleteButton({ action, id, label }: { action: DeleteAction; id: number; label: string }) {
  const confirmDelete = (event: FormEvent<HTMLFormElement>) => {
    if (!window.confirm(`Remove ${label}? This cannot be undone.`)) event.preventDefault()
  }

  return (
    <form action={action} onSubmit={confirmDelete}>
      <input type="hidden" name="id" value={id} />
      <button className="text-xs font-semibold text-red-600 hover:underline">Remove</button>
    </form>
  )
}
