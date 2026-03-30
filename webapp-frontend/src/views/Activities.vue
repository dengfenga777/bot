<template>
  <div class="activities-container">
    <!-- Hero Banner -->
    <div class="hbo-hero-banner">
      <div class="hero-gradient-overlay"></div>
      <div class="hero-card">
        <h1 class="hero-title">
          <v-icon class="hero-icon">mdi-gamepad-variant</v-icon>
          娱乐中心
        </h1>
        <p class="hero-subtitle">探索精彩活动，赢取丰厚奖励</p>
      </div>
    </div>

    <div class="content-wrapper">
      <!-- 加载状态 -->
      <div v-if="loading" class="loading-container">
        <div class="loading-content">
          <v-progress-circular indeterminate color="primary" size="50" width="4"></v-progress-circular>
          <div class="loading-text">加载中...</div>
        </div>
      </div>

      <!-- 错误状态 -->
      <div v-else-if="error" class="error-container">
        <v-alert type="error" class="error-alert" rounded="lg" elevation="4">{{ error }}</v-alert>
        <v-btn color="primary" @click="fetchUserInfoAndCheckStatus" class="mt-3">
          重试
        </v-btn>
      </div>

      <!-- HBO Tab Navigation -->
      <div v-else class="hbo-nav-tabs-container">
        <v-tabs
          v-model="currentTab"
          bg-color="transparent"
          color="gold"
          class="hbo-nav-tabs"
          show-arrows
        >
          <v-tab value="wheel" class="hbo-nav-tab">
            <v-icon start>mdi-ferris-wheel</v-icon>
            幸运转盘
          </v-tab>
          <v-tab value="blackjack" class="hbo-nav-tab">
            <v-icon start>mdi-cards</v-icon>
            21点
          </v-tab>
          <v-tab value="medals" class="hbo-nav-tab">
            <v-icon start>mdi-medal-outline</v-icon>
            勋章
          </v-tab>
          <v-tab value="auction" class="hbo-nav-tab">
            <v-icon start>mdi-gavel</v-icon>
            竞拍
          </v-tab>
        </v-tabs>
      </div>

      <!-- Tab Content -->
      <v-window v-if="!loading && !error" v-model="currentTab" class="hbo-tab-window">

          <!-- 幸运转盘 Tab -->
          <v-window-item value="wheel" class="hbo-tab-content">
            <div class="activity-tab-content">
              <div class="activity-header-section">
                <v-icon size="64" color="warning">mdi-ferris-wheel</v-icon>
                <h2 class="activity-tab-title">幸运大转盘</h2>
                <p class="activity-tab-desc">转一转，赢取丰厚奖励</p>
              </div>

              <div class="activity-requirements">
                <v-chip color="success" variant="flat" class="mr-2">
                  <v-icon start size="small">mdi-star</v-icon>
                  最低积分：{{ activities[0].requireCredits }}
                </v-chip>
                <v-chip color="info" variant="flat">
                  <v-icon start size="small">mdi-minus</v-icon>
                  消耗积分：{{ activities[0].costCredits }}
                </v-chip>
              </div>

              <div class="activity-current-credits">
                <span class="credits-label">当前积分：</span>
                <span class="credits-value">{{ userCredits.toFixed(2) }}</span>
              </div>

              <v-btn
                color="gold"
                size="x-large"
                variant="flat"
                class="start-activity-btn"
                :disabled="!canParticipateActivity(activities[0])"
                @click="openLuckyWheelDialog"
              >
                <v-icon start>mdi-play</v-icon>
                {{ canParticipateActivity(activities[0]) ? '开始游戏' : '积分不足' }}
              </v-btn>
            </div>
          </v-window-item>

          <!-- 21点 Tab -->
          <v-window-item value="blackjack" class="hbo-tab-content">
            <div class="activity-tab-content">
              <div class="activity-header-section">
                <v-icon size="64" color="red-darken-2">mdi-cards</v-icon>
                <h2 class="activity-tab-title">21 点</h2>
                <p class="activity-tab-desc">🃏搏一搏，单车变摩托</p>
              </div>

              <div class="activity-requirements">
                <v-chip color="success" variant="flat" class="mr-2">
                  <v-icon start size="small">mdi-star</v-icon>
                  最低积分：{{ activities[1].requireCredits }}
                </v-chip>
                <v-chip color="info" variant="flat">
                  <v-icon start size="small">mdi-minus</v-icon>
                  消耗积分：{{ activities[1].costCredits }}
                </v-chip>
              </div>

              <div class="activity-current-credits">
                <span class="credits-label">当前积分：</span>
                <span class="credits-value">{{ userCredits.toFixed(2) }}</span>
              </div>

              <v-btn
                color="gold"
                size="x-large"
                variant="flat"
                class="start-activity-btn"
                :disabled="!canParticipateActivity(activities[1])"
                @click="openBlackjackDialog"
              >
                <v-icon start>mdi-play</v-icon>
                {{ canParticipateActivity(activities[1]) ? '开始游戏' : '积分不足' }}
              </v-btn>
            </div>
          </v-window-item>

          <!-- 勋章商店 Tab -->
          <v-window-item value="medals" class="hbo-tab-content">
            <div class="activity-tab-content">
              <div class="activity-header-section">
                <v-icon size="64" color="warning">mdi-medal-outline</v-icon>
                <h2 class="activity-tab-title">勋章商店</h2>
                <p class="activity-tab-desc">收藏 Misaya 风格勋章，获得长期积分加成</p>
              </div>

              <MedalShop
                @credits-updated="handleMedalCreditsUpdated"
                @message="handleMedalShopMessage"
              />
            </div>
          </v-window-item>

          <!-- 竞拍活动 Tab -->
          <v-window-item value="auction" class="hbo-tab-content">
            <div class="activity-tab-content">
              <div class="activity-header-section">
                <v-icon size="64" color="blue">mdi-gavel</v-icon>
                <h2 class="activity-tab-title">竞拍活动</h2>
                <p class="activity-tab-desc">🎯 参与竞拍，赢取稀有奖品</p>
              </div>

              <div class="activity-requirements">
                <v-chip color="success" variant="flat" class="mr-2">
                  <v-icon start size="small">mdi-star</v-icon>
                  最低积分：{{ activities[3].requireCredits }}
                </v-chip>
                <v-chip color="success" variant="flat">
                  <v-icon start size="small">mdi-gift-outline</v-icon>
                  免费参与
                </v-chip>
              </div>

              <div class="activity-current-credits">
                <span class="credits-label">当前积分：</span>
                <span class="credits-value">{{ userCredits.toFixed(2) }}</span>
              </div>

              <v-btn
                color="gold"
                size="x-large"
                variant="flat"
                class="start-activity-btn"
                :disabled="!canParticipateActivity(activities[3])"
                @click="openAuctionDialog"
              >
                <v-icon start>mdi-eye</v-icon>
                {{ canParticipateActivity(activities[3]) ? '查看竞拍' : '积分不足' }}
              </v-btn>
            </div>
          </v-window-item>
        </v-window>

      <!-- 旧的活动列表（保留以备不时之需，暂时隐藏） -->
      <div v-if="false" class="activities-list">
        <!-- 活动卡片列表 -->
        <v-card 
          v-for="activity in activities" 
          :key="activity.id"
          class="activity-card mb-4" 
          elevation="8"
          :class="{ 
            'coming-soon': !activity.enabled,
            'insufficient-credits': activity.enabled && !canParticipateActivity(activity)
          }"
          @click="activity.enabled && openActivityDialog(activity)"
        >
          <div class="activity-header">
            <v-icon class="activity-icon" size="40" :color="activity.iconColor">
              {{ activity.icon }}
            </v-icon>
            <div class="activity-info">
              <h3 class="activity-title">{{ activity.title }}</h3>
              <p class="activity-subtitle">{{ activity.description }}</p>
              
              <!-- 积分要求信息 -->
              <div v-if="activity.enabled" class="credits-requirement mt-2">
                <v-chip
                  size="small"
                  variant="outlined"
                  :color="canParticipateActivity(activity) ? 'success' : 'warning'"
                  class="mr-2"
                >
                  <v-icon size="small" class="mr-1">mdi-star</v-icon>
                  最低积分要求： {{ activity.requireCredits }}
                </v-chip>
                
                <v-chip
                  v-if="activity.costCredits && activity.id !== 'auction'"
                  size="small"
                  variant="outlined"
                  color="info"
                >
                  <v-icon size="small" class="mr-1">mdi-minus</v-icon>
                  参与消耗积分：{{ activity.costCredits }}
                </v-chip>
                
                <v-chip
                  v-if="activity.id === 'auction'"
                  size="small"
                  variant="outlined"
                  color="success"
                >
                  <v-icon size="small" class="mr-1">mdi-gift-outline</v-icon>
                  免费参与
                </v-chip>
              </div>
            </div>
            <v-chip 
              class="activity-status" 
              :color="getActivityStatusColor(activity)"
              variant="elevated"
            >
              {{ getActivityStatusText(activity) }}
            </v-chip>
          </div>
          
          <v-card-actions class="justify-center">
            <div class="text-caption" :class="getActivityActionTextClass(activity)">
              {{ getActivityActionText(activity) }}
            </div>
          </v-card-actions>
        </v-card>
      </div>

      <!-- 幸运大转盘弹窗 -->
      <v-dialog v-model="showLuckyWheelDialog" max-width="800" persistent>
        <v-card class="activity-dialog">
          <v-card-title class="d-flex align-center justify-space-between">
            <div class="d-flex align-center">
              <v-icon class="mr-2" color="warning">mdi-ferris-wheel</v-icon>
              幸运大转盘
            </div>
            <v-btn icon @click="closeLuckyWheelDialog">
              <v-icon>mdi-close</v-icon>
            </v-btn>
          </v-card-title>

          <v-divider></v-divider>

          <v-card-text class="pa-6">
            <div class="activity-content">
              <LuckyWheel
                @spin-complete="onSpinComplete"
                @result-closed="onResultClosed"
              />
            </div>
          </v-card-text>

          <v-card-actions class="justify-center pb-4">
            <div class="text-caption text-info">
              当前积分：{{ userCredits.toFixed(2) }}
            </div>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <!-- 21点游戏弹窗 -->
      <v-dialog v-model="showBlackjackDialog" max-width="800" persistent>
        <v-card class="activity-dialog">
          <v-card-title class="d-flex align-center justify-space-between">
            <div class="d-flex align-center">
              <v-icon class="mr-2" color="red-darken-2">mdi-cards-playing</v-icon>
              21点游戏
            </div>
            <v-btn icon @click="closeBlackjackDialog">
              <v-icon>mdi-close</v-icon>
            </v-btn>
          </v-card-title>

          <v-divider></v-divider>

          <v-card-text class="pa-6">
            <div class="activity-content">
              <Blackjack />
            </div>
          </v-card-text>
        </v-card>
      </v-dialog>

      <!-- 通用活动弹窗 -->
      <v-dialog v-model="showActivityDialog" max-width="600">
        <v-card v-if="selectedActivity" class="activity-dialog">
          <v-card-title class="d-flex align-center justify-space-between">
            <div class="d-flex align-center">
              <v-icon class="mr-2" :color="selectedActivity.iconColor">{{ selectedActivity.icon }}</v-icon>
              {{ selectedActivity.title }}
            </div>
            <v-btn icon @click="closeActivityDialog">
              <v-icon>mdi-close</v-icon>
            </v-btn>
          </v-card-title>
          
          <v-divider></v-divider>
          
          <v-card-text class="pa-6">
            <div class="text-center">
              <v-icon size="80" :color="selectedActivity.iconColor" class="mb-4">
                {{ selectedActivity.icon }}
              </v-icon>
              <h3 class="mb-3">{{ selectedActivity.title }}</h3>
              <p class="text-body-1 mb-4">{{ selectedActivity.description }}</p>
              
              <!-- 积分要求信息 -->
              <div v-if="selectedActivity.enabled" class="credits-info mb-4">
                <v-alert
                  :type="canParticipateActivity(selectedActivity) ? 'success' : 'warning'"
                  variant="tonal"
                  density="compact"
                  class="mb-3"
                >
                  <div class="d-flex align-center justify-space-between">
                    <span>
                      <v-icon size="small" class="mr-1">mdi-star</v-icon>
                      最低积分要求：{{ selectedActivity.requireCredits }}
                    </span>
                    <span class="font-weight-bold">
                      当前积分：{{ userCredits.toFixed(2) }}
                    </span>
                  </div>
                </v-alert>
                
                <v-alert
                  v-if="selectedActivity.costCredits && selectedActivity.id !== 'auction'"
                  type="info"
                  variant="tonal"
                  density="compact"
                  class="mb-3"
                >
                  <v-icon size="small" class="mr-1">mdi-minus</v-icon>
                  每次参与消耗：{{ selectedActivity.costCredits }} 积分
                </v-alert>
                
                <v-alert
                  v-if="selectedActivity.id === 'auction'"
                  type="success"
                  variant="tonal"
                  density="compact"
                  class="mb-3"
                >
                  <v-icon size="small" class="mr-1">mdi-information</v-icon>
                  免费参与，只需要有足够积分进行出价
                </v-alert>
                
                <v-alert
                  v-if="!canParticipateActivity(selectedActivity)"
                  type="error"
                  variant="tonal"
                  density="compact"
                >
                  <v-icon size="small" class="mr-1">mdi-alert</v-icon>
                  积分不足，还需 {{ (selectedActivity.requireCredits - userCredits).toFixed(2) }} 积分
                </v-alert>
              </div>
              
              <v-chip 
                :color="selectedActivity.enabled ? (canParticipateActivity(selectedActivity) ? 'success' : 'warning') : 'grey'"
                variant="elevated"
                class="mb-4"
              >
                {{ getActivityStatusText(selectedActivity) }}
              </v-chip>
            </div>
          </v-card-text>
        </v-card>
      </v-dialog>

      <!-- 竞拍活动弹窗 -->
      <v-dialog v-model="showAuctionDialog" max-width="800" persistent>
        <v-card class="activity-dialog">
          <v-card-title class="d-flex align-center justify-space-between">
            <div class="d-flex align-center">
              <v-icon class="mr-2" color="blue">mdi-gavel</v-icon>
              竞拍活动
            </div>
            <v-btn icon @click="closeAuctionDialog">
              <v-icon>mdi-close</v-icon>
            </v-btn>
          </v-card-title>
          
          <v-divider></v-divider>
          
          <v-card-text class="pa-6">
            <div v-if="auctionLoading" class="text-center py-8">
              <v-progress-circular indeterminate color="primary" size="50"></v-progress-circular>
              <div class="mt-3">加载竞拍活动中...</div>
            </div>
            
            <div v-else-if="auctionError" class="text-center py-8">
              <v-alert type="error" variant="tonal">{{ auctionError }}</v-alert>
              <v-btn color="primary" class="mt-3" @click="loadActiveAuctions">重试</v-btn>
            </div>
            
            <div v-else-if="activeAuctions.length === 0" class="text-center py-8">
              <v-icon size="64" color="grey-lighten-2">mdi-gavel</v-icon>
              <div class="text-h6 mt-3 text-medium-emphasis">暂无进行中的竞拍活动</div>
              <div class="text-body-2 text-medium-emphasis">请稍后再来查看</div>
            </div>
            
            <div v-else>
              <v-row>
                <v-col v-for="auction in activeAuctions" :key="auction.id" cols="12" md="6">
                  <v-card variant="outlined" rounded="lg" class="auction-card">
                    <v-card-title class="d-flex align-center">
                      <v-icon class="mr-2" color="blue">mdi-trophy</v-icon>
                      {{ auction.title }}
                    </v-card-title>
                    
                    <v-card-text>
                      <p class="text-body-2 mb-3">{{ auction.description }}</p>
                      
                      <div class="auction-info mb-3">
                        <v-row dense>
                          <v-col cols="6">
                            <div class="info-item">
                              <div class="text-caption text-medium-emphasis">起拍价</div>
                              <div class="text-h6 text-primary">{{ auction.starting_price }}</div>
                            </div>
                          </v-col>
                          <v-col cols="6">
                            <div class="info-item">
                              <div class="text-caption text-medium-emphasis">当前最高价</div>
                              <div class="text-h6 text-warning">{{ auction.current_price || auction.starting_price }}</div>
                            </div>
                          </v-col>
                        </v-row>
                      </div>
                      
                      <div class="mb-3">
                        <div class="text-caption text-medium-emphasis">结束时间</div>
                        <div class="text-body-2">{{ formatDateTime(auction.end_time) }}</div>
                      </div>
                      
                      <div v-if="auction.recent_bids && auction.recent_bids.length > 0" class="mb-3">
                        <div class="text-caption text-medium-emphasis mb-2">最近出价</div>
                        <div class="recent-bids">
                          <div v-for="bid in auction.recent_bids.slice(0, 3)" :key="bid.id" class="bid-item">
                            <span class="text-body-2">{{ bid.user_name }}</span>
                            <span class="text-warning font-weight-bold">{{ bid.bid_amount }}</span>
                          </div>
                        </div>
                      </div>
                    </v-card-text>
                    
                    <v-card-actions class="pa-4 pt-0">
                      <v-btn 
                        color="blue" 
                        variant="elevated" 
                        block
                        :disabled="!canParticipateAuction(auction)"
                        @click="openBidDialog(auction)"
                      >
                        <v-icon start>mdi-gavel</v-icon>
                        {{ canParticipateAuction(auction) ? '参与竞拍' : '积分不足' }}
                      </v-btn>
                    </v-card-actions>
                  </v-card>
                </v-col>
              </v-row>
            </div>
          </v-card-text>
          
          <v-card-actions class="justify-center pb-4">
            <div class="text-caption text-info">
              当前积分：{{ userCredits.toFixed(2) }}
            </div>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <!-- 出价弹窗 -->
      <v-dialog v-model="showBidDialog" max-width="400">
        <v-card v-if="selectedAuction">
          <v-card-title>
            <v-icon class="mr-2" color="blue">mdi-gavel</v-icon>
            参与竞拍
          </v-card-title>
          
          <v-card-text>
            <div class="mb-4">
              <div class="text-h6">{{ selectedAuction.title }}</div>
              <div class="text-body-2 text-medium-emphasis">{{ selectedAuction.description }}</div>
            </div>
            
            <div class="mb-4">
              <div class="text-caption text-medium-emphasis">当前最高价</div>
              <div class="text-h6 text-warning">{{ selectedAuction.current_price || selectedAuction.starting_price }}</div>
            </div>
            
            <v-text-field
              v-model="bidAmount"
              label="出价金额"
              type="number"
              :min="getMinBidAmount(selectedAuction)"
              variant="outlined"
              :rules="bidRules"
              prefix="💰"
            ></v-text-field>
            
            <div class="text-caption text-medium-emphasis">
              最低出价：{{ getMinBidAmount(selectedAuction) }}
            </div>
          </v-card-text>
          
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn variant="text" @click="closeBidDialog">取消</v-btn>
            <v-btn 
              color="blue" 
              variant="elevated"
              :loading="bidSubmitting"
              :disabled="!isValidBid()"
              @click="submitBid"
            >
              确认出价
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <!-- 消息提示 Snackbar -->
      <v-snackbar 
        v-model="showSnackbar" 
        :color="snackbarColor" 
        :timeout="4000"
        location="top"
      >
        {{ snackbarMessage }}
        <template v-slot:actions>
          <v-btn variant="text" @click="showSnackbar = false">
            关闭
          </v-btn>
        </template>
      </v-snackbar>
    </div>
  </div>
</template>

<script>
import LuckyWheel from '@/components/LuckyWheel.vue'
import Blackjack from '@/components/Blackjack.vue'
import MedalShop from '@/components/MedalShop.vue'
import { getUserInfo } from '@/api'
import { getLuckyWheelUserStatus } from '@/services/wheelService'
import { getActiveAuctions, placeBid, getAuctionDetails } from '@/services/auctionService'
import { getBlackjackConfig } from '@/services/blackjackService'

export default {
  name: 'Activities',
  components: {
    LuckyWheel,
    Blackjack,
    MedalShop
  },
  data() {
    return {
      currentTab: 'wheel', // 当前选中的Tab
      userCredits: 0, // 用户积分
      isAdmin: false,
      loading: true, // 加载状态
      error: null, // 错误信息
      showLuckyWheelDialog: false, // 幸运大转盘弹窗
      showBlackjackDialog: false, // 21点游戏弹窗
      showActivityDialog: false, // 通用活动弹窗
      showAuctionDialog: false, // 竞拍活动弹窗
      showBidDialog: false, // 出价弹窗
      selectedActivity: null, // 选中的活动
      selectedAuction: null, // 选中的竞拍
      bidAmount: '', // 出价金额
      bidSubmitting: false, // 出价提交中
      // 竞拍相关数据
      activeAuctions: [], // 活跃的竞拍活动
      auctionLoading: false, // 竞拍加载状态
      auctionError: null, // 竞拍错误信息
      // 消息提示相关
      showSnackbar: false,
      snackbarMessage: '',
      snackbarColor: 'success',
      // 活动配置 - 将从后端获取
      activitiesConfig: {
        luckyWheel: {
          costCredits: 10,
          minCreditsRequired: 30
        }
      },
      activities: [
        {
          id: 'lucky-wheel',
          title: '幸运大转盘',
          description: '转一转，赢取丰厚奖励',
          icon: 'mdi-ferris-wheel',
          iconColor: 'warning',
          enabled: true,
          // 这些值将从后端获取
          requireCredits: 30,
          costCredits: 10
        },
        {
          id: 'black-jack',
          title: '21 点',
          description: '🃏搏一搏，单车变摩托',
          icon: 'mdi-cards',
          iconColor: 'red-darken-2',
          enabled: true,
          requireCredits: 50,
          costCredits: 20
        },
        {
          id: 'medal-shop',
          title: '勋章商店',
          description: '🏅 收藏 Misaya 勋章，解锁积分加成',
          icon: 'mdi-medal-outline',
          iconColor: 'warning',
          enabled: true,
          requireCredits: 0,
          costCredits: 0
        },
        {
          id: 'auction',
          title: '竞拍活动',
          description: '🎯 参与竞拍，赢取稀有奖品',
          icon: 'mdi-gavel',
          iconColor: 'blue',
          enabled: true,
          requireCredits: 10,
          costCredits: 0
        }
      ]
    }
  },
  mounted() {
    // 从路由查询参数获取tab，如果有的话
    const tabFromRoute = this.$route.query.tab
    if (tabFromRoute && ['wheel', 'blackjack', 'medals', 'auction'].includes(tabFromRoute)) {
      this.currentTab = tabFromRoute
    }

    // 获取用户信息和活动配置（优化：一次调用同时获取积分和活动配置）
    this.fetchUserInfoAndCheckStatus()
  },
  computed: {
    // 检查用户是否可以参与各个活动
    canParticipateActivity() {
      return (activity) => {
        return this.userCredits >= activity.requireCredits
      }
    },
    
    // 出价验证规则
    bidRules() {
      return [
        v => !!v || '请输入出价金额',
        v => !isNaN(v) && Number(v) > 0 || '出价必须是正数',
        v => this.selectedAuction && Number(v) >= this.getMinBidAmount(this.selectedAuction) || `出价不能低于 ${this.getMinBidAmount(this.selectedAuction)}`,
        v => Number(v) <= this.userCredits || '出价不能超过当前积分'
      ]
    }
  },
  methods: {
    async fetchActivitiesConfig() {
      try {
        // 获取幸运大转盘配置，同时获取用户积分信息
        const response = await getLuckyWheelUserStatus()
        const config = response.data

        // 更新用户积分（从 getLuckyWheelUserStatus 获取）
        this.userCredits = config.current_credits

        // 获取管理员状态
        try {
          const userInfoRes = await getUserInfo()
          this.isAdmin = userInfoRes.data.is_admin || false
        } catch (e) {
          this.isAdmin = false
        }

        // 更新活动配置
        this.activitiesConfig.luckyWheel = {
          costCredits: config.cost_credits,
          minCreditsRequired: config.min_credits_required
        }

        // 更新活动列表中的配置
        const luckyWheelActivity = this.activities.find(a => a.id === 'lucky-wheel')
        if (luckyWheelActivity) {
          luckyWheelActivity.requireCredits = config.min_credits_required
          luckyWheelActivity.costCredits = config.cost_credits
        }

        // 获取21点游戏配置
        try {
          const blackjackResponse = await getBlackjackConfig()
          const blackjackConfig = blackjackResponse.data
          const blackJackActivity = this.activities.find(a => a.id === 'black-jack')
          if (blackJackActivity) {
            blackJackActivity.requireCredits = blackjackConfig.min_credits_required
            blackJackActivity.costCredits = blackjackConfig.min_bet
            blackJackActivity.enabled = blackjackConfig.enabled
          }
        } catch (err) {
          console.warn('获取21点游戏配置失败，使用默认配置:', err)
        }

        console.log('活动配置获取成功:', this.activitiesConfig)
      } catch (err) {
        console.error('获取活动配置失败:', err)
        // 使用默认配置，但仍需要获取用户积分
        const luckyWheelActivity = this.activities.find(a => a.id === 'lucky-wheel')
        if (luckyWheelActivity) {
          luckyWheelActivity.requireCredits = 30
          luckyWheelActivity.costCredits = 10
        }

        const blackJackActivity = this.activities.find(a => a.id === 'black-jack')
        if (blackJackActivity) {
          blackJackActivity.requireCredits = 50
          blackJackActivity.costCredits = 20
        }

        // 如果获取活动配置失败，仍需要获取用户积分
        await this.fetchUserCreditsOnly()
      }
    },

    async fetchUserCreditsOnly() {
      try {
        // 仅获取用户积分信息
        const response = await getUserInfo()
        this.userCredits = response.data.credits
        this.isAdmin = response.data.is_admin || false
      } catch (err) {
        console.error('获取用户积分失败:', err)
        this.error = err.response?.data?.detail || '获取用户信息失败'
      }
    },

    async fetchUserInfoAndCheckStatus() {
      try {
        this.loading = true
        this.error = null
        
        // 优化：直接调用 fetchActivitiesConfig，它会同时获取积分信息
        await this.fetchActivitiesConfig()
        
        this.loading = false
      } catch (err) {
        this.error = err.response?.data?.detail || '获取用户信息失败'
        this.loading = false
        console.error('获取用户信息失败:', err)
      }
    },
    
    onSpinComplete(result) {
      // 转盘完成回调
      console.log('转盘结果：', result)
      // 转盘已经通过后端处理，这里只需要处理前端逻辑
    },
    
    onResultClosed(result) {
      // 结果弹窗关闭后更新用户积分信息
      console.log('结果弹窗已关闭，转盘结果：', result, '更新用户积分信息')
      // 优化：只更新积分信息，不需要重新获取活动配置
      this.fetchUserCreditsOnly()
    },

    // 打开幸运转盘弹窗
    openLuckyWheelDialog() {
      this.showLuckyWheelDialog = true
    },

    // 打开21点游戏弹窗
    openBlackjackDialog() {
      this.showBlackjackDialog = true
    },

    // 打开活动弹窗
    openActivityDialog(activity) {
      // 检查是否满足参与条件
      if (!this.canParticipateActivity(activity)) {
        // 不满足条件时显示提示但仍可以打开弹窗查看详情
        console.log(`积分不足，需要 ${activity.requireCredits} 积分才能参与`)
      }

      if (activity.id === 'lucky-wheel') {
        this.showLuckyWheelDialog = true
      } else if (activity.id === 'black-jack') {
        this.showBlackjackDialog = true
      } else if (activity.id === 'auction') {
        this.showAuctionDialog = true
        this.loadActiveAuctions()
      } else if (activity.id === 'medal-shop') {
        this.currentTab = 'medals'
      } else {
        this.selectedActivity = activity
        this.showActivityDialog = true
      }
    },

    // 关闭幸运大转盘弹窗
    closeLuckyWheelDialog() {
      this.showLuckyWheelDialog = false
    },

    // 关闭21点游戏弹窗
    closeBlackjackDialog() {
      this.showBlackjackDialog = false
      // 更新用户积分信息
      this.fetchUserCreditsOnly()
    },

    handleMedalCreditsUpdated(currentCredits) {
      this.userCredits = Number(currentCredits || 0)
    },

    handleMedalShopMessage(payload) {
      if (!payload) return
      this.showMessage(payload.text, payload.color === 'error' ? 'error' : 'success')
    },

    // 关闭通用活动弹窗
    closeActivityDialog() {
      this.showActivityDialog = false
      this.selectedActivity = null
    },

    // 竞拍相关方法
    async loadActiveAuctions() {
      try {
        this.auctionLoading = true
        this.auctionError = null
        const response = await getActiveAuctions()
        
        // 处理竞拍数据，添加最近出价信息
        const auctions = response.data.auctions || []
        
        // 为每个竞拍获取最近的出价记录
        for (let auction of auctions) {
          try {
            const detailResponse = await getAuctionDetails(auction.id)
            if (detailResponse.data.recent_bids) {
              auction.recent_bids = detailResponse.data.recent_bids
            }
          } catch (err) {
            console.warn(`获取竞拍 ${auction.id} 的出价记录失败:`, err)
            auction.recent_bids = []
          }
        }
        
        this.activeAuctions = auctions
        console.log('加载活跃竞拍活动:', this.activeAuctions)
      } catch (err) {
        this.auctionError = err.response?.data?.detail || '加载竞拍活动失败'
        console.error('加载竞拍活动失败:', err)
      } finally {
        this.auctionLoading = false
      }
    },

    closeAuctionDialog() {
      this.showAuctionDialog = false
      this.activeAuctions = []
      this.auctionError = null
    },

    canParticipateAuction(auction) {
      // 检查用户是否有足够的积分参与竞拍（只需要满足最低出价金额）
      const minBid = this.getMinBidAmount(auction)
      return this.userCredits >= minBid
    },

    getMinBidAmount(auction) {
      // 获取最小出价金额（当前价格 + 1 或起拍价）
      const currentPrice = auction.current_price || auction.starting_price
      return currentPrice + 1
    },

    openBidDialog(auction) {
      this.selectedAuction = auction
      this.bidAmount = this.getMinBidAmount(auction).toString()
      this.showBidDialog = true
    },

    closeBidDialog() {
      this.showBidDialog = false
      this.selectedAuction = null
      this.bidAmount = ''
      this.bidSubmitting = false
    },

    isValidBid() {
      if (!this.bidAmount || !this.selectedAuction) return false
      const amount = Number(this.bidAmount)
      return amount >= this.getMinBidAmount(this.selectedAuction) && amount <= this.userCredits
    },

    async submitBid() {
      if (!this.isValidBid()) {
        this.showMessage('出价信息无效，请检查出价金额', 'warning')
        return
      }

      try {
        this.bidSubmitting = true
        const response = await placeBid(this.selectedAuction.id, Number(this.bidAmount))
        
        // 出价成功，更新本地数据
        this.userCredits = response.data.user_credits || this.userCredits
        
        // 关闭出价弹窗
        this.closeBidDialog()
        
        // 重新加载竞拍活动以显示最新状态
        await this.loadActiveAuctions()
        
        // 显示成功消息
        this.showMessage('出价成功！', 'success')
        
      } catch (err) {
        // 提取错误消息
        let errorMsg = '出价失败'
        
        if (err.response) {
          // 服务器返回了错误响应
          const errorData = err.response.data
          if (typeof errorData === 'string') {
            errorMsg = errorData
          } else if (errorData?.detail) {
            errorMsg = errorData.detail
          } else if (errorData?.message) {
            errorMsg = errorData.message
          } else if (errorData?.error) {
            errorMsg = errorData.error
          } else {
            errorMsg = `请求失败 (状态码: ${err.response.status})`
          }
        } else if (err.request) {
          // 请求已发出但没有收到响应
          errorMsg = '网络连接失败，请检查网络后重试'
        } else if (err.message) {
          // 其他错误
          errorMsg = err.message
        }
        
        this.showMessage(errorMsg, 'error')
        console.error('出价失败详细信息:', {
          error: err,
          response: err.response?.data,
          status: err.response?.status
        })
      } finally {
        this.bidSubmitting = false
      }
    },

    // 显示消息提示
    showMessage(message, type = 'success') {
      this.snackbarMessage = message
      this.snackbarColor = type
      this.showSnackbar = true
    },

    formatDateTime(dateString) {
      if (!dateString) return '未知'
      try {
        const date = new Date(dateString)
        return date.toLocaleString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit'
        })
      } catch (err) {
        return '时间格式错误'
      }
    },

    // 获取活动状态颜色
    getActivityStatusColor(activity) {
      if (!activity.enabled) return 'grey'
      if (!this.canParticipateActivity(activity)) return 'warning'
      return 'success'
    },

    // 获取活动状态文本
    getActivityStatusText(activity) {
      if (!activity.enabled) return '敬请期待'
      if (!this.canParticipateActivity(activity)) return '积分不足'
      return '立即参与'
    },

    // 获取活动操作文本
    getActivityActionText(activity) {
      if (!activity.enabled) return '活动暂未开放'
      if (!this.canParticipateActivity(activity)) {
        const need = activity.requireCredits - this.userCredits
        return `还需 ${need.toFixed(2)} 积分才能参与`
      }
      return '点击进入活动'
    },

    // 获取活动操作文本样式
    getActivityActionTextClass(activity) {
      if (!activity.enabled) return 'text-grey'
      if (!this.canParticipateActivity(activity)) return 'text-warning'
      return 'text-primary'
    }
  }
}
</script>

<style scoped lang="scss">
.activities-container {
  min-height: 100vh;
  background: var(--hbo-bg-dark);
  padding: 0;
  padding-bottom: calc(70px + var(--hbo-spacing-6)); /* 为底部导航栏留出空间 */
}

.content-wrapper {
  padding: var(--hbo-spacing-6) var(--hbo-spacing-4) 0;
}

/* HBO Header */
/* Hero Banner */
.hbo-hero-banner {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 24px var(--hbo-spacing-4);
  margin-bottom: 0;
}

.hero-gradient-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(circle at 30% 50%, rgba(255, 214, 10, 0.1) 0%, transparent 50%),
              radial-gradient(circle at 70% 80%, rgba(6, 255, 165, 0.1) 0%, transparent 50%);
  animation: hbo-float 6s ease-in-out infinite;
  pointer-events: none;
}

.hero-card {
  position: relative;
  z-index: 2;
  background: linear-gradient(135deg, var(--hbo-purple-primary) 0%, var(--hbo-purple-deep) 100%);
  border-radius: 24px;
  padding: 48px 32px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  max-width: 700px;
  width: 100%;
  min-height: 180px;
  text-align: center;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.hero-title {
  font-size: 32px;
  font-weight: 700;
  color: var(--hbo-text-primary);
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--hbo-spacing-2);
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.hero-icon {
  font-size: 36px;
  color: var(--hbo-gold);
  filter: drop-shadow(0 0 8px rgba(255, 214, 10, 0.6));
}

.hero-subtitle {
  font-size: 16px;
  color: var(--hbo-text-secondary);
  margin-top: var(--hbo-spacing-2);
  text-align: center;
}

/* HBO Tabs */
.hbo-activities-tabs {
  padding: 0;
}

.hbo-tab-window {
  background: transparent;
  min-height: 60vh;
}

.hbo-tab-content {
  padding: var(--hbo-spacing-6) 0;
}

/* Activity Tab Content */
.activity-tab-content {
  text-align: center;
  background: var(--hbo-bg-card);
  border-radius: var(--hbo-radius-xl);
  padding: var(--hbo-spacing-8);
  box-shadow: var(--hbo-shadow-lg);
}

.activity-header-section {
  margin-bottom: var(--hbo-spacing-6);
}

.activity-tab-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--hbo-text-primary);
  margin: var(--hbo-spacing-3) 0;
}

.activity-tab-desc {
  font-size: 16px;
  color: var(--hbo-text-secondary);
  margin-bottom: var(--hbo-spacing-4);
}

.activity-requirements {
  display: flex;
  justify-content: center;
  gap: var(--hbo-spacing-2);
  margin-bottom: var(--hbo-spacing-4);
  flex-wrap: wrap;
}

.activity-current-credits {
  background: rgba(123, 44, 191, 0.1);
  padding: var(--hbo-spacing-3);
  border-radius: var(--hbo-radius-md);
  margin-bottom: var(--hbo-spacing-6);
  border: 1px solid rgba(123, 44, 191, 0.3);
}

.credits-label {
  font-size: 14px;
  color: var(--hbo-text-secondary);
  margin-right: var(--hbo-spacing-2);
}

.credits-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--hbo-gold);
  text-shadow: 0 0 8px rgba(255, 214, 10, 0.4);
}

.start-activity-btn {
  min-width: 200px;
  height: 56px;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 1px;
  box-shadow: var(--hbo-shadow-lg);
  transition: all var(--hbo-transition-base);

  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: var(--hbo-shadow-2xl);
  }

  &:disabled {
    opacity: 0.5;
  }
}

.activities-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.activity-card {
  background: rgba(var(--v-theme-surface), 0.95);
  border-radius: 20px;
  overflow: hidden;
  backdrop-filter: blur(10px);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  cursor: pointer;
}

.activity-card:hover:not(.coming-soon) {
  transform: translateY(-4px);
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.15) !important;
}

.activity-header {
  display: flex;
  align-items: center;
  padding: 24px;
  gap: 16px;
}

.activity-icon {
  background: rgba(255, 152, 0, 0.1);
  border-radius: 12px;
  padding: 8px;
}

.activity-info {
  flex: 1;
}

.activity-title {
  font-size: 20px;
  font-weight: 700;
  color: rgb(var(--v-theme-on-surface));
  margin: 0 0 4px 0;
}

.activity-subtitle {
  font-size: 14px;
  color: rgba(var(--v-theme-on-surface), 0.7);
  margin: 0;
}

.activity-status {
  font-weight: 600;
}

.activity-content {
  padding: 0 24px 24px 24px;
}

.coming-soon {
  opacity: 0.7;
  cursor: default;
}

.coming-soon .activity-header {
  opacity: 0.6;
}

.insufficient-credits {
  border: 2px solid #ff9800;
  background: rgba(255, 152, 0, 0.05);
}

.insufficient-credits .activity-header {
  opacity: 0.8;
}

.credits-requirement {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.credits-requirement .v-chip {
  font-size: 11px;
  height: 24px;
}

.credits-info .v-alert {
  text-align: left;
}

.credits-info .v-alert .v-alert__content {
  font-size: 14px;
}

.activity-dialog {
  border-radius: 20px;
  overflow: hidden;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.activity-dialog .v-card-title {
  background: linear-gradient(45deg, #667eea, #764ba2);
  color: white;
  font-weight: 600;
  flex-shrink: 0;
}

.activity-dialog .v-card-text {
  overflow-y: auto;
  flex: 1;
}

.activity-content {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}

/* 原有的空状态样式保留,以防需要 */
.empty-state {
  text-align: center;
  background: rgba(var(--v-theme-surface), 0.95);
  border-radius: 20px;
  padding: 60px 40px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
}

.empty-icon {
  margin-bottom: 20px;
  opacity: 0.7;
}

.empty-title {
  font-size: 24px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface));
  margin-bottom: 10px;
}

.empty-description {
  font-size: 16px;
  color: rgba(var(--v-theme-on-surface), 0.7);
  margin: 0;
}

/* 响应式设计 */
@media (max-width: 480px) {
  .content-wrapper {
    padding-top: 10px;
  }

  .activity-header {
    padding: 16px;
    flex-direction: column;
    text-align: center;
    gap: 12px;
  }
  
  .activity-content {
    padding: 0 16px 16px 16px;
  }
  
  .activity-title {
    font-size: 18px;
  }
  
  .activity-subtitle {
    font-size: 13px;
  }
  
  .empty-state {
    padding: 40px 20px;
  }
  
  .empty-title {
    font-size: 20px;
  }
  
  .empty-description {
    font-size: 14px;
  }
}
</style>
