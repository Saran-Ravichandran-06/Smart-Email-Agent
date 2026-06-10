import { create } from 'zustand'

import type { FollowUpResponse } from '@/api/types'

type FollowupState = {
  followups: FollowUpResponse[]
  followupsError: string | null
  loaded: boolean
  actionError: string | null
  draftingId: number | null
  resolvingId: number | null
  setFollowups: (followups: FollowUpResponse[]) => void
  setLoaded: (loaded: boolean) => void
  setFollowupsError: (error: string | null) => void
  setActionError: (error: string | null) => void
  setDraftingId: (id: number | null) => void
  setResolvingId: (id: number | null) => void
  updateFollowupInList: (followup: FollowUpResponse) => void
  removeFollowup: (id: number) => void
  getByThreadId: (threadId: string) => FollowUpResponse | undefined
  reset: () => void
}

const initialState = {
  followups: [] as FollowUpResponse[],
  followupsError: null as string | null,
  loaded: false,
  actionError: null as string | null,
  draftingId: null as number | null,
  resolvingId: null as number | null,
}

export const useFollowupStore = create<FollowupState>((set, get) => ({
  ...initialState,

  setFollowups: (followups) => set({ followups }),
  setLoaded: (loaded) => set({ loaded }),
  setFollowupsError: (error) => set({ followupsError: error }),
  setActionError: (error) => set({ actionError: error }),
  setDraftingId: (id) => set({ draftingId: id }),
  setResolvingId: (id) => set({ resolvingId: id }),
  updateFollowupInList: (followup) =>
    set((state) => ({
      followups: state.followups.map((item) =>
        item.id === followup.id ? followup : item,
      ),
    })),
  removeFollowup: (id) =>
    set((state) => ({
      followups: state.followups.filter((item) => item.id !== id),
    })),
  getByThreadId: (threadId) =>
    get().followups.find((item) => item.thread_id === threadId),
  reset: () => set(initialState),
}))
