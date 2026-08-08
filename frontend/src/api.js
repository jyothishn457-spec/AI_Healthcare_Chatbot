import axios from 'axios'

// In development the Vite proxy serves /api; in production set
// VITE_API_URL to the deployed backend base URL (e.g. https://api.example.com).
const baseURL = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({ baseURL })

// Attach the saved JWT to every outgoing request.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// If the token expires, clear the session so the user is sent back to login.
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    }
    return Promise.reject(err)
  },
)

export default api
