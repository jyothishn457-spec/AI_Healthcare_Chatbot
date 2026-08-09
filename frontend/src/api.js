import axios from 'axios'

// In development the Vite proxy serves /api; in production set
// VITE_API_URL to the deployed backend base URL (e.g. https://api.example.com).
const baseURL = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({ baseURL })

// Store the session credentials once (helpers used by auth pages).
export const saveSession = (data) => {
  localStorage.setItem('accessToken', data.access_token || data.token)
  localStorage.setItem('refreshToken', data.refresh_token || '')
  localStorage.setItem('user', JSON.stringify(data.user))
}

export const clearSession = () => {
  localStorage.removeItem('accessToken')
  localStorage.removeItem('refreshToken')
  localStorage.removeItem('user')
}

// Attach the saved JWT to every outgoing request.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('accessToken')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// If the access token expires, try to refresh it with the refresh token
// before giving up. This keeps long sessions alive transparently.
api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config
    const isAuthCall = original?.url?.includes('/login') || original?.url?.includes('/register')

    if (err.response?.status === 401 && !original?._retry && !isAuthCall) {
      original._retry = true
      const refreshToken = localStorage.getItem('refreshToken')
      if (refreshToken) {
        try {
          const { data } = await axios.post(`${baseURL}/refresh`, { refresh_token: refreshToken })
          localStorage.setItem('accessToken', data.access_token)
          localStorage.setItem('refreshToken', data.refresh_token)
          original.headers.Authorization = `Bearer ${data.access_token}`
          return api(original)
        } catch (_) {
          /* refresh failed - fall through to clearing the session */
        }
      }
    }

    if (err.response?.status === 401) {
      clearSession()
    }
    return Promise.reject(err)
  },
)

export default api
