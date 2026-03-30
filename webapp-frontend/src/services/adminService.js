import { apiClient } from '../main';

/**
 * 获取管理员设置
 * @returns {Promise} 管理员设置数据
 */
export async function getAdminSettings() {
  try {
    const response = await apiClient.get('/api/admin/settings');
    return response;
  } catch (error) {
    console.error('获取管理员设置失败:', error);
    throw error;
  }
}

/**
 * 设置 Plex 注册状态
 * @param {boolean} enabled - 是否开启注册
 * @returns {Promise} 设置结果
 */
export async function setPlexRegister(enabled) {
  try {
    const response = await apiClient.post('/api/admin/settings/plex-register', {
      enabled: enabled
    });
    return response;
  } catch (error) {
    console.error('设置 Plex 注册状态失败:', error);
    throw error;
  }
}

/**
 * 设置 Emby 注册状态
 * @param {boolean} enabled - 是否开启注册
 * @returns {Promise} 设置结果
 */
export async function setEmbyRegister(enabled) {
  try {
    const response = await apiClient.post('/api/admin/settings/emby-register', {
      enabled: enabled
    });
    return response;
  } catch (error) {
    console.error('设置 Emby 注册状态失败:', error);
    throw error;
  }
}

/**
 * 设置高级线路免费使用状态（通用，同时支持Plex和Emby）
 * @param {boolean} enabled - 是否开启高级线路免费使用
 * @returns {Promise} 设置结果
 */
export async function setPremiumFree(enabled) {
  try {
    const response = await apiClient.post('/api/admin/settings/premium-free', {
      enabled: enabled
    });
    return response;
  } catch (error) {
    console.error('设置高级线路免费使用状态失败:', error);
    throw error;
  }
}

/**
 * 设置免费的高级线路列表（通用，同时支持Plex和Emby）
 * @param {Array} freeLines - 免费高级线路列表
 * @returns {Promise} 设置结果
 */
export async function setFreePremiumLines(freeLines) {
  try {
    const response = await apiClient.post('/api/admin/settings/free-premium-lines', {
      free_lines: freeLines
    });
    return response;
  } catch (error) {
    console.error('设置免费高级线路列表失败:', error);
    throw error;
  }
}

/**
 * 设置 Emby 高级线路免费使用状态（兼容性接口，推荐使用 setPremiumFree）
 * @param {boolean} enabled - 是否开启高级线路免费使用
 * @returns {Promise} 设置结果
 */
export async function setEmbyPremiumFree(enabled) {
  try {
    const response = await apiClient.post('/api/admin/settings/emby-premium-free', {
      enabled: enabled
    });
    return response;
  } catch (error) {
    console.error('设置 Emby 高级线路免费使用状态失败:', error);
    throw error;
  }
}

/**
 * 设置免费的 Emby 高级线路列表（兼容性接口，推荐使用 setFreePremiumLines）
 * @param {Array} freeLines - 免费高级线路列表
 * @returns {Promise} 设置结果
 */
export async function setEmbyFreePremiumLines(freeLines) {
  try {
    const response = await apiClient.post('/api/admin/settings/emby-free-premium-lines', {
      free_lines: freeLines
    });
    return response;
  } catch (error) {
    console.error('设置免费高级线路列表失败:', error);
    throw error;
  }
}

/**
 * 提交捐赠记录
 * @param {Object} donationData - 捐赠数据
 * @returns {Promise} 提交结果
 */
export async function submitDonationRecord(donationData) {
  try {
    const response = await apiClient.post('/api/admin/donation', donationData);
    return response.data;
  } catch (error) {
    console.error('提交捐赠记录失败:', error);
    throw error;
  }
}

/**
 * 设置邀请码生成所需积分
 * @param {number} credits - 积分数量
 * @returns {Promise} 设置结果
 */
export async function setInvitationCredits(credits) {
  try {
    const response = await apiClient.post('/api/admin/settings/invitation-credits', {
      credits: credits
    });
    return response;
  } catch (error) {
    console.error('设置邀请码积分失败:', error);
    throw error;
  }
}

/**
 * 设置解锁NSFW所需积分
 * @param {number} credits - 积分数量
 * @returns {Promise} 设置结果
 */
export async function setUnlockCredits(credits) {
  try {
    const response = await apiClient.post('/api/admin/settings/unlock-credits', {
      credits: credits
    });
    return response;
  } catch (error) {
    console.error('设置解锁积分失败:', error);
    throw error;
  }
}

/**
 * 管理员生成邀请码
 * @param {Object} requestData - 生成邀请码的数据
 * @param {number} requestData.tg_id - 目标用户ID
 * @param {number} requestData.count - 生成数量
 * @param {boolean} requestData.is_premium - 是否是特权邀请码
 * @param {string} requestData.note - 备注信息
 * @returns {Promise} 生成结果
 */
export async function generateAdminInviteCodes(requestData) {
  try {
    const response = await apiClient.post('/api/admin/invite-codes/generate', requestData);
    return response.data;
  } catch (error) {
    console.error('生成邀请码失败:', error);
    throw error;
  }
}

/**
 * 设置解锁Premium每日所需积分
 * @param {number} credits - 积分数量
 * @returns {Promise} 设置结果
 */
export async function setPremiumDailyCredits(credits) {
  try {
    const response = await apiClient.post('/api/admin/settings/premium-daily-credits', {
      credits: credits
    });
    return response;
  } catch (error) {
    console.error('设置Premium每日积分失败:', error);
    throw error;
  }
}

/**
 * 设置 Premium 解锁开放状态
 * @param {boolean} enabled - 是否开放 Premium 解锁
 * @returns {Promise} 设置结果
 */
export async function setPremiumUnlockEnabled(enabled) {
  try {
    const response = await apiClient.post('/api/admin/settings/premium-unlock-enabled', {
      enabled: enabled
    });
    return response;
  } catch (error) {
    console.error('设置 Premium 解锁开放状态失败:', error);
    throw error;
  }
}

/**
 * 设置积分转移功能开关
 * @param {boolean} enabled - 是否开启积分转移功能
 * @returns {Promise} 设置结果
 */
export async function setCreditsTransferEnabled(enabled) {
  try {
    const response = await apiClient.post('/api/admin/settings/credits-transfer-enabled', {
      enabled: enabled
    });
    return response;
  } catch (error) {
    console.error('设置积分转移功能状态失败:', error);
    throw error;
  }
}

/**
 * 更换用户的TG绑定
 * @param {Object} bindingData - 换绑数据
 * @param {number} [bindingData.old_tg_id] - 原 TG ID
 * @param {string} [bindingData.plex_email] - 可选：Plex 邮箱
 * @param {string} [bindingData.plex_username] - 可选：Plex 用户名
 * @param {string} [bindingData.emby_username] - 可选：Emby 用户名
 * @param {number} bindingData.new_tg_id - 新的 TG ID
 * @param {string} bindingData.note - 备注信息（可选）
 * @returns {Promise} 换绑结果
 */
export async function changeTgBinding(bindingData) {
  try {
    const response = await apiClient.post('/api/admin/change-tg-binding', bindingData);
    return response.data;
  } catch (error) {
    console.error('更换TG绑定失败:', error);
    throw error;
  }
}
