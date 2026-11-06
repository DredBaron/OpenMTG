import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      const token = localStorage.getItem('token')
      if (token) {
        localStorage.removeItem('token')
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)

// 403 means "not allowed", e.g. a feature an admin has switched off. Unlike 401 it must not log
// the user out, and retrying will not help.
export const isForbidden = (err) => err?.response?.status === 403
export const retryUnlessForbidden = (failureCount, err) => !isForbidden(err) && failureCount < 3

export default api
