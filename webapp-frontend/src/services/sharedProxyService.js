import { apiClient } from '@/main'

export async function getSharedProxy() {
  const response = await apiClient.get('/api/user/shared-proxy')
  return response.data
}

export async function saveSharedProxy(domain) {
  const response = await apiClient.post('/api/user/shared-proxy', { domain })
  return response.data
}

export async function enableSharedProxy() {
  const response = await apiClient.post('/api/user/shared-proxy/enable')
  return response.data
}

export async function disableSharedProxy() {
  const response = await apiClient.post('/api/user/shared-proxy/disable')
  return response.data
}
