import { apiClient } from '@/main';

/**
 * 所有线路流量统计服务
 */

/**
 * 获取所有线路（普通+高级）的流量统计
 * @returns {Promise<Object>} 流量统计数据
 */
export async function getAllLinesTrafficStats() {
  try {
    const response = await apiClient.get('/api/system/all-lines-traffic-stats');
    return response.data;
  } catch (error) {
    console.error('获取所有线路流量统计失败:', error);
    throw error;
  }
}

/**
 * 获取线路切换历史记录
 * @param {number} limit - 返回记录数量限制
 * @returns {Promise<Object>} 历史记录数据
 */
export async function getLineSwitchHistory(limit = 10) {
  try {
    const response = await apiClient.get('/api/system/line-switch-history', {
      params: { limit }
    });
    return response.data;
  } catch (error) {
    console.error('获取线路切换历史失败:', error);
    throw error;
  }
}

/**
 * 格式化流量大小显示
 * @param {number} bytes - 字节数
 * @returns {string} 格式化后的流量大小
 */
export function formatTrafficSize(bytes) {
  if (!bytes || bytes === 0) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + units[i];
}

/**
 * 格式化时间戳
 * @param {number} timestamp - Unix时间戳
 * @returns {string} 格式化后的时间
 */
export function formatTimestamp(timestamp) {
  if (!timestamp) return '';

  const date = new Date(timestamp * 1000);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');

  return `${year}-${month}-${day} ${hours}:${minutes}`;
}
