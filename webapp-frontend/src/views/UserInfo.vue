<template>
  <div class="user-info-container">
    <!-- Hero Banner -->
    <div class="hbo-hero-banner">
      <div class="hero-gradient-overlay"></div>
      <div class="hero-card">
        <h1 class="hero-title">
          <v-icon class="hero-icon">mdi-account-circle</v-icon>
          用户中心
        </h1>
        <p class="hero-subtitle">账户信息与服务管理</p>
      </div>
    </div>

    <div class="content-wrapper">
      <v-container class="transparent-container">
      <div v-if="loading" class="loading-container">
        <div class="loading-content">
          <v-progress-circular 
            indeterminate 
            color="primary" 
            size="50"
            width="4"
          ></v-progress-circular>
          <div class="loading-text">加载中...</div>
        </div>
      </div>

      <div v-else-if="error" class="error-container">
        <v-alert 
          type="error" 
          class="error-alert"
          rounded="lg"
          elevation="4"
        >
          {{ error }}
        </v-alert>
      </div>

      <div v-else>
        <v-card class="user-info-card mb-4">
          <v-card-title class="card-title-section">
            <v-icon start color="primary">mdi-account-circle</v-icon> 个人信息
          </v-card-title>
          <v-card-text>
            <div class="d-flex justify-space-between mb-3 align-center">
              <div class="d-flex align-center">
                <v-icon size="small" color="info" class="mr-2">mdi-account-badge</v-icon>
                <span>昵称：</span>
              </div>
              <div class="value-display">{{ userInfo.display_name || '未设置' }}</div>
            </div>
            <div v-if="userInfo.medals && userInfo.medals.length" class="mb-3">
              <div class="d-flex align-center mb-2">
                <v-icon size="small" color="warning" class="mr-2">mdi-medal-outline</v-icon>
                <span>已拥有勋章：</span>
              </div>
              <UserMedals :medals="userInfo.medals" show-names />
            </div>
            <div class="d-flex justify-space-between mb-3 align-center">
              <div class="d-flex align-center">
                <v-icon size="small" color="primary" class="mr-2">mdi-star-circle</v-icon>
                <span>可用积分：</span>
              </div>
              <div class="d-flex">
                <v-btn
                  icon
                  size="x-small"
                  :color="creditsTransferEnabled ? 'amber-darken-2' : 'grey'"
                  variant="outlined"
                  @click="handleCreditsTransferClick"
                  :title="creditsTransferEnabled ? '积分转移' : '积分转移功能暂时关闭'"
                  class="mr-2 credits-transfer-btn"
                  :class="{ 'disabled-style': !creditsTransferEnabled }"
                >
                  <v-icon 
                    size="small" 
                    :class="{ 'text-grey-darken-2': !creditsTransferEnabled }"
                  >
                    {{ creditsTransferEnabled ? 'mdi-bank-transfer' : 'mdi-bank-transfer-out' }}
                  </v-icon>
                  <v-icon 
                    v-if="!creditsTransferEnabled" 
                    size="x-small" 
                    class="disable-icon"
                    color="error"
                  >
                    mdi-cancel
                  </v-icon>
                </v-btn>
                <div class="value-display credits-value">{{ userInfo.credits.toFixed(2) }}</div>
              </div>
            </div>
            <div class="d-flex justify-space-between mb-3 align-center">
              <div class="d-flex align-center">
                <v-icon size="small" color="success" class="mr-2">mdi-currency-usd</v-icon>
                <span>捐赠金额：</span>
              </div>
              <div class="value-display donation-value">{{ userInfo.donation.toFixed(2) }}</div>
            </div>
            <div class="d-flex justify-space-between mb-3 align-center">
              <div class="d-flex align-center">
                <v-icon size="small" color="warning" class="mr-2">mdi-brightness-percent</v-icon>
                <span>勋章加成：</span>
              </div>
              <div class="value-display">{{ Number(userInfo.medal_multiplier || 1).toFixed(2) }}x</div>
            </div>
            <div class="d-flex justify-space-between mb-3 align-center">
              <div class="d-flex align-center">
                <v-icon size="small" color="purple" class="mr-2">mdi-account-multiple</v-icon>
                <span>邀请人数：</span>
              </div>
              <div class="value-display invited-count-value">{{ userInfo.invited_count || 0 }}</div>
            </div>
            <v-divider class="my-3"></v-divider>

            <div v-if="userInfo.invitation_codes && userInfo.invitation_codes.length > 0">
              <div class="font-weight-bold mb-2 d-flex align-center">
                <v-icon size="small" color="info" class="mr-2">mdi-ticket-account</v-icon>
                <span>可用邀请码（3天有效）：</span>
              </div>
              <div v-for="(code, index) in userInfo.invitation_codes" :key="index" class="mb-2">
                <div class="invitation-code-row-horizontal">
                  <div class="invitation-code-container-horizontal">
                    <div class="invitation-code-with-tag">
                      <v-chip 
                        size="small" 
                        :color="privilegedCodes[index] ? 'amber-darken-2' : 'primary'"
                        @click="copyToClipboard(code)"
                        class="invitation-chip-horizontal"
                        elevation="2"
                        rounded="lg"
                        :title="code"
                      >
                        <span class="code-text">{{ code.length > 16 ? code.substring(0, 10) + '...' + code.substring(code.length - 4) : code }}</span>
                        <v-icon end icon="mdi-content-copy" size="small"></v-icon>
                      </v-chip>
                      <!-- 特权码提示文字 - 放在邀请码右侧 -->
                      <div v-if="privilegedCodes[index]" class="privilege-tag-horizontal">
                        <v-icon size="x-small" color="amber-darken-2">mdi-crown</v-icon>
                        <span class="privilege-text">特权</span>
                      </div>
                    </div>
                  </div>
                  <v-btn
                    size="x-small"
                    color="success"
                    variant="outlined"
                    @click="redeemCodeForCredits(code, index)"
                    :loading="redeemingCodes[index]"
                    :disabled="redeemingCodes[index]"
                    class="redeem-button-horizontal"
                    title="兑换为积分"
                  >
                    <v-icon size="small" start>mdi-star</v-icon>
                    兑换积分
                  </v-btn>
                </div>
              </div>
            </div>
            <div v-else class="text-center text-subtitle-2 my-2">
              <v-icon color="grey" class="mr-1">mdi-ticket-confirmation-outline</v-icon>
              暂无可用邀请码
            </div>
          </v-card-text>
        </v-card>

        <!-- Plex 账户信息 -->
        <v-card v-if="userInfo.plex_info" class="user-info-card mb-4 plex-account-card">
          <v-card-title class="card-title-section plex-title">
            <v-icon start color="orange-darken-2" class="plex-icon">mdi-plex</v-icon>
            <span class="service-title">Plex 账户</span>
          </v-card-title>
          <v-card-text>
            <div class="d-flex justify-space-between mb-2 align-center account-info-row">
              <div class="d-flex align-center info-label">
                <v-icon size="small" color="blue-darken-1" class="mr-2">mdi-account</v-icon>
                <span class="label-text">用户名</span>
              </div>
              <div class="d-flex align-center justify-end info-value">
                <span class="value-text">{{ userInfo.plex_info.username }}</span>

              </div>
            </div>
            <div class="d-flex justify-space-between mb-2 align-center account-info-row">
              <div class="d-flex align-center info-label">
                <v-icon size="small" color="red-darken-1" class="mr-2">mdi-email</v-icon>
                <span class="label-text">邮箱</span>
              </div>
              <div class="info-value">
                <span class="value-text">{{ userInfo.plex_info.email }}</span>
              </div>
            </div>
            <div class="d-flex justify-space-between mb-2 align-center account-info-row">
              <div class="d-flex align-center info-label">
                <v-icon size="small" color="purple-darken-1" class="mr-2">mdi-clock-time-four-outline</v-icon>
                <span class="label-text">观看等级</span>
              </div>
              <div class="d-flex align-center justify-end info-value" :title="`观看时长: ${userInfo.plex_info.watched_time.toFixed(2)}小时`">
                <template v-if="watchLevelIcons(userInfo.plex_info.watched_time).length > 0">
                  <div class="level-icons-container" @click="showWatchTimeDialog(userInfo.plex_info.watched_time)">
                    <span
                      v-for="(icon, index) in watchLevelIcons(userInfo.plex_info.watched_time)"
                      :key="`plex-icon-${index}`"
                      :class="['emoji-icon', icon.class]"
                    >
                      {{ icon.icon }}
                    </span>
                  </div>
                </template>
                <span v-else-if="showNoWatchTimeText(userInfo.plex_info.watched_time)" class="text-grey">暂无观看记录</span>
              </div>
            </div>
            <div class="d-flex justify-space-between mb-2 align-center account-info-row">
              <div class="d-flex align-center info-label">
                <v-icon size="small" color="indigo-darken-1" class="mr-2">mdi-folder-multiple</v-icon>
                <span class="label-text">资料库权限</span>
              </div>
              <v-chip
                :color="userInfo.plex_info.all_lib ? 'success' : 'warning'"
                size="small"
                elevation="1"
              >
                {{ userInfo.plex_info.all_lib ? '全部' : '部分' }}
              </v-chip>
            </div>



          </v-card-text>
        </v-card>

        <!-- Emby 账户信息 -->
        <v-card v-if="userInfo.emby_info" class="user-info-card mb-4 emby-account-card">
          <v-card-title class="card-title-section emby-title">
            <v-icon start color="green-darken-2" class="emby-icon">mdi-emby</v-icon>
            <span class="service-title">Emby 账户</span>
          </v-card-title>
          <v-card-text>
            <div class="d-flex justify-space-between mb-2 align-center account-info-row">
              <div class="d-flex align-center info-label">
                <v-icon size="small" color="blue-darken-1" class="mr-2">mdi-account</v-icon>
                <span class="label-text">用户名</span>
              </div>
              <div class="d-flex align-center justify-end info-value">
                <span class="value-text">{{ userInfo.emby_info.username }}</span>
              </div>
            </div>
            <div v-if="userInfo.emby_info.created_at" class="d-flex justify-space-between mb-2 align-center account-info-row">
              <div class="d-flex align-center info-label">
                <v-icon size="small" color="pink-darken-1" class="mr-2">mdi-cake-variant</v-icon>
                <span class="label-text">破壳日</span>
              </div>
              <div class="info-value">
                <span class="value-text">{{ userInfo.emby_info.created_at }}</span>
              </div>
            </div>
            <div class="d-flex justify-space-between mb-2 align-center account-info-row">
              <div class="d-flex align-center info-label">
                <v-icon size="small" color="purple-darken-1" class="mr-2">mdi-clock-time-four-outline</v-icon>
                <span class="label-text">观看等级</span>
              </div>
              <div class="d-flex align-center justify-end info-value" :title="`观看时长: ${userInfo.emby_info.watched_time.toFixed(2)}小时`">
                <template v-if="watchLevelIcons(userInfo.emby_info.watched_time).length > 0">
                  <div class="level-icons-container" @click="showWatchTimeDialog(userInfo.emby_info.watched_time)">
                    <span
                      v-for="(icon, index) in watchLevelIcons(userInfo.emby_info.watched_time)"
                      :key="`emby-icon-${index}`"
                      :class="['emoji-icon', icon.class]"
                    >
                      {{ icon.icon }}
                    </span>
                  </div>
                </template>
                <span v-else-if="showNoWatchTimeText(userInfo.emby_info.watched_time)" class="text-grey">暂无观看记录</span>
              </div>
            </div>
            <div class="d-flex justify-space-between mb-2 align-center account-info-row">
              <div class="d-flex align-center info-label">
                <v-icon size="small" color="indigo-darken-1" class="mr-2">mdi-folder-multiple</v-icon>
                <span class="label-text">资料库权限</span>
              </div>
              <v-chip
                :color="userInfo.emby_info.all_lib ? 'success' : 'warning'"
                size="small"
                elevation="1"
              >
                {{ userInfo.emby_info.all_lib ? '全部' : '部分' }}
              </v-chip>
            </div>
            <div class="d-flex justify-space-between mb-2 align-center entrance-url-row account-info-row">
              <div class="d-flex align-center info-label">
                <v-icon size="small" color="deep-orange-darken-1" class="mr-2">mdi-web</v-icon>
                <span class="label-text">入口线路</span>
              </div>
              <div
                class="entrance-url-chip"
                @click="copyToClipboard(systemStatus.emby_entry_url)"
                title="点击复制线路地址"
              >
                {{ systemStatus.emby_entry_url }}
                <v-icon size="x-small" class="ml-1">mdi-content-copy</v-icon>
              </div>
            </div>


                      </v-card-text>
        </v-card>

        <!-- Overseerr 账户信息 -->
        <v-card v-if="userInfo.overseerr_info" class="user-info-card mb-4">
          <v-card-title class="card-title-section">
            <v-icon start color="blue-darken-2">mdi-movie-search</v-icon> Overseerr 账户
          </v-card-title>
          <v-card-text>
            <div class="d-flex justify-space-between mb-2 align-center">
              <div class="d-flex align-center">
                <v-icon size="small" color="red-darken-1" class="mr-2">mdi-email</v-icon>
                <span>邮箱：</span>
              </div>
              <div>{{ userInfo.overseerr_info.email }}</div>
            </div>
          </v-card-text>
        </v-card>

        <!-- 个人活动数据卡片 -->
        <v-card class="user-info-card mb-4">
          <v-card-title class="card-title-section">
            <v-icon start color="deep-purple-darken-2">mdi-chart-line</v-icon> 个人活动数据
          </v-card-title>
          <v-card-text>
            <!-- 幸运大转盘数据 -->
            <div class="activity-section">
              <div class="section-header">
                <v-icon size="small" color="purple-darken-1" class="mr-2">mdi-wheel-barrow</v-icon>
                <span class="section-title">幸运大转盘</span>
              </div>
              
              <div v-if="activityLoading" class="activity-loading">
                <v-progress-circular 
                  indeterminate 
                  color="primary" 
                  size="30"
                  width="3"
                ></v-progress-circular>
                <span class="ml-2">加载中...</span>
              </div>
              
              <div v-else class="activity-stats-grid">
                <!-- 今日数据 -->
                <div class="stats-card today-stats">
                  <div class="stats-card-header">
                    <v-icon size="small" color="orange-darken-2">mdi-weather-sunny</v-icon>
                    <span>今日数据</span>
                  </div>
                  <div class="stats-items">
                    <div class="stat-item">
                      <span class="stat-label">游戏次数</span>
                      <span class="stat-value today-value">{{ activityStats.today_spins }}</span>
                    </div>
                    <div class="stat-item">
                      <span class="stat-label">积分变化</span>
                      <span 
                        class="stat-value today-value"
                        :class="activityStats.today_credits_change >= 0 ? 'positive' : 'negative'"
                      >
                        {{ activityStats.today_credits_change >= 0 ? '+' : '' }}{{ activityStats.today_credits_change.toFixed(1) }}
                      </span>
                    </div>
                    <div class="stat-item">
                      <span class="stat-label">邀请码获得</span>
                      <span class="stat-value today-value">{{ activityStats.today_invite_codes }}</span>
                    </div>
                  </div>
                </div>

                <!-- 总计数据 -->
                <div class="stats-card total-stats">
                  <div class="stats-card-header">
                    <v-icon size="small" color="green-darken-2">mdi-chart-box</v-icon>
                    <span>历史总计</span>
                  </div>
                  <div class="stats-items">
                    <div class="stat-item">
                      <span class="stat-label">游戏次数</span>
                      <span class="stat-value total-value">{{ activityStats.total_spins }}</span>
                    </div>
                    <div class="stat-item">
                      <span class="stat-label">积分变化</span>
                      <span 
                        class="stat-value total-value"
                        :class="activityStats.total_credits_change >= 0 ? 'positive' : 'negative'"
                      >
                        {{ activityStats.total_credits_change >= 0 ? '+' : '' }}{{ activityStats.total_credits_change.toFixed(1) }}
                      </span>
                    </div>
                    <div class="stat-item">
                      <span class="stat-label">邀请码获得</span>
                      <span class="stat-value total-value">{{ activityStats.total_invite_codes }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 21点游戏数据 -->
            <div class="activity-section mt-4">
              <div class="section-header">
                <v-icon size="small" color="purple-darken-1" class="mr-2">mdi-cards</v-icon>
                <span class="section-title">21点</span>
              </div>

              <div v-if="blackjackLoading" class="activity-loading">
                <v-progress-circular
                  indeterminate
                  color="primary"
                  size="30"
                  width="3"
                ></v-progress-circular>
                <span class="ml-2">加载中...</span>
              </div>

              <div v-else class="activity-stats-grid">
                <!-- 今日数据 -->
                <div class="stats-card today-stats">
                  <div class="stats-card-header">
                    <v-icon size="small" color="orange-darken-2">mdi-weather-sunny</v-icon>
                    <span>今日数据</span>
                  </div>
                  <div class="stats-items">
                    <div class="stat-item">
                      <span class="stat-label">游戏次数</span>
                      <span class="stat-value today-value">{{ blackjackStats.today_games }}</span>
                    </div>
                    <div class="stat-item">
                      <span class="stat-label">积分变化</span>
                      <span
                        class="stat-value today-value"
                        :class="blackjackStats.today_credits_change >= 0 ? 'positive' : 'negative'"
                      >
                        {{ blackjackStats.today_credits_change >= 0 ? '+' : '' }}{{ blackjackStats.today_credits_change.toFixed(1) }}
                      </span>
                    </div>
                    <div class="stat-item">
                      <span class="stat-label">胜场数</span>
                      <span class="stat-value today-value">{{ blackjackStats.today_wins }}</span>
                    </div>
                  </div>
                </div>

                <!-- 总计数据 -->
                <div class="stats-card total-stats">
                  <div class="stats-card-header">
                    <v-icon size="small" color="green-darken-2">mdi-chart-box</v-icon>
                    <span>历史总计</span>
                  </div>
                  <div class="stats-items">
                    <div class="stat-item">
                      <span class="stat-label">游戏次数</span>
                      <span class="stat-value total-value">{{ blackjackStats.total_games }}</span>
                    </div>
                    <div class="stat-item">
                      <span class="stat-label">积分变化</span>
                      <span
                        class="stat-value total-value"
                        :class="blackjackStats.total_credits_change >= 0 ? 'positive' : 'negative'"
                      >
                        {{ blackjackStats.total_credits_change >= 0 ? '+' : '' }}{{ blackjackStats.total_credits_change.toFixed(1) }}
                      </span>
                    </div>
                    <div class="stat-item">
                      <span class="stat-label">胜场数</span>
                      <span class="stat-value total-value">{{ blackjackStats.total_wins }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 最近游戏记录 - 合并显示所有游戏的记录 -->
            <div v-if="hasAnyRecentGames" class="activity-section mt-4">
              <v-divider class="mb-3"></v-divider>
              <div class="section-header">
                <v-icon size="small" color="indigo-darken-1" class="mr-2">mdi-history</v-icon>
                <span class="section-title">最近游戏记录</span>
              </div>

              <!-- 幸运转盘记录 -->
              <div v-if="!activityLoading && activityStats.recent_games && activityStats.recent_games.length > 0" class="recent-games-list mb-3">
                <div class="game-category-title">幸运大转盘</div>
                <div
                  v-for="(game, index) in activityStats.recent_games"
                  :key="'wheel-' + index"
                  class="recent-game-item"
                >
                  <div class="game-result">
                    <v-chip
                      size="small"
                      :color="getGameResultColor(game.item_name)"
                      class="game-chip"
                      :title="game.item_name"
                    >
                      {{ game.item_name }}
                    </v-chip>
                  </div>
                  <div class="game-change">
                    <span
                      class="change-value"
                      :class="game.credits_change >= 0 ? 'positive' : 'negative'"
                    >
                      {{ game.credits_change >= 0 ? '+' : '' }}{{ game.credits_change }}
                    </span>
                  </div>
                  <div class="game-date">
                    {{ formatGameDate(game.date) }}
                  </div>
                </div>
              </div>

              <!-- 21点记录 -->
              <div v-if="!blackjackLoading && blackjackStats.recent_games && blackjackStats.recent_games.length > 0" class="recent-games-list mb-3">
                <div class="game-category-title">21点</div>
                <div
                  v-for="(game, index) in blackjackStats.recent_games"
                  :key="'blackjack-' + index"
                  class="recent-game-item"
                >
                  <div class="game-result">
                    <v-chip
                      size="small"
                      :color="getBlackjackResultColor(game.result)"
                      class="game-chip"
                      :title="getBlackjackResultText(game.result)"
                    >
                      {{ getBlackjackResultText(game.result) }}
                    </v-chip>
                  </div>
                  <div class="game-change">
                    <span
                      class="change-value"
                      :class="game.credits_change >= 0 ? 'positive' : 'negative'"
                    >
                      {{ game.credits_change >= 0 ? '+' : '' }}{{ game.credits_change }}
                    </span>
                  </div>
                  <div class="game-date">
                    {{ formatGameDate(game.date) }}
                  </div>
                </div>
              </div>

            </div>
          </v-card-text>
        </v-card>

        <div v-if="!userInfo.plex_info && !userInfo.emby_info" class="no-accounts-message">
          <v-alert 
            type="info" 
            class="info-alert"
            rounded="lg"
            elevation="4"
          >
            <v-icon start>mdi-information</v-icon>
            您尚未绑定任何媒体服务账户，请先进行绑定
          </v-alert>
        </div>
      </div>
      </v-container>
    </div>
    
    <!-- 使用捐赠对话框组件 -->
    <donation-dialog
      ref="donationDialog"
      @donation-submitted="handleDonationSubmitted"
    />
    
    <!-- 使用积分转移对话框组件 -->
    <credits-transfer-dialog
      ref="creditsTransferDialog"
      :current-credits="userInfo.credits"
      @transfer-completed="handleCreditsTransferCompleted"
    />
    
    <!-- 邀请码生成对话框 -->
    <invite-code-dialog
      ref="inviteCodeDialog"
      @code-generated="handleInviteCodeGenerated"
    />

    <!-- 兑换码对话框 -->
    <redeem-code-dialog
      ref="redeemCodeDialog"
      @code-redeemed="handleCodeRedeemed"
    />

    <!-- 绑定账户对话框 -->
    <bind-account-dialog
      ref="bindAccountDialog"
      @account-bound="handleAccountBound"
    />

  </div>
</template>

<script>
import { getUserInfo } from '@/api'
import { getSystemStatus } from '@/services/systemService'
import DonationDialog from '@/components/DonationDialog.vue'
import CreditsTransferDialog from '@/components/CreditsTransferDialog.vue'
import InviteCodeDialog from '@/components/InviteCodeDialog.vue'
import RedeemCodeDialog from '@/components/RedeemCodeDialog.vue'
import BindAccountDialog from '@/components/BindAccountDialog.vue'
import UserMedals from '@/components/UserMedals.vue'
import { getWatchLevelIcons, showNoWatchTimeText } from '@/utils/watchLevel.js'
import { redeemInviteCodeForCredits } from '@/services/inviteCodeService.js'
import { checkPrivilegedInviteCode } from '@/services/mediaServiceApi.js'
import { getUserActivityStats } from '@/services/wheelService.js'
import { getUserBlackjackStats } from '@/services/blackjackService.js'

export default {
  name: 'UserInfo',
  components: {
    DonationDialog,
    CreditsTransferDialog,
    InviteCodeDialog,
    RedeemCodeDialog,
    BindAccountDialog,
    UserMedals,
  },
  data() {
    return {
      userInfo: {
        display_name: '',
        credits: 0,
        donation: 0,
        medal_multiplier: 1,
        medals: [],
        invitation_codes: [],
        plex_info: null,
        emby_info: null,
        overseerr_info: null,
        is_admin: false
      },
      loading: true,
      error: null,
      redeemingCodes: {}, // 用于跟踪每个邀请码的兑换状态
      privilegedCodes: {}, // 用于跟踪特权邀请码状态
      activityStats: {
        today_spins: 0,
        total_spins: 0,
        week_spins: 0,
        total_credits_change: 0.0,
        today_credits_change: 0.0,
        week_credits_change: 0.0,
        total_invite_codes: 0,
        today_invite_codes: 0,
        week_invite_codes: 0,
        recent_games: []
      },
      blackjackStats: {
        today_games: 0,
        week_games: 0,
        total_games: 0,
        today_credits_change: 0.0,
        week_credits_change: 0.0,
        total_credits_change: 0.0,
        today_wins: 0,
        week_wins: 0,
        total_wins: 0,
        recent_games: []
      },
      activityLoading: false,
      blackjackLoading: false,
      systemStatus: {
        site_name: '', // 默认值，从后端获取后会更新
        emby_entry_url: '', // 默认值，从后端获取后会更新

        community_links: {
          group: '',
          channel: ''
        }
      },
      creditsTransferEnabled: true, // 积分转移功能开关状态

    }
  },
  computed: {
    hasAnyRecentGames() {
      return (
        (!this.activityLoading && this.activityStats.recent_games && this.activityStats.recent_games.length > 0) ||
        (!this.blackjackLoading && this.blackjackStats.recent_games && this.blackjackStats.recent_games.length > 0)
      )
    }
  },
  mounted() {
    this.fetchUserInfo()
    this.fetchActivityStats()
    this.fetchBlackjackStats()
    this.fetchSystemStatus() // 这里会同时获取系统状态和积分转移开关状态
  },
  methods: {
    // Quick Actions Dialog Methods
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
      // Refresh user info to show new invite code
      this.fetchUserInfo()
    },

    // eslint-disable-next-line no-unused-vars
    handleCodeRedeemed(result) {
      // Refresh user info after code redemption
      this.fetchUserInfo()
    },

    // eslint-disable-next-line no-unused-vars
    handleAccountBound(accountInfo) {
      // Refresh user info after account binding
      this.fetchUserInfo()
    },

    async fetchUserInfo() {
      try {
        this.loading = true
        const response = await getUserInfo()
        this.userInfo = response.data
        
        // 检查每个邀请码的特权状态
        if (this.userInfo.invitation_codes && this.userInfo.invitation_codes.length > 0) {
          await this.checkPrivilegedCodes()
        }
        
        this.loading = false
      } catch (err) {
        this.error = err.response?.data?.detail || '获取用户信息失败'
        this.loading = false
        console.error('获取用户信息失败:', err)
      }
    },

    // 获取活动数据
    async fetchActivityStats() {
      try {
        this.activityLoading = true
        const response = await getUserActivityStats()
        if (response.data && response.data.success) {
          this.activityStats = response.data.data
        }
      } catch (err) {
        console.error('获取活动统计数据失败:', err)
        // 不显示错误，使用默认值
      } finally {
        this.activityLoading = false
      }
    },

    // 获取21点游戏数据
    async fetchBlackjackStats() {
      try {
        this.blackjackLoading = true
        const response = await getUserBlackjackStats()
        if (response.data && response.data.success) {
          this.blackjackStats = response.data.data
        }
      } catch (err) {
        console.error('获取21点统计数据失败:', err)
        // 不显示错误，使用默认值
      } finally {
        this.blackjackLoading = false
      }
    },

    // 获取系统状态
    async fetchSystemStatus() {
      try {
        const response = await getSystemStatus()
        this.systemStatus = response
        // 同时获取积分转移开关状态
        this.creditsTransferEnabled = response.credits_transfer_enabled !== undefined ? 
          response.credits_transfer_enabled : true
      } catch (err) {
        console.error('获取系统状态失败:', err)
        // 使用默认值，不影响用户体验
        this.creditsTransferEnabled = true
      }
    },

    // 检查特权邀请码
    async checkPrivilegedCodes() {
      // 重置特权码状态映射
      this.privilegedCodes = {};
      
      for (let i = 0; i < this.userInfo.invitation_codes.length; i++) {
        const code = this.userInfo.invitation_codes[i]
        try {
          const result = await checkPrivilegedInviteCode(code)
          this.privilegedCodes[i] = result.privileged
        } catch (error) {
          console.error(`检查邀请码 ${code} 特权状态失败:`, error)
          this.privilegedCodes[i] = false
        }
      }
    },
    
    showMessage(message, type = 'success') {
      if (window.Telegram?.WebApp) {
        window.Telegram.WebApp.showPopup({
          title: type === 'error' ? '错误' : '成功',
          message: message
        })
      } else {
        alert(message)
      }
    },
    copyToClipboard(text) {
      navigator.clipboard.writeText(text).then(() => {
        if (window.Telegram?.WebApp) {
          window.Telegram.WebApp.showPopup({
            title: '复制成功',
            message: '已复制到剪贴板'
          })
        } else {
          alert('已复制到剪贴板')
        }
      }).catch(err => {
        console.error('复制失败:', err)
      })
    },

    // 兑换邀请码为积分
    async redeemCodeForCredits(code, index) {
      // 显示确认提示框
      const confirmed = await this.showConfirmDialog(
        '确认兑换',
        `确定要兑换邀请码 "${code}" 为积分吗？\n\n兑换后将获得该邀请码价值 80% 的积分，且邀请码将被消耗。`
      );

      if (!confirmed) {
        return; // 用户取消了操作
      }

      try {
        // 设置加载状态
        this.redeemingCodes[index] = true;
        
        const response = await redeemInviteCodeForCredits(code);
        
        if (response.success) {
          // 更新用户积分
          this.userInfo.credits = response.current_credits;
          
          // 从邀请码列表中移除已兑换的邀请码
          this.userInfo.invitation_codes.splice(index, 1);
          
          // 更新特权码状态映射 - 移除对应索引，并重新映射后续索引
          const newPrivilegedCodes = {};
          Object.keys(this.privilegedCodes).forEach(key => {
            const keyIndex = parseInt(key);
            if (keyIndex < index) {
              // 保持原索引
              newPrivilegedCodes[keyIndex] = this.privilegedCodes[keyIndex];
            } else if (keyIndex > index) {
              // 索引向前移动
              newPrivilegedCodes[keyIndex - 1] = this.privilegedCodes[keyIndex];
            }
            // 跳过被删除的索引
          });
          this.privilegedCodes = newPrivilegedCodes;
          
          // 同样更新兑换状态映射
          const newRedeemingCodes = {};
          Object.keys(this.redeemingCodes).forEach(key => {
            const keyIndex = parseInt(key);
            if (keyIndex < index) {
              newRedeemingCodes[keyIndex] = this.redeemingCodes[keyIndex];
            } else if (keyIndex > index) {
              newRedeemingCodes[keyIndex - 1] = this.redeemingCodes[keyIndex];
            }
          });
          this.redeemingCodes = newRedeemingCodes;
          
          // 显示成功消息
          const message = `成功兑换！获得 ${response.credits_earned.toFixed(2)} 积分`;
          this.showMessage(message, 'success');
          
          if (window.Telegram?.WebApp) {
            window.Telegram.WebApp.showPopup({
              title: '兑换成功',
              message: message
            });
          }
        } else {
          // 显示错误消息
          this.showMessage(response.message, 'error');
        }
      } catch (error) {
        console.error('兑换邀请码失败:', error);
        this.showMessage('兑换失败，请稍后重试', 'error');
      } finally {
        // 清除加载状态
        if (this.redeemingCodes[index] !== undefined) {
          this.redeemingCodes[index] = false;
        }
      }
    },

    // 显示确认对话框
    showConfirmDialog(title, message) {
      return new Promise((resolve) => {
        if (window.Telegram?.WebApp) {
          // 在 Telegram 环境中使用原生确认对话框
          window.Telegram.WebApp.showConfirm(message, (confirmed) => {
            resolve(confirmed);
          });
        } else {
          // 在开发环境中使用浏览器的 confirm
          const confirmed = confirm(`${title}\n\n${message}`);
          resolve(confirmed);
        }
      });
    },


    // 使用导入的方法获取观看等级图标
    watchLevelIcons(watchedTime) {
      return getWatchLevelIcons(watchedTime);
    },
    
    // 检查是否显示"暂无观看记录"文本
    showNoWatchTimeText(watchedTime) {
      return showNoWatchTimeText(watchedTime);
    },

    // 显示观看时长对话框
    showWatchTimeDialog(watchedTime) {
      const message = `观看时长：${watchedTime.toFixed(2)} 小时`;
      
      if (window.Telegram?.WebApp) {
        window.Telegram.WebApp.showPopup({
          title: '观看时长信息',
          message: message
        });
      } else {
        alert(message);
      }
    },
    
    // 打开捐赠对话框
    openDonationDialog() {
      this.$refs.donationDialog.open();
    },
    
    // 处理积分转移按钮点击事件
    handleCreditsTransferClick() {
      if (!this.creditsTransferEnabled) {
        // 功能关闭时显示提示
        this.showMessage('积分转移功能暂时关闭', 'error')
        return
      }
      
      // 功能开启时正常打开对话框
      this.openCreditsTransferDialog()
    },
    
    // 打开积分转移对话框
    openCreditsTransferDialog() {
      this.$refs.creditsTransferDialog.open();
    },
    
    // 处理积分转移完成事件
    handleCreditsTransferCompleted(result) {
      const { amount, target_user, current_credits } = result;
      
      // 更新用户积分
      this.userInfo.credits = current_credits;
      
      // 显示成功消息
      this.showMessage(`成功转移 ${amount} 积分给用户 ${target_user}`, 'success');
    },
    
    // 处理捐赠提交事件
    handleDonationSubmitted() {
      // 重新获取用户信息以更新捐赠金额
      this.fetchUserInfo();
    },
    
    
    // 根据游戏结果获取颜色
    getGameResultColor(itemName) {
      if (itemName.includes('邀请码')) {
        return 'amber-darken-2'
      } else if (itemName.includes('+')) {
        return 'success'
      } else if (itemName.includes('-')) {
        return 'error'
      } else if (itemName.includes('翻倍')) {
        return 'purple'
      } else if (itemName.includes('减半')) {
        return 'orange-darken-2'
      } else {
        return 'grey'
      }
    },

    // 格式化游戏日期
    formatGameDate(dateString) {
      try {
        const today = new Date().toDateString()
        const gameDate = new Date(dateString).toDateString()

        if (today === gameDate) {
          return '今天'
        }

        const yesterday = new Date()
        yesterday.setDate(yesterday.getDate() - 1)
        if (yesterday.toDateString() === gameDate) {
          return '昨天'
        }

        return dateString
      } catch (error) {
        return dateString
      }
    },

    // 获取21点游戏结果颜色
    getBlackjackResultColor(result) {
      const colorMap = {
        'win': 'success',
        'blackjack': 'purple',
        'dealer_bust': 'success',
        'lose': 'error',
        'bust': 'error',
        'push': 'warning'
      }
      return colorMap[result] || 'grey'
    },

    // 获取21点游戏结果文本
    getBlackjackResultText(result) {
      const textMap = {
        'win': '胜利',
        'blackjack': '黑杰克',
        'dealer_bust': '庄家爆牌',
        'lose': '失败',
        'bust': '爆牌',
        'push': '平局'
      }
      return textMap[result] || result
    },
    // 打开社区链接
    openCommunityLink(type) {
      let url = '';
      let title = '';
      
      if (type === 'group') {
        url = this.systemStatus.community_links?.group || '';
        title = '用户交流群';
      } else if (type === 'channel') {
        url = this.systemStatus.community_links?.channel || '';
        title = '官方通知频道';
      }

      if (url) {
        if (window.Telegram?.WebApp) {
          // 在 Telegram 环境中打开链接
          window.Telegram.WebApp.openTelegramLink(url);
          this.showMessage(`正在打开${title}...`, 'success');
        } else {
          // 在浏览器环境中的处理
          try {
            // 尝试直接打开链接
            const newWindow = window.open(url, '_blank', 'noopener,noreferrer');
            
            // 检查是否被弹窗拦截器拦截
            if (!newWindow || newWindow.closed || typeof newWindow.closed == 'undefined') {
              // 被拦截，显示手动打开提示
              this.showBrowserLinkDialog(url, title);
            } else {
              // 成功打开
              this.showMessage(`正在打开${title}...`, 'success');
            }
          } catch (error) {
            console.error('打开链接失败:', error);
            // 出错时也显示手动打开提示
            this.showBrowserLinkDialog(url, title);
          }
        }
      } else {
        this.showMessage(`${title}链接暂未配置`, 'error');
      }
    },

    // 在浏览器中显示链接对话框（用于被弹窗拦截的情况）
    showBrowserLinkDialog(url, title) {
      // 创建一个简单的确认对话框
      const message = `浏览器阻止了弹窗，请手动打开${title}：\n\n${url}\n\n点击确定复制链接到剪贴板`;
      
      if (confirm(message)) {
        // 用户确认后复制链接到剪贴板
        this.copyToClipboard(url);
        this.showMessage('链接已复制到剪贴板，请手动打开', 'success');
      }
    },

    // 复制社区链接URL
    copyLinkUrl(type) {
      let url = '';
      let title = '';
      
      if (type === 'group') {
        url = this.systemStatus.community_links?.group || '';
        title = '用户交流群';
      } else if (type === 'channel') {
        url = this.systemStatus.community_links?.channel || '';
        title = '官方通知频道';
      }

      if (url) {
        this.copyToClipboard(url);
        this.showMessage(`${title}链接已复制`, 'success');
      } else {
        this.showMessage(`${title}链接暂未配置`, 'error');
      }
    },

    // 显示链接右键菜单
    showLinkContextMenu(type, event) {
      // 阻止默认右键菜单
      event.preventDefault();
      
      let title = type === 'group' ? '用户交流群' : '官方通知频道';
      
      // 在非Telegram环境中提供复制选项
      if (!window.Telegram?.WebApp) {
        const message = `${title}选项：\n1. 打开链接\n2. 复制链接\n\n请选择操作（确定=打开链接，取消=复制链接）`;
        
        if (confirm(message)) {
          this.openCommunityLink(type);
        } else {
          this.copyLinkUrl(type);
        }
      }
    },
  }
}
</script>

<style scoped>
.user-info-container {
  min-height: 100vh;
  background: var(--hbo-bg-dark);
  padding: 0;
  padding-bottom: calc(70px + var(--hbo-spacing-6)); /* 为底部导航栏留出空间 */
}

.content-wrapper {
  max-width: 800px;
  margin: 0 auto;
  padding: var(--hbo-spacing-6) var(--hbo-spacing-4) 0;
}

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

.transparent-container {
  background: transparent !important;
  padding: 0 !important;
}

/* 加载状态样式 */
.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
  padding: 40px;
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 30px;
  background: rgba(var(--v-theme-surface), 0.95);
  border-radius: 16px;
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
}

.loading-text {
  font-size: 14px;
  color: rgba(var(--v-theme-on-surface), 0.7);
  font-weight: 500;
}

/* 错误状态样式 */
.error-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
  padding: 20px;
}

.error-alert {
  background: rgba(255, 255, 255, 0.95) !important;
  backdrop-filter: blur(10px);
  border: none !important;
  max-width: 500px;
}

.user-info-card {
  background: rgba(var(--v-theme-surface), 0.95);
  border-radius: 16px;
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  border: none;
}

.user-info-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 15px 35px rgba(0, 0, 0, 0.15);
}

.card-title-section {
  text-align: center;
  font-size: 18px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface));
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  backdrop-filter: blur(10px);
  border-radius: 16px 16px 0 0;
  border-bottom: 1px solid rgba(102, 126, 234, 0.2);
  padding: 20px 24px 16px;
}

/* 确保卡片内容左对齐 */
.user-info-card .v-card-text {
  text-align: left;
  padding: 24px;
}

/* 无账户消息样式 */
.no-accounts-message {
  text-align: center;
  margin: 40px 0;
}

.info-alert {
  background: rgba(255, 255, 255, 0.95) !important;
  backdrop-filter: blur(10px);
  border: none !important;
}

/* 通用芯片样式 */
.v-chip {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  border: 1px solid rgba(102, 126, 234, 0.2);
  backdrop-filter: blur(5px);
  transition: all 0.3s ease;
  font-weight: 500;
}

.v-chip:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.v-chip.v-chip--size-small {
  height: 28px !important;
  font-size: 12px !important;
  padding: 0 12px !important;
}

/* Vuetify 主题颜色覆盖 */
.v-chip.v-chip--variant-flat.text-success {
  background: linear-gradient(135deg, rgba(76, 175, 80, 0.15) 0%, rgba(76, 175, 80, 0.08) 100%) !important;
  color: #2E7D32 !important;
  border: 1px solid rgba(76, 175, 80, 0.3) !important;
}

.v-chip.v-chip--variant-flat.text-warning {
  background: linear-gradient(135deg, rgba(255, 152, 0, 0.15) 0%, rgba(255, 152, 0, 0.08) 100%) !important;
  color: #E65100 !important;
  border: 1px solid rgba(255, 152, 0, 0.3) !important;
}

.v-chip.v-chip--variant-flat.text-primary {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.15) 100%) !important;
  color: #3F51B5 !important;
  border: 1px solid rgba(102, 126, 234, 0.3) !important;
}

.v-chip.v-chip--variant-flat.text-amber-darken-2 {
  background: linear-gradient(135deg, rgba(255, 193, 7, 0.15) 0%, rgba(255, 193, 7, 0.08) 100%) !important;
  color: #F57C00 !important;
  border: 1px solid rgba(255, 193, 7, 0.3) !important;
}

/* 特权邀请码芯片样式 - 移除蓝色边框 */
.invitation-chip-horizontal.text-amber-darken-2 {
  border: 1px solid rgba(255, 193, 7, 0.3) !important;
  box-shadow: none !important;
}

.invitation-chip-horizontal.text-amber-darken-2:hover {
  border: 1px solid rgba(255, 193, 7, 0.5) !important;
  box-shadow: 0 4px 12px rgba(255, 193, 7, 0.2) !important;
}

/* 可点击的芯片样式 */
.clickable-chip {
  cursor: pointer;
  transition: all 0.3s ease;
}

.clickable-chip:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
}

/* 邀请码芯片样式 */
.invitation-chip {
  cursor: pointer;
  transition: all 0.3s ease;
  font-weight: 500;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.15) 100%) !important;
  border: 1px solid rgba(102, 126, 234, 0.3) !important;
  backdrop-filter: blur(8px);
}

/* 新增：水平布局的邀请码芯片样式 */
.invitation-chip-horizontal {
  cursor: pointer;
  transition: all 0.3s ease;
  font-weight: 500;
  max-width: 100%;
  min-width: 0;
}

/* 普通邀请码的样式 */
.invitation-chip-horizontal:not(.text-amber-darken-2) {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.15) 100%) !important;
  border: 1px solid rgba(102, 126, 234, 0.3) !important;
  backdrop-filter: blur(8px);
}

.invitation-chip:hover,
.invitation-chip-horizontal:not(.text-amber-darken-2):hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
}

/* 邀请码文本样式 */
.code-text {
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 160px;
  letter-spacing: 0.5px;
}

/* 值显示样式 */
.value-display {
  padding: 4px 12px;
  border-radius: 12px;
  font-weight: 600;
  font-size: 14px;
  min-width: 60px;
  text-align: center;
  backdrop-filter: blur(5px);
}

.credits-value {
  background: linear-gradient(135deg, rgba(255, 193, 7, 0.1) 0%, rgba(255, 193, 7, 0.05) 100%);
  color: #F57C00;
  border: 1px solid rgba(255, 193, 7, 0.2);
}

.donation-value {
  background: linear-gradient(135deg, rgba(76, 175, 80, 0.1) 0%, rgba(76, 175, 80, 0.05) 100%);
  color: #388E3C;
  border: 1px solid rgba(76, 175, 80, 0.2);
}

.invited-count-value {
  background: linear-gradient(135deg, rgba(156, 39, 176, 0.1) 0%, rgba(156, 39, 176, 0.05) 100%);
  color: #7B1FA2;
  border: 1px solid rgba(156, 39, 176, 0.2);
}

/* 观看等级图标样式 */
.level-icons-container {
  display: flex;
  align-items: center;
  gap: 2px;
  cursor: pointer;
  transition: all 0.3s ease;
  padding: 2px 6px;
  border-radius: 8px;
}

.level-icons-container:hover {
  background: rgba(102, 126, 234, 0.1);
  transform: scale(1.05);
}

.emoji-icon {
  font-size: 16px;
  transition: transform 0.2s ease;
}

.emoji-icon:hover {
  transform: scale(1.1);
}

/* 入口线路样式 */
.entrance-url-row {
  position: relative;
}

.entrance-url-chip {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  background: linear-gradient(135deg, rgba(255, 87, 34, 0.1) 0%, rgba(255, 87, 34, 0.05) 100%);
  border: 1px solid rgba(255, 87, 34, 0.2);
  border-radius: 20px;
  color: #D84315;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  backdrop-filter: blur(5px);
  font-family: 'Monaco', 'Courier New', monospace;
  letter-spacing: 0.3px;
}

.entrance-url-chip:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(255, 87, 34, 0.2);
  background: linear-gradient(135deg, rgba(255, 87, 34, 0.15) 0%, rgba(255, 87, 34, 0.08) 100%);
  border-color: rgba(255, 87, 34, 0.3);
}

/* 邀请码容器样式 */
.invitation-code-container {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

/* 新增：水平布局的邀请码容器样式 */
.invitation-code-container-horizontal {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  flex: 1;
  min-width: 0; /* 允许收缩 */
}

/* 新增：邀请码和特权标签的水平容器 */
.invitation-code-with-tag {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

/* 特权码标签样式 */
.privilege-tag {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 2px 6px;
  background: linear-gradient(135deg, rgba(255, 193, 7, 0.1) 0%, rgba(255, 193, 7, 0.05) 100%);
  border: 1px solid rgba(255, 193, 7, 0.3);
  border-radius: 8px;
  font-size: 10px;
  color: #FF8F00;
  font-weight: 500;
  box-shadow: none !important;
  filter: none !important;
  backdrop-filter: none !important;
}

/* 新增：水平布局的特权码标签样式 */
.privilege-tag-horizontal {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 2px 6px;
  background: linear-gradient(135deg, rgba(255, 193, 7, 0.15) 0%, rgba(255, 193, 7, 0.08) 100%);
  border: 1px solid rgba(255, 193, 7, 0.4);
  border-radius: 10px;
  font-size: 9px;
  color: #FF8F00;
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
  box-shadow: none !important;
  filter: none !important;
  backdrop-filter: none !important;
}

/* 确保特权标签不继承任何阴影效果 */
.privilege-tag-horizontal *,
.privilege-tag * {
  box-shadow: none !important;
  filter: none !important;
}

/* 特权标签内的图标样式 */
.privilege-tag-horizontal .v-icon,
.privilege-tag .v-icon {
  box-shadow: none !important;
  filter: none !important;
  text-shadow: none !important;
}

.privilege-text {
  font-size: 10px;
  line-height: 1;
  text-shadow: none !important;
}

/* 邀请码行样式 */
.invitation-code-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

/* 新增：水平布局的邀请码行样式 */
.invitation-code-row-horizontal {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.invitation-code-row:last-child {
  border-bottom: none;
}

.invitation-code-row-horizontal:last-child {
  border-bottom: none;
}

/* 兑换按钮样式 */
.redeem-button {
  flex-shrink: 0;
  font-size: 12px;
  height: 28px;
  border-radius: 14px;
  transition: all 0.3s ease;
}

/* 新增：水平布局的兑换按钮样式 */
.redeem-button-horizontal {
  flex-shrink: 0;
  font-size: 11px;
  height: 32px;
  border-radius: 16px;
  transition: all 0.3s ease;
  min-width: 90px;
}

.redeem-button:hover,
.redeem-button-horizontal:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
}

.redeem-button:disabled,
.redeem-button-horizontal:disabled {
  opacity: 0.6;
}

/* 积分转移按钮样式 */
.credits-transfer-btn {
  transition: all 0.3s ease;
  position: relative;
}

.credits-transfer-btn.disabled-style {
  opacity: 0.6;
  cursor: not-allowed;
}

.credits-transfer-btn.disabled-style:hover {
  transform: none !important;
  box-shadow: none !important;
}

.credits-transfer-btn .disable-icon {
  position: absolute;
  top: -2px;
  right: -2px;
  background: white;
  border-radius: 50%;
  font-size: 10px !important;
}

/* 个人活动数据卡片样式 */
.activity-section {
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 2px solid rgba(102, 126, 234, 0.1);
}

.section-title {
  font-weight: 600;
  font-size: 16px;
  color: rgb(var(--v-theme-on-surface));
}

.activity-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 30px;
  font-size: 14px;
  color: rgba(var(--v-theme-on-surface), 0.7);
}

.activity-stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.stats-card {
  background: linear-gradient(135deg, rgba(var(--v-theme-surface), 0.9) 0%, rgba(var(--v-theme-surface), 0.95) 100%);
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 12px;
  padding: 16px;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.stats-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
}

.stats-card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
  font-weight: 600;
  font-size: 14px;
  color: #555;
}

.stats-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
}

.stat-label {
  font-size: 13px;
  color: rgba(var(--v-theme-on-surface), 0.7);
  font-weight: 500;
}

.stat-value {
  font-weight: 700;
  font-size: 15px;
  padding: 2px 8px;
  border-radius: 6px;
  min-width: 50px;
  text-align: center;
}

.today-value {
  background: linear-gradient(135deg, rgba(255, 152, 0, 0.1) 0%, rgba(255, 152, 0, 0.05) 100%);
  color: #F57C00;
  border: 1px solid rgba(255, 152, 0, 0.2);
}

.week-value {
  background: linear-gradient(135deg, rgba(33, 150, 243, 0.1) 0%, rgba(33, 150, 243, 0.05) 100%);
  color: #1976D2;
  border: 1px solid rgba(33, 150, 243, 0.2);
}

.total-value {
  background: linear-gradient(135deg, rgba(76, 175, 80, 0.1) 0%, rgba(76, 175, 80, 0.05) 100%);
  color: #388E3C;
  border: 1px solid rgba(76, 175, 80, 0.2);
}

.stat-value.positive {
  background: linear-gradient(135deg, rgba(76, 175, 80, 0.15) 0%, rgba(76, 175, 80, 0.08) 100%) !important;
  color: #2E7D32 !important;
  border-color: rgba(76, 175, 80, 0.3) !important;
}

.stat-value.negative {
  background: linear-gradient(135deg, rgba(244, 67, 54, 0.15) 0%, rgba(244, 67, 54, 0.08) 100%) !important;
  color: #C62828 !important;
  border-color: rgba(244, 67, 54, 0.3) !important;
}

/* 最近游戏记录样式 */
.recent-games-section {
  margin-top: 16px;
}

.recent-games-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.game-category-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: white;
  margin-bottom: 8px;
  padding-left: 4px;
  border-left: 3px solid rgb(var(--v-theme-primary));
  padding-left: 12px;
}

.recent-game-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: linear-gradient(135deg, rgba(var(--v-theme-surface), 0.6) 0%, rgba(var(--v-theme-surface), 0.8) 100%);
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.04);
  transition: all 0.2s ease;
}

.recent-game-item:hover {
  background: linear-gradient(135deg, rgba(var(--v-theme-surface), 0.8) 0%, rgba(var(--v-theme-surface), 0.9) 100%);
  transform: translateX(2px);
}

.game-result {
  flex: 2;
}

.game-chip {
  font-size: 12px !important;
  height: 24px !important;
  max-width: 200px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.game-change {
  flex: 1;
  text-align: center;
}

.change-value {
  font-weight: 600;
  font-size: 14px;
  padding: 2px 6px;
  border-radius: 4px;
}

.change-value.positive {
  color: #2E7D32;
  background: rgba(76, 175, 80, 0.1);
}

.change-value.negative {
  color: #C62828;
  background: rgba(244, 67, 54, 0.1);
}

.game-date {
  flex: 1;
  text-align: right;
  font-size: 12px;
  color: rgba(var(--v-theme-on-surface), 0.6);
  font-weight: 500;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .activity-stats-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  
  .stats-card {
    padding: 12px;
  }
  
  .stats-card-header {
    font-size: 13px;
  }
  
  .stat-value {
    font-size: 14px;
    min-width: 45px;
  }
  
  .recent-game-item {
    padding: 8px 10px;
  }
  
  .game-chip {
    font-size: 11px !important;
    height: 22px !important;
    max-width: 150px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  
  .change-value {
    font-size: 13px;
  }
  
  .game-date {
    font-size: 11px;
  }
}

@media (max-width: 480px) {
  .activity-stats-grid {
    gap: 10px;
  }
  
  .stats-card {
    padding: 10px;
  }
  
  .stat-item {
    gap: 8px;
  }
  
  .stat-label {
    font-size: 12px;
  }
  
  .stat-value {
    font-size: 13px;
    min-width: 40px;
    padding: 1px 6px;
  }
  
  .recent-game-item {
    padding: 8px 6px;
    gap: 4px;
  }
  
  .game-result {
    flex: 1.5;
    min-width: 0;
  }
  
  .game-chip {
    font-size: 10px !important;
    height: 20px !important;
    max-width: 120px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  .game-change {
    flex: 1;
    text-align: center;
    min-width: 0;
  }
  
  .change-value {
    font-size: 12px;
    padding: 1px 4px;
  }
  
  .game-date {
    flex: 1;
    text-align: right;
    font-size: 10px;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

/* 超小屏幕优化 */
@media (max-width: 360px) {
  .recent-game-item {
    padding: 6px 4px;
    gap: 2px;
  }
  
  .game-result {
    flex: 1.2;
  }
  
  .game-chip {
    font-size: 9px !important;
    height: 18px !important;
    max-width: 100px;
    padding: 0 4px !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  
  .change-value {
    font-size: 11px;
    padding: 1px 3px;
  }
  
  .game-date {
    font-size: 9px;
  }
}

/* 特殊的卡片颜色变化 */
.today-stats {
  border-left: 4px solid #FF9800;
}

.week-stats {
  border-left: 4px solid #2196F3;
}

.total-stats {
  border-left: 4px solid #4CAF50;
}

/* 社区链接部分样式 */
.community-links-section {
  margin-bottom: 20px;
}

.community-links-card {
  background: rgba(var(--v-theme-surface), 0.95);
  border-radius: 16px;
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  border: none;
}

.community-links-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.15);
}

.community-links-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.community-link-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  background: linear-gradient(135deg, rgba(var(--v-theme-surface), 0.8) 0%, rgba(var(--v-theme-surface), 0.9) 100%);
  border: 1px solid rgba(0, 0, 0, 0.05);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.community-link-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.03) 0%, rgba(118, 75, 162, 0.03) 100%);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.community-link-item:hover::before {
  opacity: 1;
}

.community-link-item:hover {
  transform: translateX(4px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
  border-color: rgba(102, 126, 234, 0.2);
}

.link-icon-wrapper {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.group-link {
  background: linear-gradient(135deg, #4CAF50 0%, #66BB6A 100%);
}

.channel-link {
  background: linear-gradient(135deg, #FF9800 0%, #FFB74D 100%);
}

.community-link-item:hover .link-icon-wrapper {
  transform: scale(1.1);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15);
}

.link-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.link-title {
  font-size: 15px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface));
  line-height: 1.3;
}

.link-description {
  font-size: 13px;
  color: rgba(var(--v-theme-on-surface), 0.7);
  line-height: 1.4;
  opacity: 0.9;
}

.community-link-item:hover .link-title {
  color: #667eea;
}

.community-link-item:hover .link-description {
  color: #555;
  opacity: 1;
}

.link-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.copy-link-btn {
  opacity: 0;
  transition: opacity 0.3s ease;
  background: rgba(102, 126, 234, 0.1) !important;
  border-radius: 6px;
}

.community-link-item:hover .copy-link-btn {
  opacity: 1;
}

.copy-link-btn:hover {
  background: rgba(102, 126, 234, 0.2) !important;
  transform: scale(1.1);
}

.no-links-message {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  color: rgba(var(--v-theme-on-surface), 0.5);
  font-size: 14px;
  font-style: italic;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .community-links-grid {
    gap: 10px;
  }
  
  .community-link-item {
    padding: 14px 16px;
    gap: 12px;
  }
  
  .link-icon-wrapper {
    width: 40px;
    height: 40px;
    border-radius: 10px;
  }
  
  .link-title {
    font-size: 14px;
  }
  
  .link-description {
    font-size: 12px;
  }

  .copy-link-btn {
    opacity: 1; /* 在移动设备上始终显示复制按钮 */
  }
}

@media (max-width: 480px) {
  .community-link-item {
    padding: 12px 14px;
    gap: 10px;
  }
  
  .link-icon-wrapper {
    width: 36px;
    height: 36px;
    border-radius: 8px;
  }
  
  .link-icon-wrapper .v-icon {
    font-size: 18px !important;
  }
  
  .link-title {
    font-size: 13px;
  }
  
  .link-description {
    font-size: 11px;
  }

  .link-actions {
    gap: 4px;
  }

  .copy-link-btn {
    opacity: 1; /* 在小屏设备上始终显示 */
  }
}

/* Plex 和 Emby 账户面板专属样式优化 */
/* Plex 面板样式 */
.plex-account-card {
  border-left: 4px solid #E59500 !important;
  position: relative;
}

.plex-account-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, #E59500, transparent);
  opacity: 0.6;
}

.plex-title {
  background: linear-gradient(135deg, rgba(229, 149, 0, 0.08) 0%, rgba(229, 149, 0, 0.03) 100%) !important;
  border-bottom: 1px solid rgba(229, 149, 0, 0.15) !important;
}

.plex-icon {
  font-size: 24px !important;
  filter: drop-shadow(0 2px 4px rgba(229, 149, 0, 0.3));
}

/* Emby 面板样式 */
.emby-account-card {
  border-left: 4px solid #52B54B !important;
  position: relative;
}

.emby-account-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, #52B54B, transparent);
  opacity: 0.6;
}

.emby-title {
  background: linear-gradient(135deg, rgba(82, 181, 75, 0.08) 0%, rgba(82, 181, 75, 0.03) 100%) !important;
  border-bottom: 1px solid rgba(82, 181, 75, 0.15) !important;
}

.emby-icon {
  font-size: 24px !important;
  filter: drop-shadow(0 2px 4px rgba(82, 181, 75, 0.3));
}

/* 服务标题样式 */
.service-title {
  font-size: 19px;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: rgba(255, 255, 255, 0.95);
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

/* 账户信息行样式 */
.account-info-row {
  padding: 10px 8px;
  border-radius: 10px;
  transition: all 0.2s ease;
  position: relative;
}

.account-info-row::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 0;
  background: linear-gradient(180deg, rgba(102, 126, 234, 0.6), rgba(118, 75, 162, 0.6));
  border-radius: 0 2px 2px 0;
  transition: height 0.2s ease;
}

.account-info-row:hover {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.03) 0%, rgba(118, 75, 162, 0.03) 100%);
  transform: translateX(2px);
}

.account-info-row:hover::before {
  height: 70%;
}

/* 标签文本样式 */
.info-label {
  gap: 8px;
}

.label-text {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.85);
  letter-spacing: 0.3px;
  position: relative;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.label-text::after {
  content: ':';
  margin-left: 2px;
  opacity: 0.6;
}

/* 信息值样式 */
.info-value {
  font-size: 14px;
}

.value-text {
  font-weight: 600;
  color: rgba(255, 255, 255, 0.95);
  letter-spacing: 0.2px;
  padding: 4px 12px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.25) 0%, rgba(118, 75, 162, 0.25) 100%);
  border-radius: 8px;
  border: 1px solid rgba(102, 126, 234, 0.35);
  transition: all 0.2s ease;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.account-info-row:hover .value-text {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.35) 0%, rgba(118, 75, 162, 0.35) 100%);
  border-color: rgba(102, 126, 234, 0.5);
  transform: scale(1.02);
  color: rgba(255, 255, 255, 1);
}

/* 优化图标颜色和阴影 */
.account-info-row .v-icon {
  transition: all 0.2s ease;
}

.account-info-row:hover .v-icon {
  transform: scale(1.1);
  filter: brightness(1.1);
}

/* 响应式优化 */
@media (max-width: 768px) {
  .service-title {
    font-size: 17px;
  }

  .label-text {
    font-size: 13px;
  }

  .value-text {
    font-size: 13px;
    padding: 3px 10px;
  }

  .account-info-row {
    padding: 8px 6px;
  }
}

@media (max-width: 480px) {
  .service-title {
    font-size: 16px;
  }

  .label-text {
    font-size: 12px;
  }

  .value-text {
    font-size: 12px;
    padding: 2px 8px;
  }

  .account-info-row {
    padding: 6px 4px;
  }

  .plex-icon, .emby-icon {
    font-size: 20px !important;
  }
}
</style>
