import { create } from 'zustand'

export type LoadingKey =
  | 'global'
  | 'emails'
  | 'emailDetail'
  | 'tasks'
  | 'followups'
  | 'reply'
  | 'settings'

type LoadingState = Record<LoadingKey, boolean>

type AppState = {
  sidebarCollapsed: boolean
  loading: LoadingState
  setSidebarCollapsed: (collapsed: boolean) => void
  toggleSidebar: () => void
  setLoading: (key: LoadingKey, value: boolean) => void
  isLoading: (key?: LoadingKey) => boolean
}

const initialLoading: LoadingState = {
  global: false,
  emails: false,
  emailDetail: false,
  tasks: false,
  followups: false,
  reply: false,
  settings: false,
}

export const useAppStore = create<AppState>((set, get) => ({
  sidebarCollapsed: false,
  loading: { ...initialLoading },

  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

  toggleSidebar: () =>
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

  setLoading: (key, value) =>
    set((state) => ({
      loading: { ...state.loading, [key]: value },
    })),

  isLoading: (key) => {
    if (!key) {
      return Object.values(get().loading).some(Boolean)
    }
    return get().loading[key]
  },
}))
