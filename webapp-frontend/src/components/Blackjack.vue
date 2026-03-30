<template>
  <div class="blackjack-container">
    <!-- 游戏标题 -->
    <div class="game-header">
      <h2 class="game-title">
        <v-icon color="red-darken-2" size="28">mdi-cards-playing</v-icon>
        21点游戏
      </h2>
      <v-chip v-if="!gameEnabled" color="error" size="small">
        <v-icon start size="16">mdi-cancel</v-icon>
        游戏未开放
      </v-chip>
    </div>

    <!-- 当前积分和状态 -->
    <v-card class="status-card mb-4" variant="tonal">
      <v-card-text>
        <div class="d-flex justify-space-between align-center">
          <div>
            <div class="text-caption text-medium-emphasis">当前积分</div>
            <div class="text-h5 font-weight-bold text-primary">{{ currentCredits.toFixed(2) }}</div>
          </div>
          <div v-if="gameState">
            <div class="text-caption text-medium-emphasis">下注金额</div>
            <div class="text-h6 font-weight-bold text-success">{{ gameState.bet_amount }}</div>
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- 游戏区域 -->
    <div v-if="!gameState" class="betting-area">
      <!-- 下注界面 -->
      <v-card class="betting-card">
        <v-card-title class="text-center">
          <v-icon start color="orange-darken-2">mdi-poker-chip</v-icon>
          下注
        </v-card-title>
        <v-card-text>
          <div class="text-center mb-4">
            <div class="text-caption text-medium-emphasis mb-2">
              下注范围: {{ minBet }} - {{ maxBet }} 积分
            </div>
            <v-text-field
              v-model.number="betAmount"
              type="number"
              label="下注金额"
              variant="outlined"
              density="comfortable"
              :min="minBet"
              :max="maxBet"
              :disabled="loading || !gameEnabled"
              @keyup.enter="startGame"
            >
              <template v-slot:prepend-inner>
                <v-icon>mdi-currency-usd</v-icon>
              </template>
            </v-text-field>
          </div>

          <!-- 快捷下注按钮 -->
          <div class="quick-bet-buttons mb-4">
            <v-btn
              v-for="amount in [10, 50, 100, 500]"
              :key="amount"
              size="small"
              variant="outlined"
              color="primary"
              @click="betAmount = amount"
              :disabled="loading || !gameEnabled || amount > currentCredits"
            >
              {{ amount }}
            </v-btn>
          </div>

          <v-btn
            block
            size="large"
            color="success"
            :loading="loading"
            :disabled="!canBet || !gameEnabled"
            @click="startGame"
          >
            <v-icon start>mdi-play</v-icon>
            开始游戏
          </v-btn>
        </v-card-text>
      </v-card>
    </div>

    <!-- 游戏进行中 -->
    <div v-else class="game-area">
      <!-- 庄家区域 -->
      <v-card class="dealer-area mb-4" variant="tonal" color="deep-purple">
        <v-card-title class="text-center text-white">
          <v-icon start color="white">mdi-account-tie</v-icon>
          庄家
          <v-chip
            v-if="!gameState.dealer_hidden_card"
            class="ml-2"
            size="small"
            color="white"
            variant="flat"
          >
            {{ gameState.dealer_score }} 点
          </v-chip>
        </v-card-title>
        <v-card-text class="text-center">
          <div class="cards-container">
            <div
              v-for="(card, index) in gameState.dealer_hand"
              :key="`dealer-${index}`"
              class="card"
              :class="{ 'hidden-card': index === 1 && gameState.dealer_hidden_card }"
            >
              <div v-if="index === 1 && gameState.dealer_hidden_card" class="card-back">
                <v-icon size="48" color="white">mdi-card-outline</v-icon>
              </div>
              <div v-else class="card-front">
                <div class="card-rank" :class="getCardColor(card.suit)">{{ card.rank }}</div>
                <div class="card-suit" :class="getCardColor(card.suit)">{{ card.suit }}</div>
              </div>
            </div>
          </div>
        </v-card-text>
      </v-card>

      <!-- VS 分隔 -->
      <div class="vs-divider my-4">
        <v-icon size="32" color="grey">mdi-sword-cross</v-icon>
      </div>

      <!-- 玩家区域 -->
      <v-card class="player-area mb-4" variant="tonal" color="green">
        <v-card-title class="text-center text-white">
          <v-icon start color="white">mdi-account</v-icon>
          玩家
          <v-chip class="ml-2" size="small" color="white" variant="flat">
            {{ gameState.player_score }} 点
          </v-chip>
        </v-card-title>
        <v-card-text class="text-center">
          <div class="cards-container">
            <div
              v-for="(card, index) in gameState.player_hand"
              :key="`player-${index}`"
              class="card"
            >
              <div class="card-front">
                <div class="card-rank" :class="getCardColor(card.suit)">{{ card.rank }}</div>
                <div class="card-suit" :class="getCardColor(card.suit)">{{ card.suit }}</div>
              </div>
            </div>
          </div>
        </v-card-text>
      </v-card>

      <!-- 操作按钮 -->
      <div v-if="gameState.game_status === 'playing'" class="action-buttons">
        <v-btn
          size="large"
          color="primary"
          variant="elevated"
          :loading="loading"
          @click="hit"
        >
          <v-icon start>mdi-plus</v-icon>
          要牌
        </v-btn>
        <v-btn
          size="large"
          color="warning"
          variant="elevated"
          :loading="loading"
          @click="playerStand"
        >
          <v-icon start>mdi-hand-back-left</v-icon>
          停牌
        </v-btn>
      </div>

      <!-- 游戏结果 -->
      <v-card v-if="gameState.game_status === 'finished'" class="result-card" variant="elevated">
        <v-card-text class="text-center">
          <div class="result-icon mb-3">
            <v-icon :color="getResultColor(gameState.result)" size="64">
              {{ getResultIcon(gameState.result) }}
            </v-icon>
          </div>
          <div class="text-h5 font-weight-bold mb-2">
            {{ getResultText(gameState.result) }}
          </div>
          <div class="text-h6" :class="gameState.credits_change >= 0 ? 'text-success' : 'text-error'">
            {{ gameState.credits_change >= 0 ? '+' : '' }}{{ gameState.credits_change.toFixed(2) }} 积分
          </div>
          <div class="text-caption text-medium-emphasis mt-2">
            当前积分: {{ gameState.current_credits.toFixed(2) }}
          </div>
          <v-btn
            class="mt-4"
            color="primary"
            variant="elevated"
            @click="newGame"
          >
            <v-icon start>mdi-refresh</v-icon>
            再来一局
          </v-btn>
        </v-card-text>
      </v-card>
    </div>

    <!-- 规则说明 -->
    <v-card class="rules-card mt-4" variant="outlined">
      <v-card-title>
        <v-icon start color="info">mdi-information</v-icon>
        游戏规则
      </v-card-title>
      <v-card-text>
        <ul class="rules-list">
          <li>目标是使手牌点数尽量接近21点但不超过21点</li>
          <li>A = 1或11点，J/Q/K = 10点，其他按牌面点数计算</li>
          <li>如果拿到天生21点（黑杰克），赢1.5倍赔率</li>
          <li>庄家必须在17点及以上停牌</li>
          <li>超过21点即为爆牌，直接输掉本局</li>
        </ul>
      </v-card-text>
    </v-card>
  </div>
</template>

<script>
import {
  startBlackjackGame,
  hitCard,
  stand,
  getBlackjackUserStatus,
  getBlackjackConfig
} from '@/services/blackjackService'

export default {
  name: 'Blackjack',
  data() {
    return {
      loading: false,
      betAmount: 50,
      minBet: 10,
      maxBet: 1000,
      minCreditsRequired: 50,
      currentCredits: 0,
      gameState: null,
      gameEnabled: true
    }
  },
  computed: {
    canBet() {
      return (
        this.betAmount >= this.minBet &&
        this.betAmount <= this.maxBet &&
        this.betAmount <= this.currentCredits &&
        this.currentCredits >= this.minCreditsRequired
      )
    }
  },
  mounted() {
    this.loadConfig()
    this.loadUserStatus()
  },
  methods: {
    async loadConfig() {
      try {
        const response = await getBlackjackConfig()
        this.minBet = response.data.min_bet
        this.maxBet = response.data.max_bet
        this.minCreditsRequired = response.data.min_credits_required
        this.gameEnabled = response.data.enabled
      } catch (error) {
        console.error('加载配置失败:', error)
      }
    },
    async loadUserStatus() {
      try {
        const response = await getBlackjackUserStatus()
        this.currentCredits = response.data.current_credits
      } catch (error) {
        console.error('加载用户状态失败:', error)
      }
    },
    async startGame() {
      if (!this.canBet) return

      try {
        this.loading = true
        const response = await startBlackjackGame(this.betAmount)
        this.gameState = response.data
        this.currentCredits = this.gameState.current_credits
      } catch (error) {
        console.error('开始游戏失败:', error)
        this.showMessage(error.response?.data?.detail || '开始游戏失败', 'error')
      } finally {
        this.loading = false
      }
    },
    async hit() {
      try {
        this.loading = true
        const response = await hitCard(this.gameState.game_id)
        this.gameState = response.data
        if (this.gameState.game_status === 'finished') {
          this.currentCredits = this.gameState.current_credits
        }
      } catch (error) {
        console.error('要牌失败:', error)
        this.showMessage(error.response?.data?.detail || '要牌失败', 'error')
      } finally {
        this.loading = false
      }
    },
    async playerStand() {
      try {
        this.loading = true
        const response = await stand(this.gameState.game_id)
        this.gameState = response.data
        this.currentCredits = this.gameState.current_credits
      } catch (error) {
        console.error('停牌失败:', error)
        this.showMessage(error.response?.data?.detail || '停牌失败', 'error')
      } finally {
        this.loading = false
      }
    },
    newGame() {
      this.gameState = null
      this.loadUserStatus()
    },
    getCardColor(suit) {
      return suit === '♥' || suit === '♦' ? 'text-red' : 'text-black'
    },
    getResultColor(result) {
      const colors = {
        win: 'success',
        blackjack: 'success',
        dealer_bust: 'success',
        lose: 'error',
        bust: 'error',
        push: 'warning'
      }
      return colors[result] || 'grey'
    },
    getResultIcon(result) {
      const icons = {
        win: 'mdi-trophy',
        blackjack: 'mdi-star',
        dealer_bust: 'mdi-emoticon-happy',
        lose: 'mdi-emoticon-sad',
        bust: 'mdi-alert-circle',
        push: 'mdi-equal'
      }
      return icons[result] || 'mdi-help-circle'
    },
    getResultText(result) {
      const texts = {
        win: '你赢了！',
        blackjack: '黑杰克！大赢！',
        dealer_bust: '庄家爆牌，你赢了！',
        lose: '你输了',
        bust: '爆牌了',
        push: '平局'
      }
      return texts[result] || '游戏结束'
    },
    showMessage(message, type = 'success') {
      if (window.Telegram?.WebApp) {
        window.Telegram.WebApp.showPopup({
          title: type === 'error' ? '错误' : '提示',
          message: message
        })
      } else {
        alert(message)
      }
    }
  }
}
</script>

<style scoped>
.blackjack-container {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
}

.game-header {
  text-align: center;
  margin-bottom: 24px;
}

.game-title {
  font-size: 24px;
  font-weight: 700;
  color: #333;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.status-card {
  border-radius: 12px;
}

.betting-card {
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.quick-bet-buttons {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.cards-container {
  display: flex;
  justify-content: center;
  gap: 12px;
  padding: 20px;
  flex-wrap: wrap;
}

.card {
  width: 80px;
  height: 112px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: transform 0.3s ease;
}

.card:hover {
  transform: translateY(-4px);
}

.hidden-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.card-front,
.card-back {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.card-rank {
  font-size: 24px;
  font-weight: bold;
}

.card-suit {
  font-size: 28px;
}

.text-red {
  color: #d32f2f;
}

.text-black {
  color: #212121;
}

.vs-divider {
  text-align: center;
}

.action-buttons {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-top: 24px;
}

.result-card {
  border-radius: 16px;
  margin-top: 24px;
  animation: fadeIn 0.5s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: scale(0.9);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.result-icon {
  animation: bounce 0.6s ease;
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

.rules-card {
  border-radius: 12px;
}

.rules-list {
  padding-left: 20px;
  line-height: 1.8;
}

.rules-list li {
  margin-bottom: 8px;
}

@media (max-width: 600px) {
  .blackjack-container {
    padding: 12px;
  }

  .card {
    width: 60px;
    height: 84px;
  }

  .card-rank {
    font-size: 18px;
  }

  .card-suit {
    font-size: 20px;
  }

  .action-buttons {
    flex-direction: column;
  }
}
</style>
