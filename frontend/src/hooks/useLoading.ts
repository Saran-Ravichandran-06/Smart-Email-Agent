import { useCallback } from 'react'

import { useAppStore, type LoadingKey } from '@/store/useAppStore'

export function useLoading(key: LoadingKey) {
  const loading = useAppStore((state) => state.loading[key])
  const setLoading = useAppStore((state) => state.setLoading)

  const start = useCallback(() => setLoading(key, true), [key, setLoading])
  const stop = useCallback(() => setLoading(key, false), [key, setLoading])

  return { loading, start, stop }
}
