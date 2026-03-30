<template>
  <div class="admin-panel">
    <v-container fluid class="px-2 px-sm-4">
      <v-row>
        <v-col cols="12">
          <h1 class="text-h5 text-sm-h4 mb-4 mb-sm-6">🃏 21点游戏管理面板</h1>
        </v-col>
      </v-row>

      <!-- 快速操作卡片 -->
      <v-row>
        <v-col cols="6" sm="6" md="4" lg="4">
          <v-card class="admin-card" elevation="6" rounded="xl">
            <v-card-title class="d-flex align-center pa-3 pa-sm-4 admin-card-header">
              <v-avatar size="32" class="mr-2" color="rgba(255,255,255,0.2)" variant="flat">
                <v-icon size="18" color="white">mdi-cog</v-icon>
              </v-avatar>
              <span class="text-body-2 text-sm-body-1 font-weight-bold">游戏配置</span>
            </v-card-title>
            <v-card-text class="pa-3 pa-sm-4">
              <div class="text-caption text-sm-body-2" style="color: rgba(0, 0, 0, 0.6);">管理下注限制、赔率和参与条件</div>
            </v-card-text>
            <v-card-actions class="pa-3 pa-sm-4 pt-0">
              <v-btn color="primary" block size="small" variant="elevated" @click="openGameConfig">
                <v-icon size="16" class="mr-1">mdi-cog</v-icon>
                配置游戏
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-col>

        <v-col cols="6" sm="6" md="4" lg="4">
          <v-card class="admin-card" elevation="6" rounded="xl">
            <v-card-title class="d-flex align-center pa-3 pa-sm-4 admin-card-header">
              <v-avatar size="32" class="mr-2" color="rgba(255,255,255,0.2)" variant="flat">
                <v-icon size="18" color="white">mdi-chart-bar</v-icon>
              </v-avatar>
              <span class="text-body-2 text-sm-body-1 font-weight-bold">游戏统计</span>
            </v-card-title>
            <v-card-text class="pa-3 pa-sm-4">
              <div class="text-caption text-sm-body-2" style="color: rgba(0, 0, 0, 0.6);">查看游戏数据和玩家统计信息</div>
            </v-card-text>
            <v-card-actions class="pa-3 pa-sm-4 pt-0">
              <v-btn color="info" block size="small" variant="elevated" @click="loadStats">
                <v-icon size="16" class="mr-1">mdi-chart-bar</v-icon>
                查看统计
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-col>

        <v-col cols="12" sm="6" md="4" lg="4">
          <v-card class="admin-card" elevation="6" rounded="xl">
            <v-card-title class="d-flex align-center pa-3 pa-sm-4 admin-card-header">
              <v-avatar size="32" class="mr-2" color="rgba(255,255,255,0.2)" variant="flat">
                <v-icon size="18" color="white">mdi-power</v-icon>
              </v-avatar>
              <span class="text-body-2 text-sm-body-1 font-weight-bold">游戏开关</span>
            </v-card-title>
            <v-card-text class="pa-3 pa-sm-4">
              <div class="text-caption text-sm-body-2" style="color: rgba(0, 0, 0, 0.6);">启用或禁用21点游戏</div>
            </v-card-text>
            <v-card-actions class="pa-3 pa-sm-4 pt-0">
              <v-btn
                :color="gameConfig.enabled ? 'success' : 'error'"
                block
                size="small"
                variant="elevated"
                @click="toggleGameEnabled"
                :loading="toggleLoading"
              >
                <v-icon size="16" class="mr-1">{{ gameConfig.enabled ? 'mdi-check' : 'mdi-close' }}</v-icon>
                {{ gameConfig.enabled ? '游戏已开启' : '游戏已关闭' }}
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-col>
      </v-row>

      <!-- 当前游戏配置 -->
      <v-row class="mt-4 mt-sm-6">
        <v-col cols="12">
          <v-card elevation="8" rounded="xl" class="config-card">
            <v-card-title class="d-flex align-center flex-wrap pa-4 pa-sm-6 config-card-header">
              <v-avatar size="36" class="mr-3" color="rgba(255,255,255,0.2)" variant="flat">
                <v-icon size="20" color="white">mdi-tune</v-icon>
              </v-avatar>
              <span class="text-body-1 text-sm-h6 mr-2 font-weight-bold">当前游戏配置</span>
              <v-spacer class="d-none d-sm-flex"></v-spacer>
              <v-btn
                color="white"
                variant="outlined"
                size="small"
                prepend-icon="mdi-cog"
                @click="openGameConfig"
                class="mt-2 mt-sm-0 config-btn"
              >
                修改配置
              </v-btn>
            </v-card-title>

            <v-card-text class="pa-4 pa-sm-6">
              <v-row>
                <v-col cols="6" sm="4" md="3">
                  <div class="config-item">
                    <div class="config-label">最小下注</div>
                    <div class="config-value config-number">{{ gameConfig.min_bet }}</div>
                  </div>
                </v-col>
                <v-col cols="6" sm="4" md="3">
                  <div class="config-item">
                    <div class="config-label">最大下注</div>
                    <div class="config-value config-number">{{ gameConfig.max_bet }}</div>
                  </div>
                </v-col>
                <v-col cols="6" sm="4" md="3">
                  <div class="config-item">
                    <div class="config-label">最低积分要求</div>
                    <div class="config-value config-number">{{ gameConfig.min_credits_required }}</div>
                  </div>
                </v-col>
                <v-col cols="6" sm="4" md="3">
                  <div class="config-item">
                    <div class="config-label">黑杰克赔率</div>
                    <div class="config-value config-number">{{ gameConfig.blackjack_payout_ratio }}x</div>
                  </div>
                </v-col>
                <v-col cols="6" sm="4" md="3">
                  <div class="config-item">
                    <div class="config-label">普通赢赔率</div>
                    <div class="config-value config-number">{{ gameConfig.win_payout_ratio }}x</div>
                  </div>
                </v-col>
                <v-col cols="6" sm="4" md="3">
                  <div class="config-item">
                    <div class="config-label">游戏状态</div>
                    <div class="config-value">
                      <v-chip
                        :color="gameConfig.enabled ? 'success' : 'error'"
                        variant="flat"
                        size="small"
                        rounded="lg"
                        class="config-chip"
                      >
                        {{ gameConfig.enabled ? '开启' : '关闭' }}
                      </v-chip>
                    </div>
                  </div>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- 游戏统计数据 -->
      <v-row class="mt-4 mt-sm-6" v-if="stats">
        <v-col cols="12">
          <v-card elevation="8" rounded="xl" class="stats-card">
            <v-card-title class="d-flex align-center flex-wrap pa-4 pa-sm-6 stats-card-header">
              <v-avatar size="36" class="mr-3" color="rgba(255,255,255,0.2)" variant="flat">
                <v-icon size="20" color="white">mdi-chart-line</v-icon>
              </v-avatar>
              <span class="text-body-1 text-sm-h6 mr-2 font-weight-bold">游戏统计</span>
            </v-card-title>

            <v-card-text class="pa-4 pa-sm-6">
              <v-row class="stats-row">
                <v-col cols="6" sm="4" md="3">
                  <v-card variant="outlined" class="text-center stat-card" elevation="3">
                    <v-card-text class="pa-3">
                      <div class="text-body-1 text-sm-h6 font-weight-bold text-primary">{{ stats.total_games.toLocaleString() }}</div>
                      <div class="text-caption" style="color: rgba(0, 0, 0, 0.6);">总游戏局数</div>
                    </v-card-text>
                  </v-card>
                </v-col>
                <v-col cols="6" sm="4" md="3">
                  <v-card variant="outlined" class="text-center stat-card" elevation="3">
                    <v-card-text class="pa-3">
                      <div class="text-body-1 text-sm-h6 font-weight-bold text-success">{{ stats.total_wins.toLocaleString() }}</div>
                      <div class="text-caption" style="color: rgba(0, 0, 0, 0.6);">玩家胜场</div>
                    </v-card-text>
                  </v-card>
                </v-col>
                <v-col cols="6" sm="4" md="3">
                  <v-card variant="outlined" class="text-center stat-card" elevation="3">
                    <v-card-text class="pa-3">
                      <div class="text-body-1 text-sm-h6 font-weight-bold text-error">{{ stats.total_losses.toLocaleString() }}</div>
                      <div class="text-caption" style="color: rgba(0, 0, 0, 0.6);">玩家败场</div>
                    </v-card-text>
                  </v-card>
                </v-col>
                <v-col cols="6" sm="4" md="3">
                  <v-card variant="outlined" class="text-center stat-card" elevation="3">
                    <v-card-text class="pa-3">
                      <div class="text-body-1 text-sm-h6 font-weight-bold text-warning">{{ stats.total_pushes.toLocaleString() }}</div>
                      <div class="text-caption" style="color: rgba(0, 0, 0, 0.6);">平局</div>
                    </v-card-text>
                  </v-card>
                </v-col>
                <v-col cols="6" sm="4" md="3">
                  <v-card variant="outlined" class="text-center stat-card" elevation="3">
                    <v-card-text class="pa-3">
                      <div class="text-body-1 text-sm-h6 font-weight-bold text-purple">{{ stats.total_blackjacks.toLocaleString() }}</div>
                      <div class="text-caption" style="color: rgba(0, 0, 0, 0.6);">黑杰克次数</div>
                    </v-card-text>
                  </v-card>
                </v-col>
                <v-col cols="6" sm="4" md="3">
                  <v-card variant="outlined" class="text-center stat-card" elevation="3">
                    <v-card-text class="pa-3">
                      <div class="text-body-1 text-sm-h6 font-weight-bold text-info">{{ stats.total_bet_amount.toFixed(2) }}</div>
                      <div class="text-caption" style="color: rgba(0, 0, 0, 0.6);">总下注金额</div>
                    </v-card-text>
                  </v-card>
                </v-col>
                <v-col cols="6" sm="4" md="3">
                  <v-card variant="outlined" class="text-center stat-card" elevation="3">
                    <v-card-text class="pa-3">
                      <div class="text-body-1 text-sm-h6 font-weight-bold text-teal">{{ stats.total_payout_amount.toFixed(2) }}</div>
                      <div class="text-caption" style="color: rgba(0, 0, 0, 0.6);">总赔付金额</div>
                    </v-card-text>
                  </v-card>
                </v-col>
                <v-col cols="6" sm="4" md="3">
                  <v-card variant="outlined" class="text-center stat-card" elevation="3">
                    <v-card-text class="pa-3">
                      <div class="text-body-1 text-sm-h6 font-weight-bold text-orange">{{ stats.house_edge }}%</div>
                      <div class="text-caption" style="color: rgba(0, 0, 0, 0.6);">庄家优势</div>
                    </v-card-text>
                  </v-card>
                </v-col>
                <v-col cols="6" sm="4" md="3">
                  <v-card variant="outlined" class="text-center stat-card" elevation="3">
                    <v-card-text class="pa-3">
                      <div class="text-body-1 text-sm-h6 font-weight-bold text-primary">{{ stats.active_players.toLocaleString() }}</div>
                      <div class="text-caption" style="color: rgba(0, 0, 0, 0.6);">活跃玩家</div>
                    </v-card-text>
                  </v-card>
                </v-col>
                <v-col cols="6" sm="4" md="3">
                  <v-card variant="outlined" class="text-center stat-card" elevation="3">
                    <v-card-text class="pa-3">
                      <div class="text-body-1 text-sm-h6 font-weight-bold text-success">{{ stats.today_games.toLocaleString() }}</div>
                      <div class="text-caption" style="color: rgba(0, 0, 0, 0.6);">今日游戏</div>
                    </v-card-text>
                  </v-card>
                </v-col>
                <v-col cols="6" sm="4" md="3">
                  <v-card variant="outlined" class="text-center stat-card" elevation="3">
                    <v-card-text class="pa-3">
                      <div class="text-body-1 text-sm-h6 font-weight-bold text-info">{{ stats.week_games.toLocaleString() }}</div>
                      <div class="text-caption" style="color: rgba(0, 0, 0, 0.6);">本周游戏</div>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-container>

    <!-- 游戏配置弹窗 -->
    <v-dialog
      v-model="showConfigDialog"
      :max-width="$vuetify.display.xs ? '95vw' : '600'"
      :fullscreen="$vuetify.display.xs"
      persistent
    >
      <v-card rounded="xl" elevation="16" class="config-dialog">
        <v-card-title class="config-dialog-header pa-4 pa-sm-6">
          <v-avatar size="40" class="mr-3" color="rgba(255,255,255,0.2)" variant="flat">
            <v-icon size="22" color="white">mdi-cards-playing</v-icon>
          </v-avatar>
          <div class="flex-grow-1">
            <div class="text-h6 font-weight-bold">21点游戏配置</div>
            <div class="text-body-2 opacity-90">配置下注限制和赔率</div>
          </div>
          <v-btn
            icon="mdi-close"
            variant="text"
            color="white"
            @click="showConfigDialog = false"
          ></v-btn>
        </v-card-title>

        <v-card-text class="pa-4 pa-sm-6">
          <v-form ref="configForm" v-model="configValid">
            <!-- 下注限制 -->
            <div class="mb-6">
              <h4 class="text-h6 font-weight-bold mb-4 d-flex align-center">
                <v-icon class="mr-2" color="primary">mdi-cash</v-icon>
                下注限制
              </h4>

              <v-row>
                <v-col cols="12" sm="6">
                  <v-text-field
                    v-model.number="tempConfig.min_bet"
                    label="最���下注"
                    type="number"
                    min="1"
                    max="10000"
                    step="1"
                    density="compact"
                    variant="outlined"
                    rounded="lg"
                    :rules="[
                      v => !!v || '最小下注不能为空',
                      v => v >= 1 || '最小下注不能少于1',
                      v => v <= 10000 || '最小下注不能超过10000',
                      v => v < tempConfig.max_bet || '最小下注必须小于最大下注'
                    ]"
                  >
                    <template v-slot:prepend-inner>
                      <v-icon size="small" color="primary">mdi-minus-circle</v-icon>
                    </template>
                  </v-text-field>
                </v-col>

                <v-col cols="12" sm="6">
                  <v-text-field
                    v-model.number="tempConfig.max_bet"
                    label="最大下注"
                    type="number"
                    min="1"
                    max="100000"
                    step="1"
                    density="compact"
                    variant="outlined"
                    rounded="lg"
                    :rules="[
                      v => !!v || '最大下注不能为空',
                      v => v >= 1 || '最大下注不能少于1',
                      v => v <= 100000 || '最大下注不能超过100000',
                      v => v > tempConfig.min_bet || '最大下注必须大于最小下注'
                    ]"
                  >
                    <template v-slot:prepend-inner>
                      <v-icon size="small" color="primary">mdi-plus-circle</v-icon>
                    </template>
                  </v-text-field>
                </v-col>
              </v-row>
            </div>

            <v-divider class="mb-6"></v-divider>

            <!-- 赔率配置 -->
            <div class="mb-6">
              <h4 class="text-h6 font-weight-bold mb-4 d-flex align-center">
                <v-icon class="mr-2" color="success">mdi-percent</v-icon>
                赔率配置
              </h4>

              <v-row>
                <v-col cols="12" sm="6">
                  <v-text-field
                    v-model.number="tempConfig.blackjack_payout_ratio"
                    label="黑杰克赔率"
                    type="number"
                    min="1.0"
                    max="5.0"
                    step="0.1"
                    density="compact"
                    variant="outlined"
                    rounded="lg"
                    :rules="[
                      v => !!v || '黑杰克赔率不能为空',
                      v => v >= 1.0 || '黑杰克赔率不能少于1.0',
                      v => v <= 5.0 || '黑杰克赔率不能超过5.0'
                    ]"
                  >
                    <template v-slot:prepend-inner>
                      <v-icon size="small" color="success">mdi-star</v-icon>
                    </template>
                    <template v-slot:append-inner>
                      <span class="text-caption">倍</span>
                    </template>
                  </v-text-field>
                </v-col>

                <v-col cols="12" sm="6">
                  <v-text-field
                    v-model.number="tempConfig.win_payout_ratio"
                    label="普通赢赔率"
                    type="number"
                    min="0.5"
                    max="3.0"
                    step="0.1"
                    density="compact"
                    variant="outlined"
                    rounded="lg"
                    :rules="[
                      v => !!v || '普通赢赔率不能为空',
                      v => v >= 0.5 || '普通赢赔率不能少于0.5',
                      v => v <= 3.0 || '普通赢赔率不能超过3.0'
                    ]"
                  >
                    <template v-slot:prepend-inner>
                      <v-icon size="small" color="success">mdi-trophy</v-icon>
                    </template>
                    <template v-slot:append-inner>
                      <span class="text-caption">倍</span>
                    </template>
                  </v-text-field>
                </v-col>
              </v-row>
            </div>

            <v-divider class="mb-6"></v-divider>

            <!-- 参与条件 -->
            <div class="mb-6">
              <h4 class="text-h6 font-weight-bold mb-4 d-flex align-center">
                <v-icon class="mr-2" color="warning">mdi-shield-check</v-icon>
                参与条件
              </h4>

              <v-text-field
                v-model.number="tempConfig.min_credits_required"
                label="最低积分要求"
                type="number"
                min="1"
                max="100000"
                step="1"
                density="compact"
                variant="outlined"
                rounded="lg"
                :rules="[
                  v => !!v || '最低积分要求不能为空',
                  v => v >= 1 || '最低积分要求不能少于1',
                  v => v <= 100000 || '最低积分要求不能超过100000',
                  v => v >= tempConfig.min_bet || '最低积分要求不能少于最小下注'
                ]"
              >
                <template v-slot:prepend-inner>
                  <v-icon size="small" color="warning">mdi-security</v-icon>
                </template>
              </v-text-field>
            </div>

            <v-divider class="mb-6"></v-divider>

            <!-- 游戏开关 -->
            <div class="mb-4">
              <h4 class="text-h6 font-weight-bold mb-4 d-flex align-center">
                <v-icon class="mr-2" color="info">mdi-power</v-icon>
                游戏开关
              </h4>

              <v-card variant="outlined" rounded="lg" class="setting-card">
                <v-card-text class="pa-4">
                  <v-switch
                    v-model="tempConfig.enabled"
                    label="启用21点游戏"
                    color="success"
                    hide-details
                    class="mb-0"
                  >
                    <template v-slot:append>
                      <v-tooltip location="top">
                        <template v-slot:activator="{ props }">
                          <v-icon v-bind="props" color="grey" size="small">mdi-help-circle-outline</v-icon>
                        </template>
                        <span>关闭后玩家将无法参与21点游戏</span>
                      </v-tooltip>
                    </template>
                  </v-switch>
                </v-card-text>
              </v-card>
            </div>

            <!-- 配置预览 -->
            <v-alert
              type="info"
              variant="tonal"
              rounded="lg"
              class="mt-4"
            >
              <template v-slot:prepend>
                <v-icon size="large">mdi-information-outline</v-icon>
              </template>
              <div class="text-subtitle-2 mb-2 font-weight-bold">配置说明</div>
              <ul class="text-body-2">
                <li>下注范围: <strong>{{ tempConfig.min_bet }}</strong> - <strong>{{ tempConfig.max_bet }}</strong> 积分</li>
                <li>黑杰克赔率: <strong>{{ tempConfig.blackjack_payout_ratio }}x</strong></li>
                <li>普通赢赔率: <strong>{{ tempConfig.win_payout_ratio }}x</strong></li>
                <li>最低积分要求: <strong>{{ tempConfig.min_credits_required }}</strong> 积分</li>
                <li>游戏状态: <strong :class="tempConfig.enabled ? 'text-success' : 'text-error'">{{ tempConfig.enabled ? '开启' : '关闭' }}</strong></li>
              </ul>
            </v-alert>
          </v-form>
        </v-card-text>

        <v-card-actions class="pa-4 pa-sm-6 bg-grey-lighten-5">
          <v-spacer></v-spacer>
          <v-btn
            variant="text"
            @click="showConfigDialog = false"
            class="mr-2"
          >
            取消
          </v-btn>
          <v-btn
            color="primary"
            :disabled="!configValid"
            :loading="configSaving"
            variant="elevated"
            rounded="lg"
            @click="saveGameConfig"
          >
            <v-icon class="mr-2">mdi-content-save</v-icon>
            保存配置
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import { getBlackjackConfig, updateBlackjackConfig, getBlackjackStats } from '@/services/blackjackService'

export default {
  name: 'BlackjackAdminPanel',
  data() {
    return {
      showConfigDialog: false,
      gameConfig: {
        min_bet: 10,
        max_bet: 1000,
        min_credits_required: 50,
        blackjack_payout_ratio: 1.5,
        win_payout_ratio: 1.0,
        enabled: true
      },
      tempConfig: {
        min_bet: 10,
        max_bet: 1000,
        min_credits_required: 50,
        blackjack_payout_ratio: 1.5,
        win_payout_ratio: 1.0,
        enabled: true
      },
      stats: null,
      configValid: false,
      configSaving: false,
      toggleLoading: false
    }
  },
  mounted() {
    this.loadGameConfig()
    this.loadStats()
  },
  methods: {
    async loadGameConfig() {
      try {
        const response = await getBlackjackConfig()
        this.gameConfig = { ...response.data }
      } catch (error) {
        console.error('加载游戏配置失败:', error)
      }
    },

    async loadStats() {
      try {
        const response = await getBlackjackStats()
        this.stats = response.data
      } catch (error) {
        console.error('加载统计数据失败:', error)
        this.stats = {
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
    },

    openGameConfig() {
      this.tempConfig = JSON.parse(JSON.stringify(this.gameConfig))
      this.showConfigDialog = true
    },

    async saveGameConfig() {
      if (!this.configValid) return

      this.configSaving = true
      try {
        await updateBlackjackConfig(this.tempConfig)

        // 更新本地配置
        this.gameConfig = JSON.parse(JSON.stringify(this.tempConfig))
        this.showConfigDialog = false

        this.$emit('show-message', '21点游戏配置更新成功')
        console.log('21点游戏配置更新成功')

      } catch (error) {
        console.error('更新游戏配置失败:', error)
        const errorMessage = error.response?.data?.detail || '更新配置失败，请稍后重试'
        alert(errorMessage)
      } finally {
        this.configSaving = false
      }
    },

    async toggleGameEnabled() {
      this.toggleLoading = true
      try {
        const newConfig = {
          ...this.gameConfig,
          enabled: !this.gameConfig.enabled
        }

        await updateBlackjackConfig(newConfig)
        this.gameConfig = newConfig

        this.$emit('show-message', `21点游戏已${this.gameConfig.enabled ? '开启' : '关闭'}`)
      } catch (error) {
        console.error('切换游戏状态失败:', error)
        alert('切换游戏状态失败，请稍后重试')
      } finally {
        this.toggleLoading = false
      }
    }
  }
}
</script>

<style scoped>
/* 主面板样式 */
.admin-panel {
  min-height: 100vh;
  background: rgb(var(--v-theme-background));
  padding: 16px 0;
}

@media (min-width: 600px) {
  .admin-panel {
    padding: 24px 0;
  }
}

/* 统一的卡片样式 */
.admin-card {
  height: 100%;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  border: 1px solid rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.admin-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12) !important;
}

.admin-card-header {
  background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
  color: white;
  border-radius: 16px 16px 0 0 !important;
  min-height: 64px;
}

.admin-card .v-card-text {
  min-height: 80px;
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.95);
}

.admin-card .v-card-actions {
  background: rgba(255, 255, 255, 0.95);
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

/* 配置卡片样式 */
.config-card {
  border: 1px solid rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.config-card-header {
  background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
  color: white;
  border-radius: 16px 16px 0 0 !important;
}

.config-item {
  text-align: center;
  padding: 8px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.7);
  margin: 4px 0;
  transition: all 0.2s ease;
}

.config-item:hover {
  background: rgba(255, 255, 255, 0.9);
  transform: translateY(-1px);
}

.config-label {
  font-size: 0.75rem;
  color: rgba(0, 0, 0, 0.6);
  margin-bottom: 4px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.config-value {
  font-weight: 600;
  font-size: 0.875rem;
}

.config-number {
  color: #1976d2;
  font-family: 'Monaco', 'Courier New', monospace;
}

.config-chip {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.25px;
}

.config-btn {
  border-width: 2px;
  font-weight: 600;
}

/* 统计卡片样式 */
.stats-card {
  border: 1px solid rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.stats-card-header {
  background: linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%);
  color: white;
  border-radius: 16px 16px 0 0 !important;
}

.stat-card {
  border: 2px solid rgba(0, 0, 0, 0.06);
  border-radius: 12px !important;
  transition: all 0.2s ease;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(248, 250, 252, 0.9) 100%);
}

.stat-card:hover {
  border-color: rgba(25, 118, 210, 0.3);
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.stats-row .v-col {
  padding: 8px 6px;
}

@media (min-width: 600px) {
  .stats-row .v-col {
    padding: 12px 8px;
  }
}

/* 对话框样式 */
.config-dialog {
  border: 1px solid rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.config-dialog-header {
  background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
  color: white;
  border-radius: 16px 16px 0 0 !important;
  position: sticky;
  top: 0;
  z-index: 2;
}

/* 设置卡片样式 */
.setting-card {
  border: 2px solid rgba(0, 0, 0, 0.06);
  border-radius: 12px !important;
  transition: all 0.2s ease;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(248, 250, 252, 0.9) 100%);
}

.setting-card:hover {
  border-color: rgba(25, 118, 210, 0.2);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

/* 全局按钮样式优化 */
.v-btn {
  border-radius: 12px !important;
  font-weight: 600;
  letter-spacing: 0.25px;
  text-transform: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.2s ease;
}

.v-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

/* 表单字段样式 */
.v-text-field .v-field {
  border-radius: 12px !important;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

/* 修复输入框文字颜色 */
.v-text-field input {
  color: rgba(0, 0, 0, 0.87) !important;
}

.v-text-field label {
  color: rgba(0, 0, 0, 0.6) !important;
}

.v-text-field .v-field--focused label {
  color: rgb(var(--v-theme-primary)) !important;
}

.v-text-field input::placeholder {
  color: rgba(0, 0, 0, 0.38) !important;
}

.v-switch {
  border-radius: 8px;
}

/* 芯片样式 */
.v-chip {
  border-radius: 8px !important;
  font-weight: 600;
  letter-spacing: 0.25px;
}

/* 卡片动作区域样式 */
.v-card-actions.bg-grey-lighten-5 {
  background: linear-gradient(135deg, rgba(248, 250, 252, 0.9) 0%, rgba(241, 245, 249, 0.9) 100%) !important;
  backdrop-filter: blur(10px);
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}

/* 表单字段增强样式 */
.config-dialog .v-text-field .v-field {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 0, 0, 0.08);
  transition: all 0.2s ease;
}

.config-dialog .v-text-field .v-field:hover {
  background: rgba(255, 255, 255, 0.95);
  border-color: rgba(25, 118, 210, 0.3);
}

.config-dialog .v-text-field .v-field--focused {
  background: white;
  border-color: rgb(var(--v-theme-primary));
  box-shadow: 0 0 0 2px rgba(25, 118, 210, 0.2);
}

/* 确保配置对话框中的输入框文字清晰 */
.config-dialog .v-text-field input {
  color: rgba(0, 0, 0, 0.87) !important;
}

.config-dialog .v-text-field label {
  color: rgba(0, 0, 0, 0.6) !important;
}

/* 小屏幕优化 */
@media (max-width: 599px) {
  .admin-panel {
    padding: 12px 0;
  }

  .admin-card-header {
    min-height: 56px;
  }

  .admin-card .v-card-text {
    min-height: 64px;
  }

  .admin-card .v-card-title span {
    font-size: 0.8rem;
    line-height: 1.2;
  }

  .admin-card .v-card-text div {
    font-size: 0.75rem;
    line-height: 1.3;
  }

  .stats-row .text-caption {
    font-size: 0.65rem;
  }

  .config-item {
    padding: 6px;
    margin: 2px 0;
  }
}

/* 深色模式支持 */
@media (prefers-color-scheme: dark) {
  .admin-panel {
    background: linear-gradient(135deg, #1a202c 0%, #2d3748 100%);
  }

  .stat-card,
  .setting-card {
    background: linear-gradient(135deg, rgba(45, 55, 72, 0.9) 0%, rgba(26, 32, 44, 0.9) 100%);
    border-color: rgba(255, 255, 255, 0.1);
  }

  .config-item {
    background: rgba(45, 55, 72, 0.6);
    color: white;
  }

  .config-item:hover {
    background: rgba(45, 55, 72, 0.8);
  }
}
</style>
