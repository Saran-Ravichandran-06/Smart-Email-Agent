import { create } from 'zustand'
import { persist } from 'zustand/middleware'

import type { AuthUserResponse, ReplyTone } from '@/api/types'

type SettingsState = {
  defaultReplyTone: ReplyTone
  user: AuthUserResponse | null
  setDefaultReplyTone: (tone: ReplyTone) => void
  setUser: (user: AuthUserResponse | null) => void
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      defaultReplyTone: 'neutral',
      user: null,

      setDefaultReplyTone: (tone) => set({ defaultReplyTone: tone }),
      setUser: (user) => set({ user }),
    }),
    {
      name: 'email-agent-settings',
      partialize: (state) => ({ defaultReplyTone: state.defaultReplyTone }),
    },
  ),
)
