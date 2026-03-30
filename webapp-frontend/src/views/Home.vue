<template>
  <div class="home-view">
    <!-- Hero Banner -->
    <div class="hbo-hero-banner">
      <div class="hero-gradient-overlay"></div>
      <div class="hero-card">
        <h1 class="hero-title">
          <v-icon class="hero-icon">mdi-star-circle</v-icon>
          欢迎回来
        </h1>
        <p class="hero-subtitle">{{ greeting }}</p>
      </div>
    </div>


    <!-- Daily Check-in Section -->
    <section class="checkin-section">
      <h2 class="section-title">
        <v-icon class="title-icon">mdi-calendar-check</v-icon>
        每日签到
      </h2>
      <checkin-calendar @credits-updated="loadUserData" />
    </section>

    <!-- Quick Actions Grid -->
    <section class="quick-actions-section">
      <h2 class="section-title">
        <v-icon class="title-icon">mdi-lightning-bolt</v-icon>
        快捷操作
      </h2>
      <v-row dense>
        <v-col cols="6" sm="3">
          <div class="hbo-action-card" @click="openInviteCodeDialog">
            <div class="action-icon-wrapper action-invite">
              <v-icon class="action-icon">mdi-account-plus</v-icon>
            </div>
            <div class="action-label">生成邀请码</div>
            <div class="action-hint">创建新邀请</div>
          </div>
        </v-col>

        <v-col cols="6" sm="3">
          <div class="hbo-action-card" @click="openRedeemCodeDialog">
            <div class="action-icon-wrapper action-redeem">
              <v-icon class="action-icon">mdi-ticket-percent</v-icon>
            </div>
            <div class="action-label">兑换邀请码</div>
            <div class="action-hint">输入兑换码</div>
          </div>
        </v-col>

        <v-col cols="6" sm="3">
          <div class="hbo-action-card" @click="openBindAccountDialog">
            <div class="action-icon-wrapper action-bind">
              <v-icon class="action-icon">mdi-link-variant</v-icon>
            </div>
            <div class="action-label">绑定账户</div>
            <div class="action-hint">关联媒体账号</div>
          </div>
        </v-col>

      </v-row>
    </section>

    <!-- Continue Playing Section -->
    <section class="continue-section" v-if="recentGames.length > 0">
      <h2 class="section-title">
        <v-icon class="title-icon">mdi-gamepad-variant</v-icon>
        继续游玩
      </h2>
      <v-row dense>
        <v-col
          v-for="game in recentGames"
          :key="game.id"
          cols="12"
          sm="6"
        >
          <div class="hbo-game-card" @click="navigateTo(game.route)">
            <div class="game-thumbnail" :class="`${game.id}-bg`">
              <div class="game-overlay">
                <v-icon class="game-play-icon">mdi-play-circle</v-icon>
              </div>
            </div>
            <div class="game-info">
              <div class="game-title">
                <v-icon size="small" class="game-title-icon">{{ game.icon }}</v-icon>
                {{ game.name }}
              </div>
              <div class="game-desc">{{ game.description }}</div>
            </div>
          </div>
        </v-col>
      </v-row>
    </section>

    <!-- Community Links Section -->
    <section v-if="systemStatus.community_links?.group || systemStatus.community_links?.channel" class="community-section">
      <h2 class="section-title">
        <v-icon class="title-icon">mdi-account-group</v-icon>
        交流讨论
      </h2>
      <div class="community-links-container">
        <!-- 交流群链接 -->
        <div
          v-if="systemStatus.community_links?.group"
          class="community-link-item"
          @click="openCommunityLink('group')"
        >
          <div class="link-icon-wrapper group-link">
            <v-icon color="white" size="20">mdi-forum</v-icon>
          </div>
          <div class="link-content">
            <div class="link-title">用户交流群</div>
            <div class="link-description">随便聊聊</div>
          </div>
          <div class="link-actions">
            <v-btn
              icon
              size="x-small"
              variant="text"
              @click.stop="copyLinkUrl('group')"
              title="复制链接"
              class="copy-link-btn"
            >
              <v-icon size="16">mdi-content-copy</v-icon>
            </v-btn>
            <v-icon color="primary" size="20">mdi-chevron-right</v-icon>
          </div>
        </div>

        <!-- 通知频道链接 -->
        <div
          v-if="systemStatus.community_links?.channel && systemStatus.community_links.channel !== systemStatus.community_links.group"
          class="community-link-item"
          @click="openCommunityLink('channel')"
        >
          <div class="link-icon-wrapper channel-link">
            <v-icon color="white" size="20">mdi-bullhorn</v-icon>
          </div>
          <div class="link-content">
            <div class="link-title">官方通知频道</div>
            <div class="link-description">获取最新服务公告和更新</div>
          </div>
          <div class="link-actions">
            <v-btn
              icon
              size="x-small"
              variant="text"
              @click.stop="copyLinkUrl('channel')"
              title="复制链接"
              class="copy-link-btn"
            >
              <v-icon size="16">mdi-content-copy</v-icon>
            </v-btn>
            <v-icon color="primary" size="20">mdi-chevron-right</v-icon>
          </div>
        </div>
      </div>
    </section>

    <!-- Recent Activity -->
    <section class="activity-section">
      <h2 class="section-title">
        <v-icon class="title-icon">mdi-history</v-icon>
        最近动态
      </h2>
      <div class="hbo-activity-list">
        <div
          v-for="(activity, index) in recentActivities"
          :key="index"
          class="activity-item"
        >
          <div class="activity-icon-wrapper" :class="`activity-${activity.type}`">
            <v-icon class="activity-icon">{{ activity.icon }}</v-icon>
          </div>
          <div class="activity-content">
            <div class="activity-title">{{ activity.title }}</div>
            <div class="activity-time">{{ activity.time }}</div>
          </div>
          <div class="activity-value" :class="activity.valueClass">
            {{ activity.value }}
          </div>
        </div>

        <div v-if="recentActivities.length === 0" class="empty-state">
          <v-icon class="empty-icon">mdi-inbox-outline</v-icon>
          <div class="empty-text">暂无最近动态</div>
        </div>
      </div>
    </section>

    <!-- Dialog Components -->
    <invite-code-dialog
      ref="inviteCodeDialog"
      @code-generated="handleInviteCodeGenerated"
    />

    <redeem-code-dialog
      ref="redeemCodeDialog"
      @code-redeemed="handleCodeRedeemed"
    />

    <bind-account-dialog
      ref="bindAccountDialog"
      @account-bound="handleAccountBound"
    />

  </div>
</template>

<script>
import InviteCodeDialog from '@/components/InviteCodeDialog.vue'
import RedeemCodeDialog from '@/components/RedeemCodeDialog.vue'
import BindAccountDialog from '@/components/BindAccountDialog.vue'
import CheckinCalendar from '@/components/CheckinCalendar.vue'


export default {
  name: 'Home',
  components: {
    InviteCodeDialog,
    RedeemCodeDialog,
    BindAccountDialog,
    CheckinCalendar,
  },
  data() {
    return {
      userStats: {
        credits: 0,
        watchTime: 0, // minutes
        ranking: 0,
      },
      checkedInToday: false,
      recentGames: [],
      recentActivities: [],
      systemStatus: {
        community_links: {
          group: '',
          channel: ''
        }
      }
    }
  },
  computed: {
    greeting() {
      const hour = new Date().getHours()
      if (hour < 6) return '夜深了，注意休息 🌙'
      if (hour < 12) return '早安，美好的一天开始了 ☀️'
      if (hour < 18) return '下午好，继续加油 ⚡'
      return '晚上好，放松一下吧 🌟'
    }
  },
  mounted() {
    this.loadUserData()
    this.loadRecentGames()
    this.loadRecentActivities()
    this.loadSystemStatus()
  },
  methods: {
    async loadUserData() {
      try {
        const response = await this.$apiClient.get('/api/user/dashboard')
        if (response.data.success) {
          this.userStats = {
            credits: response.data.data.credits || 0,
            watchTime: response.data.data.watchTime || 0,
            ranking: response.data.data.ranking || 0,
          }
        } else {
          console.error('加载用户数据失败:', response.data.error)
          this.userStats = { credits: 0, watchTime: 0, ranking: 0 }
        }
        this.checkedInToday = false
      } catch (error) {
        console.error('加载用户数据失败:', error)
        this.userStats = { credits: 0, watchTime: 0, ranking: 0 }
      }
    },

    async loadRecentGames() {
      try {
        const response = await this.$apiClient.get('/api/user/recent-games')
        if (response.data.success) {
          this.recentGames = response.data.games
        } else {
          console.error('加载最近游戏失败:', response.data.error)
          this.recentGames = []
        }
      } catch (error) {
        console.error('加载最近游戏失败:', error)
        this.recentGames = []
      }
    },

    async loadRecentActivities() {
      try {
        const response = await this.$apiClient.get('/api/user/recent-activities')
        if (response.data.success) {
          this.recentActivities = response.data.activities
        } else {
          console.error('加载最近动态失败:', response.data.error)
          this.recentActivities = []
        }
      } catch (error) {
        console.error('加载最近动态失败:', error)
        this.recentActivities = []
      }
    },

    formatWatchTime(minutes) {
      const hours = Math.floor(minutes / 60)
      const mins = minutes % 60
      if (hours === 0) return `${mins}分钟`
      if (mins === 0) return `${hours}小时`
      return `${hours}小时${mins}分`
    },

    navigateTo(destination) {
      // 所有游戏都在 Activities 视图中，使用 tab 参数区分
      this.$router.push({ name: 'activities', query: { tab: destination } })
    },

    // Quick Action Dialog Methods
    openInviteCodeDialog() {
      this.$refs.inviteCodeDialog.open()
    },

    openRedeemCodeDialog() {
      this.$refs.redeemCodeDialog.open()
    },

    openBindAccountDialog() {
      this.$refs.bindAccountDialog.open()
    },

    // Event Handlers for Quick Actions
    // eslint-disable-next-line no-unused-vars
    handleInviteCodeGenerated(code) {
      // Refresh user data after invite code is generated
      this.loadUserData()
    },

    // eslint-disable-next-line no-unused-vars
    handleCodeRedeemed(result) {
      // Refresh user data after code redemption
      this.loadUserData()
    },

    // eslint-disable-next-line no-unused-vars
    handleAccountBound(accountInfo) {
      // Refresh user data after account binding
      this.loadUserData()
    },

    async loadSystemStatus() {
      try {
        const response = await this.$apiClient.get('/api/system/status')
        // API 直接返回数据，不是 { success, data } 格式
        if (response.data) {
          this.systemStatus = {
            ...this.systemStatus,
            ...response.data
          }
        }
      } catch (error) {
        // Silently fail - community links are optional
      }
    },

    openCommunityLink(type) {
      let url = ''
      if (type === 'group') {
        url = this.systemStatus.community_links?.group || ''
      } else if (type === 'channel') {
        url = this.systemStatus.community_links?.channel || ''
      }
      if (url) {
        window.open(url, '_blank')
      }
    },

    async copyLinkUrl(type) {
      let url = ''
      if (type === 'group') {
        url = this.systemStatus.community_links?.group || ''
      } else if (type === 'channel') {
        url = this.systemStatus.community_links?.channel || ''
      }
      if (url) {
        try {
          await navigator.clipboard.writeText(url)
          this.$toast?.success?.('链接已复制') || alert('链接已复制')
        } catch {
          // Fallback for older browsers
          const textArea = document.createElement('textarea')
          textArea.value = url
          document.body.appendChild(textArea)
          textArea.select()
          document.execCommand('copy')
          document.body.removeChild(textArea)
          this.$toast?.success?.('链接已复制') || alert('链接已复制')
        }
      }
    }
  }
}
</script>

<style scoped lang="scss">
.home-view {
  padding: 0 0 calc(70px + var(--hbo-spacing-6)) 0; // Bottom padding for navigation bar
  min-height: 100vh;
  background: var(--hbo-bg-dark);
}

/* Hero Banner */
.hbo-hero-banner {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 24px var(--hbo-spacing-4) var(--hbo-spacing-6);
  margin-bottom: var(--hbo-spacing-2);
  overflow: visible;
  z-index: 1;
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
  z-index: 1;
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

/* Stats Section */
.stats-section {
  padding: 0 var(--hbo-spacing-4) var(--hbo-spacing-6);
}

.hbo-stat-card {
  background: var(--hbo-bg-card);
  border-radius: var(--hbo-radius-lg);
  padding: var(--hbo-spacing-4);
  display: flex;
  align-items: center;
  gap: var(--hbo-spacing-3);
  position: relative;
  overflow: hidden;
  transition: all var(--hbo-transition-base);
  box-shadow: var(--hbo-shadow-md);

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: linear-gradient(180deg, var(--hbo-purple-primary), var(--hbo-purple-deep));
    transition: width var(--hbo-transition-base);
  }

  &:hover::before {
    width: 8px;
  }
}

.stat-credits::before {
  background: linear-gradient(180deg, var(--hbo-gold), var(--hbo-gold-dark));
}

.stat-watchtime::before {
  background: linear-gradient(180deg, var(--hbo-cyan), var(--hbo-cyan-dark));
}

.stat-ranking::before {
  background: linear-gradient(180deg, var(--hbo-pink), var(--hbo-pink-dark));
}

.stat-icon-wrapper {
  width: 48px;
  height: 48px;
  border-radius: var(--hbo-radius-md);
  background: rgba(123, 44, 191, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon {
  font-size: 24px;
  color: var(--hbo-purple-light);
}

.stat-credits .stat-icon {
  color: var(--hbo-gold);
}

.stat-watchtime .stat-icon {
  color: var(--hbo-cyan);
}

.stat-ranking .stat-icon {
  color: var(--hbo-pink);
}

.stat-content {
  flex: 1;
}

.stat-label {
  font-size: 12px;
  color: var(--hbo-text-secondary);
  margin-bottom: 4px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--hbo-text-primary);
}

/* Section Title */
.section-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--hbo-text-primary);
  margin-bottom: var(--hbo-spacing-4);
  display: flex;
  align-items: center;
  gap: var(--hbo-spacing-2);
}

.title-icon {
  color: var(--hbo-gold);
  font-size: 24px;
}

/* Checkin Section */
.checkin-section {
  padding: 0 var(--hbo-spacing-4) var(--hbo-spacing-6);
}

/* Quick Actions Section */
.quick-actions-section {
  position: relative;
  z-index: 2;
  padding: 0 var(--hbo-spacing-4) var(--hbo-spacing-6);
  padding-top: 96px;
}

.hbo-action-card {
  background: var(--hbo-bg-card);
  border-radius: var(--hbo-radius-lg);
  padding: var(--hbo-spacing-4);
  text-align: center;
  cursor: pointer;
  transition: all var(--hbo-transition-base);
  box-shadow: var(--hbo-shadow-md);
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, var(--hbo-purple-primary), var(--hbo-purple-deep));
    transform: scaleX(0);
    transition: transform var(--hbo-transition-base);
  }

  &:hover {
    transform: translateY(-6px);
    box-shadow: var(--hbo-shadow-lg), var(--hbo-shadow-purple-glow);

    &::before {
      transform: scaleX(1);
    }
  }

  &:active {
    transform: translateY(-4px);
  }
}

.hbo-action-card:hover .action-icon-wrapper {
  transform: scale(1.1) rotate(5deg);
}

.action-icon-wrapper {
  width: 56px;
  height: 56px;
  border-radius: var(--hbo-radius-md);
  margin: 0 auto var(--hbo-spacing-3);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: all var(--hbo-transition-base);
}

.action-invite {
  background: linear-gradient(135deg, var(--hbo-purple-primary), var(--hbo-purple-deep));
  box-shadow: 0 4px 12px rgba(123, 44, 191, 0.3);
}

.action-redeem {
  background: linear-gradient(135deg, var(--hbo-pink), var(--hbo-pink-dark));
  box-shadow: 0 4px 12px rgba(255, 0, 110, 0.3);
}

.action-bind {
  background: linear-gradient(135deg, var(--hbo-cyan), var(--hbo-cyan-dark));
  box-shadow: 0 4px 12px rgba(6, 255, 165, 0.3);
}

.action-line {
  background: linear-gradient(135deg, var(--hbo-blue), var(--hbo-blue-dark));
  box-shadow: 0 4px 12px rgba(33, 150, 243, 0.3);
}

.action-icon {
  font-size: 28px;
  color: var(--hbo-text-primary);
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
}

.action-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--hbo-text-primary);
  margin-bottom: 4px;
  letter-spacing: 0.3px;
}

.action-hint {
  font-size: 11px;
  color: var(--hbo-text-secondary);
  font-weight: 500;
}

/* Continue Playing Section */
.continue-section {
  padding: 0 var(--hbo-spacing-4) var(--hbo-spacing-6);
}

.hbo-game-card {
  background: var(--hbo-bg-card);
  border-radius: var(--hbo-radius-xl);
  overflow: hidden;
  cursor: pointer;
  transition: all var(--hbo-transition-base);
  box-shadow: var(--hbo-shadow-lg);

  &:hover {
    transform: translateY(-8px);
    box-shadow: var(--hbo-shadow-2xl);

    .game-overlay {
      opacity: 1;
    }
  }
}

.game-thumbnail {
  position: relative;
  height: 180px;
  background-size: cover;
  background-position: center;
}

.wheel-bg {
  background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%),
              radial-gradient(circle at 50% 50%, rgba(255, 214, 10, 0.3), transparent);
  background-blend-mode: normal, overlay;
}

.blackjack-bg {
  background: linear-gradient(135deg, #E91E63 0%, #C2185B 100%),
              radial-gradient(circle at 50% 50%, rgba(255, 0, 110, 0.2), transparent);
  background-blend-mode: normal, overlay;
}

.auction-bg {
  background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%),
              radial-gradient(circle at 50% 50%, rgba(6, 255, 165, 0.2), transparent);
  background-blend-mode: normal, overlay;
}

.match-bg {
  background: linear-gradient(135deg, #4CAF50 0%, #388E3C 100%),
              radial-gradient(circle at 50% 50%, rgba(76, 175, 80, 0.2), transparent);
  background-blend-mode: normal, overlay;
}

.game-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity var(--hbo-transition-base);
}

.game-play-icon {
  font-size: 64px;
  color: var(--hbo-text-primary);
  filter: drop-shadow(0 4px 12px rgba(0, 0, 0, 0.6));
}

.game-badge {
  position: absolute;
  top: var(--hbo-spacing-2);
  right: var(--hbo-spacing-2);
}

.game-info {
  padding: var(--hbo-spacing-4);
}

.game-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--hbo-text-primary);
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.game-title-icon {
  color: var(--hbo-gold);
}

.game-desc {
  font-size: 13px;
  color: var(--hbo-text-secondary);
  margin-bottom: var(--hbo-spacing-3);
}

.game-meta {
  display: flex;
  gap: var(--hbo-spacing-2);
}

.game-progress {
  margin-top: var(--hbo-spacing-2);
}

.progress-label {
  font-size: 12px;
  color: var(--hbo-text-secondary);
  margin-bottom: 4px;
}

.game-progress-bar {
  margin-bottom: 4px;
}

.progress-text {
  font-size: 11px;
  color: var(--hbo-cyan);
  text-align: right;
  font-weight: 600;
}

/* Activity Section */
.activity-section {
  padding: 0 var(--hbo-spacing-4) var(--hbo-spacing-6);
}

.hbo-activity-list {
  background: var(--hbo-bg-card);
  border-radius: var(--hbo-radius-lg);
  overflow: hidden;
  box-shadow: var(--hbo-shadow-md);
}

.activity-item {
  display: flex;
  align-items: center;
  gap: var(--hbo-spacing-3);
  padding: var(--hbo-spacing-4);
  border-bottom: 1px solid var(--hbo-border-subtle);
  transition: background var(--hbo-transition-fast);

  &:last-child {
    border-bottom: none;
  }

  &:hover {
    background: rgba(123, 44, 191, 0.05);
  }
}

.activity-icon-wrapper {
  width: 40px;
  height: 40px;
  border-radius: var(--hbo-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.activity-checkin {
  background: rgba(6, 255, 165, 0.15);
}

.activity-game {
  background: rgba(123, 44, 191, 0.15);
}

.activity-wheel {
  background: rgba(255, 214, 10, 0.15);
}

.activity-auction {
  background: rgba(33, 150, 243, 0.15);
}

.activity-watch {
  background: rgba(123, 44, 191, 0.15);
}

.activity-match {
  background: rgba(255, 152, 0, 0.15);
}

.activity-blackjack {
  background: rgba(255, 0, 110, 0.15);
}

.activity-icon {
  font-size: 20px;
  color: var(--hbo-text-primary);
}

.activity-content {
  flex: 1;
  min-width: 0;
}

.activity-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--hbo-text-primary);
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.activity-time {
  font-size: 12px;
  color: var(--hbo-text-secondary);
}

.activity-value {
  font-size: 16px;
  font-weight: 700;
  flex-shrink: 0;
}

.value-positive {
  color: var(--hbo-cyan);
}

.value-negative {
  color: var(--hbo-pink);
}

.empty-state {
  padding: var(--hbo-spacing-8) var(--hbo-spacing-4);
  text-align: center;
}

.empty-icon {
  font-size: 64px;
  color: var(--hbo-text-disabled);
  margin-bottom: var(--hbo-spacing-2);
}

.empty-text {
  font-size: 14px;
  color: var(--hbo-text-secondary);
}

/* Responsive */
@media (max-width: 600px) {
  .hbo-hero-banner {
    padding: 20px var(--hbo-spacing-4) var(--hbo-spacing-5);
    margin-bottom: var(--hbo-spacing-3);
  }

  .hero-card {
    min-height: 0;
    padding: 36px 24px;
  }

  .hero-title {
    font-size: 24px;
  }

  .hero-icon {
    font-size: 28px;
  }

  .hero-subtitle {
    font-size: 14px;
  }

  .section-title {
    font-size: 18px;
  }

  .stat-value {
    font-size: 20px;
  }

  .game-thumbnail {
    height: 140px;
  }
}

/* Community Section */
.community-section {
  padding: 0 var(--hbo-spacing-4) var(--hbo-spacing-6);
}

.community-links-container {
  background: var(--hbo-bg-card);
  border-radius: var(--hbo-radius-lg);
  overflow: hidden;
  box-shadow: var(--hbo-shadow-md);
}

.community-link-item {
  display: flex;
  align-items: center;
  gap: var(--hbo-spacing-3);
  padding: var(--hbo-spacing-4);
  border-bottom: 1px solid var(--hbo-border-subtle);
  cursor: pointer;
  transition: all var(--hbo-transition-base);
  position: relative;

  &:last-child {
    border-bottom: none;
  }

  &:hover {
    background: rgba(123, 44, 191, 0.05);
    transform: translateX(4px);
  }
}

.link-icon-wrapper {
  width: 40px;
  height: 40px;
  border-radius: var(--hbo-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all var(--hbo-transition-base);
}

.group-link {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.channel-link {
  background: linear-gradient(135deg, #FF9800 0%, #FFB74D 100%);
  box-shadow: 0 4px 12px rgba(255, 152, 0, 0.3);
}

.community-link-item:hover .link-icon-wrapper {
  transform: scale(1.1);
}

.link-content {
  flex: 1;
  min-width: 0;
}

.link-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--hbo-text-primary);
  margin-bottom: 2px;
}

.link-description {
  font-size: 12px;
  color: var(--hbo-text-secondary);
}

.link-actions {
  display: flex;
  align-items: center;
  gap: var(--hbo-spacing-1);
}

.copy-link-btn {
  opacity: 0;
  transition: opacity var(--hbo-transition-base);
}

.community-link-item:hover .copy-link-btn {
  opacity: 1;
}

@media (min-width: 1280px) {
  .home-view {
    max-width: 1200px;
    margin: 0 auto;
  }
}
</style>
