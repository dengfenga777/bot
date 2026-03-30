// 21点游戏相关服务
import { apiClient } from '../main'

// 21点游戏 API
export const getBlackjackConfig = () => {
  return apiClient.get('/api/blackjack/config')
}

export const updateBlackjackConfig = (config) => {
  return apiClient.put('/api/blackjack/config', config)
}

export const startBlackjackGame = (betAmount) => {
  return apiClient.post('/api/blackjack/start', { bet_amount: betAmount })
}

export const hitCard = (gameId) => {
  return apiClient.post('/api/blackjack/hit', { game_id: gameId })
}

export const stand = (gameId) => {
  return apiClient.post('/api/blackjack/stand', { game_id: gameId })
}

export const getBlackjackUserStatus = () => {
  return apiClient.get('/api/blackjack/user-status')
}

// 获取21点统计数据（管理员）
export const getBlackjackStats = async () => {
  try {
    const response = await apiClient.get('/api/blackjack/stats')
    return response
  } catch (error) {
    console.error('获取21点统计失败:', error)
    // 返回默认数据
    return {
      data: {
        total_games: 0,
        total_wins: 0,
        total_losses: 0,
        total_pushes: 0,
        total_blackjacks: 0,
        total_bet_amount: 0.0,
        total_payout_amount: 0.0,
        house_edge: 0.0,
        active_players: 0,
        today_games: 0,
        week_games: 0
      }
    }
  }
}

// 获取用户个人21点活动统计数据
export const getUserBlackjackStats = () => {
  return apiClient.get('/api/blackjack/user-activity-stats')
}
