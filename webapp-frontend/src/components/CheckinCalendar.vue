<template>
  <div class="checkin-wrap">
    <!-- 签到卡片 -->
    <v-card class="checkin-card mb-4" rounded="xl" elevation="0">
      <v-card-title class="checkin-header pa-5 pb-3">
        <div class="d-flex align-center justify-space-between w-100">
          <div class="d-flex align-center gap-2">
            <v-icon size="28" color="amber-lighten-1">mdi-calendar-check</v-icon>
            <span class="text-h6 font-weight-bold">每日签到</span>
          </div>
          <v-chip size="small" color="amber" variant="tonal">
            本月已签 {{ status.month_count }} 天
          </v-chip>
        </div>
      </v-card-title>

      <v-card-text class="pa-5 pt-2">
        <!-- 连续签到展示 -->
        <div class="streak-row mb-4">
          <div class="streak-num">{{ status.streak }}</div>
          <div class="streak-label">连续签到天数</div>
        </div>

        <div class="summary-grid mb-4">
          <div class="summary-card">
            <div class="summary-value">{{ status.total_count || 0 }}</div>
            <div class="summary-label">累计签到天数</div>
          </div>
          <div class="summary-card">
            <div class="summary-value">{{ status.total_rank ? `#${status.total_rank}` : '--' }}</div>
            <div class="summary-label">总榜排名</div>
          </div>
        </div>

        <!-- 奖励预告 -->
        <div class="reward-preview mb-4">
          <v-chip
            v-for="item in rewardMilestones"
            :key="item.day"
            :color="item.reached ? 'success' : 'grey-lighten-2'"
            :variant="item.reached ? 'elevated' : 'tonal'"
            class="ma-1"
            size="small"
          >
            <v-icon start size="14">{{ item.reached ? 'mdi-check-circle' : 'mdi-circle-outline' }}</v-icon>
            第{{ item.day }}天 +{{ item.reward }}分
          </v-chip>
        </div>

        <!-- 签到按钮 -->
        <v-btn
          v-if="statusReady && !status.checked_in_today && status.can_checkin"
          block
          color="amber-darken-2"
          size="large"
          rounded="xl"
          :loading="loading"
          @click="doCheckin"
          class="checkin-btn"
        >
          <v-icon start>mdi-hand-clap</v-icon>
          立即签到（+{{ nextReward }} 积分）
        </v-btn>
        <v-btn
          v-else-if="statusReady && status.checked_in_today"
          block
          color="success"
          size="large"
          rounded="xl"
          disabled
          variant="tonal"
        >
          <v-icon start>mdi-check-circle</v-icon>
          今日已签到 ✓
        </v-btn>
        <v-btn
          v-else-if="statusReady"
          block
          color="grey"
          size="large"
          rounded="xl"
          disabled
          variant="tonal"
        >
          <v-icon start>mdi-lock-outline</v-icon>
          {{ status.disabled_reason || '暂不可签到' }}
        </v-btn>
        <v-btn
          v-else
          block
          color="grey"
          size="large"
          rounded="xl"
          disabled
          variant="tonal"
        >
          <v-progress-circular indeterminate size="16" width="2" class="mr-2" />
          签到状态加载中...
        </v-btn>

        <!-- 签到结果 -->
        <v-expand-transition>
          <v-alert
            v-if="checkinResult"
            :type="checkinResult.success ? 'success' : 'warning'"
            class="mt-3"
            density="compact"
            variant="tonal"
            rounded="lg"
          >
            {{ checkinResult.message }}
            <div v-if="checkinResult.milestone" class="mt-1 font-weight-bold">
              🎉 {{ checkinResult.milestone }}
            </div>
          </v-alert>
        </v-expand-transition>
      </v-card-text>
    </v-card>

    <!-- 月度排行榜 -->
    <v-card rounded="xl" elevation="0">
      <v-card-title class="pa-5 pb-3">
        <div class="d-flex align-center gap-2">
          <v-icon color="deep-orange">mdi-trophy</v-icon>
          <span class="text-subtitle-1 font-weight-bold">本月签到前三</span>
          <v-chip size="x-small" color="amber" variant="tonal">TOP 3</v-chip>
          <v-chip size="x-small" color="grey" variant="tonal" class="ml-auto">{{ leaderboardMonth }}</v-chip>
        </div>
      </v-card-title>
      <v-card-text class="pa-5 pt-0">
        <div v-if="loadingLeaderboard" class="text-center py-4">
          <v-progress-circular indeterminate size="32" color="amber"></v-progress-circular>
        </div>
        <div v-else-if="leaderboard.length === 0" class="text-center text-grey py-4">
          本月暂无签到记录
        </div>
        <div v-else>
          <div
            v-for="(item, idx) in leaderboard"
            :key="item.tg_id"
            class="leaderboard-row"
            :class="{ 'top-row': idx < 3 }"
          >
            <div class="rank-badge">{{ ['🥇','🥈','🥉'][idx] || (idx + 1) }}</div>
            <div class="user-meta">
              <div class="user-name">{{ item.name }}</div>
              <UserMedals v-if="item.medals && item.medals.length" :medals="item.medals" compact />
            </div>
            <div class="days-badge">
              <v-chip size="x-small" :color="idx < 3 ? 'amber' : 'grey-lighten-2'" variant="tonal">
                {{ item.days }} 天
              </v-chip>
            </div>
          </div>
          <div class="mt-3 text-caption text-grey text-center">
            🏆 每月结算日前三名各获赠 20 积分
          </div>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script>
// uses this.$apiClient injected by main.js
import UserMedals from '@/components/UserMedals.vue'

export default {
  name: 'CheckinCalendar',
  components: {
    UserMedals,
  },
  data() {
    return {
      loading: false,
      loadingLeaderboard: true,
      statusReady: false,
      status: {
        checked_in_today: false,
        streak: 0,
        month_count: 0,
        total_count: 0,
        total_rank: null,
        next_reward: 1,
        can_checkin: false,
        disabled_reason: '',
      },
      checkinResult: null,
      leaderboard: [],
      leaderboardMonth: '',
    }
  },
  computed: {
    nextReward() {
      return this.status.next_reward || 1
    },
    rewardMilestones() {
      const streak = this.status.streak
      return [
        { day: 7,  reward: 3,  reached: streak >= 7 },
        { day: 14, reward: 5,  reached: streak >= 14 },
        { day: 30, reward: 10, reached: streak >= 30 },
      ]
    },
  },
  async mounted() {
    await Promise.all([this.loadStatus(), this.loadLeaderboard()])
  },
  methods: {
    async loadStatus() {
      try {
        const res = (await this.$apiClient.get('/api/checkin/status')).data
        if (res.success) this.status = res.data
      } catch (e) {
        console.error('loadStatus:', e)
        this.status = {
          checked_in_today: false,
          streak: 0,
          month_count: 0,
          total_count: 0,
          total_rank: null,
          next_reward: 1,
          can_checkin: false,
          disabled_reason: e.response?.data?.detail || '签到状态加载失败',
        }
      } finally {
        this.statusReady = true
      }
    },
    async loadLeaderboard() {
      this.loadingLeaderboard = true
      try {
        const res = (await this.$apiClient.get('/api/checkin/leaderboard')).data
        if (res.success) {
          this.leaderboard = (res.data || []).slice(0, 3)
          this.leaderboardMonth = res.month
        }
      } catch (e) { console.error('loadLeaderboard:', e) }
      finally { this.loadingLeaderboard = false }
    },
    async doCheckin() {
      this.loading = true
      this.checkinResult = null
      try {
        const res = (await this.$apiClient.post('/api/checkin')).data
        this.checkinResult = {
          success: res.success,
          message: res.success ? `签到成功！获得 +${res.data?.reward} 积分，连续 ${res.data?.streak} 天` : res.message,
          milestone: res.data?.milestone_msg || '',
        }
        if (res.success) {
          await this.loadStatus()
          await this.loadLeaderboard()
          this.$emit('credits-updated')
        }
      } catch (e) {
        this.checkinResult = {
          success: false,
          message: e.response?.data?.detail || e.response?.data?.message || '签到失败，请重试',
        }
        await this.loadStatus()
      } finally {
        this.loading = false
      }
    },
  },
}
</script>

<style scoped>
.checkin-wrap { color: var(--hbo-text-primary); }
.checkin-card { background: var(--hbo-bg-card) !important; border: 1px solid rgba(255,214,10,0.25) !important; }
.checkin-header { border-bottom: 1px solid var(--hbo-border-subtle) !important; }
.streak-row { text-align: center; }
.streak-num { font-size: 3rem; font-weight: 800; color: #ffb300; line-height: 1; }
.streak-label { font-size: 0.8rem; color: var(--hbo-text-secondary); margin-top: 4px; }
.summary-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.summary-card { padding: 14px 12px; border-radius: 16px; background: rgba(255,214,10,0.06); border: 1px solid rgba(255,214,10,0.14); text-align: center; }
.summary-value { font-size: 1.35rem; font-weight: 800; color: #ffd24a; line-height: 1.1; }
.summary-card .summary-label { margin-top: 6px; }
.reward-preview { display: flex; flex-wrap: wrap; justify-content: center; }
.checkin-btn { font-weight: 700; letter-spacing: 0.5px; }
.leaderboard-row { display: flex; align-items: flex-start; padding: 10px 0; border-bottom: 1px solid var(--hbo-border-subtle); gap: 12px; }
.leaderboard-row:last-child { border-bottom: none; }
.top-row { background: rgba(255,214,10,0.07); border-radius: 8px; padding: 10px 8px; margin: 2px 0; }
.rank-badge { font-size: 1.2rem; min-width: 28px; text-align: center; margin-top: 2px; }
.user-meta { flex: 1; min-width: 0; }
.user-name { flex: 1; font-weight: 500; font-size: 0.9rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--hbo-text-primary); }
.user-meta :deep(.user-medals.compact) { margin-top: 4px; }
.days-badge { margin-left: auto; align-self: center; }

@media (max-width: 420px) {
  .summary-grid { gap: 10px; }
  .summary-card { padding: 12px 10px; }
  .summary-value { font-size: 1.2rem; }
}
</style>
