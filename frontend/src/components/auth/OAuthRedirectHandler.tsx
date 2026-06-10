import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { fetchAuthUser } from '@/api/auth'
import { useSettingsStore } from '@/store/useSettingsStore'

export default function OAuthRedirectHandler() {
  const location = useLocation()
  const navigate = useNavigate()
  const setUser = useSettingsStore((s) => s.setUser)

  useEffect(() => {
    const params = new URLSearchParams(location.search)
    if (params.get('oauth') !== 'success') {
      return
    }

    void fetchAuthUser()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => {
        params.delete('oauth')
        const search = params.toString()
        navigate(
          { pathname: location.pathname, search: search ? `?${search}` : '' },
          { replace: true },
        )
      })
  }, [location.pathname, location.search, navigate, setUser])

  return null
}
