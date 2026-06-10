import { create } from 'zustand'

import type { EmailResponse } from '@/api/types'
import type { PriorityFilter } from '@/lib/priority'

type EmailState = {
  emails: EmailResponse[]
  selectedEmailId: number | null
  selectedEmail: EmailResponse | null
  detailLoadedEmailId: number | null
  cleanedBody: string | null
  priorityFilter: PriorityFilter
  listLoadedPriority: PriorityFilter | null
  readEmailIds: number[]
  listError: string | null
  detailError: string | null
  setEmails: (emails: EmailResponse[]) => void
  setSelectedEmailId: (id: number | null) => void
  setSelectedEmail: (email: EmailResponse | null) => void
  setDetailLoadedEmailId: (id: number | null) => void
  setCleanedBody: (body: string | null) => void
  setPriorityFilter: (filter: PriorityFilter) => void
  setListLoadedPriority: (filter: PriorityFilter | null) => void
  markAsRead: (id: number) => void
  setListError: (error: string | null) => void
  setDetailError: (error: string | null) => void
  resetDetail: () => void
  reset: () => void
}

const initialState = {
  emails: [] as EmailResponse[],
  selectedEmailId: null as number | null,
  selectedEmail: null as EmailResponse | null,
  detailLoadedEmailId: null as number | null,
  cleanedBody: null as string | null,
  priorityFilter: 'all' as PriorityFilter,
  listLoadedPriority: null as PriorityFilter | null,
  readEmailIds: [] as number[],
  listError: null as string | null,
  detailError: null as string | null,
}

export const useEmailStore = create<EmailState>((set) => ({
  ...initialState,

  setEmails: (emails) => set({ emails }),
  setSelectedEmailId: (id) => set({ selectedEmailId: id }),
  setSelectedEmail: (email) => set({ selectedEmail: email }),
  setDetailLoadedEmailId: (id) => set({ detailLoadedEmailId: id }),
  setCleanedBody: (body) => set({ cleanedBody: body }),
  setPriorityFilter: (filter) => set({ priorityFilter: filter }),
  setListLoadedPriority: (filter) => set({ listLoadedPriority: filter }),
  markAsRead: (id) =>
    set((state) => ({
      readEmailIds: state.readEmailIds.includes(id)
        ? state.readEmailIds
        : [...state.readEmailIds, id],
    })),
  setListError: (error) => set({ listError: error }),
  setDetailError: (error) => set({ detailError: error }),
  resetDetail: () =>
    set({
      selectedEmail: null,
      detailLoadedEmailId: null,
      cleanedBody: null,
      detailError: null,
    }),
  reset: () => set(initialState),
}))
