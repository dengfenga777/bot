/**
 * 主题配置服务
 */
import { apiClient } from '@/main'

/**
 * 获取主题配置
 */
export async function getThemeConfig() {
  return apiClient.get('/api/theme/config')
}

/**
 * 更新主题配置
 * @param {Object} config - 主题配置对象
 */
export async function updateThemeConfig(config) {
  return apiClient.post('/api/theme/config', config)
}

/**
 * 重置主题配置为默认值
 */
export async function resetThemeConfig() {
  return apiClient.post('/api/theme/reset')
}
