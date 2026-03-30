import { apiClient } from '../main';

/**
 * 获取系统状态信息
 * @returns {Promise} 系统状态数据
 */
export async function getSystemStatus() {
  try {
    const response = await apiClient.get('/api/system/status');
    return response.data;
  } catch (error) {
    console.error('获取系统状态失败:', error);
    throw error;
  }
}

/**
 * 获取特权用户列表
 * @returns {Promise} 特权用户列表
 */
export async function getPrivilegedUsers() {
  try {
    const response = await apiClient.get('/api/system/privileged-users');
    return response.data;
  } catch (error) {
    console.error('获取特权用户列表失败:', error);
    throw error;
  }
}

/**
 * 添加特权用户
 * @param {number} tgId - Telegram用户ID
 * @returns {Promise} 添加结果
 */
export async function addPrivilegedUser(tgId) {
  try {
    const response = await apiClient.post('/api/system/privileged-users', {
      tg_id: tgId
    });
    return response.data;
  } catch (error) {
    console.error('添加特权用户失败:', error);
    throw error;
  }
}

/**
 * 删除特权用户
 * @param {number} tgId - Telegram用户ID
 * @returns {Promise} 删除结果
 */
export async function removePrivilegedUser(tgId) {
  try {
    const response = await apiClient.delete(`/api/system/privileged-users/${tgId}`);
    return response.data;
  } catch (error) {
    console.error('删除特权用户失败:', error);
    throw error;
  }
}
