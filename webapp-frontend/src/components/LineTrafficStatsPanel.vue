<template>
  <v-dialog v-model="dialog" max-width="1200" scrollable class="line-traffic-stats-dialog">
    <v-card>
      <v-card-title class="text-center">
        <v-icon start color="blue-darken-2">mdi-chart-bar</v-icon>
        线路流量统计
      </v-card-title>

      <v-card-text>
        <div v-if="loading" class="text-center my-4">
          <v-progress-circular indeterminate size="small" color="primary"></v-progress-circular>
          <span class="ml-2">加载流量统计中...</span>
        </div>

        <div v-else-if="error" class="mb-4">
          <v-alert type="error" density="compact">{{ error }}</v-alert>
        </div>

        <div v-else>
          <!-- 线路统计列表 -->
          <v-row>
            <v-col
              v-for="lineStat in stats"
              :key="lineStat.line"
              cols="12"
              md="6"
              lg="4"
            >
              <v-card class="line-stat-card" variant="outlined">
                <v-card-title class="pb-2">
                  <div class="d-flex align-center justify-space-between">
                    <span class="line-name">{{ lineStat.line }}</span>
                    <v-chip
                      :color="lineStat.is_premium ? 'amber' : 'blue'"
                      size="x-small"
                      class="ml-2"
                    >
                      {{ lineStat.is_premium ? '高级' : '普通' }}
                    </v-chip>
                  </div>
                </v-card-title>

                <v-card-text>
                  <!-- 流量统计 -->
                  <div class="traffic-stats">
                    <div class="stat-item">
                      <span class="stat-label">今日流量</span>
                      <span class="stat-value">{{ formatTraffic(lineStat.today_traffic) }}</span>
                    </div>
                    <div class="stat-item">
                      <span class="stat-label">本周流量</span>
                      <span class="stat-value">{{ formatTraffic(lineStat.week_traffic) }}</span>
                    </div>
                    <div class="stat-item">
                      <span class="stat-label">本月流量</span>
                      <span class="stat-value">{{ formatTraffic(lineStat.month_traffic) }}</span>
                    </div>
                    <div class="stat-item">
                      <span class="stat-label">活跃用户</span>
                      <span class="stat-value">{{ lineStat.active_users }} 人</span>
                    </div>
                  </div>

                  <!-- Top用户 -->
                  <v-divider class="my-3"></v-divider>
                  <div class="top-users">
                    <div class="section-title">流量Top 5</div>
                    <div
                      v-for="(user, index) in lineStat.top_users"
                      :key="user.username"
                      class="top-user-item"
                    >
                      <v-chip size="x-small" class="rank-chip">{{ index + 1 }}</v-chip>
                      <span class="username">{{ user.username }}</span>
                      <span class="traffic">{{ formatTraffic(user.traffic) }}</span>
                    </div>
                    <div v-if="lineStat.top_users.length === 0" class="text-grey text-caption text-center py-2">
                      暂无数据
                    </div>
                  </div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </div>
      </v-card-text>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="primary" variant="text" @click="refresh">刷新</v-btn>
        <v-btn color="grey" variant="text" @click="close">关闭</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import {
  getAllLinesTrafficStats,
  formatTrafficSize,
} from '@/services/allLinesTrafficService';

export default {
  name: 'LineTrafficStatsPanel',
  data() {
    return {
      dialog: false,
      loading: false,
      error: null,
      stats: [],
    };
  },
  methods: {
    async open() {
      this.dialog = true;
      await this.fetchStats();
    },

    close() {
      this.dialog = false;
      this.error = null;
    },

    async fetchStats() {
      this.loading = true;
      this.error = null;

      try {
        const response = await getAllLinesTrafficStats();
        if (response.success) {
          this.stats = response.data || [];
          // 按流量排序（今日流量）
          this.stats.sort((a, b) => b.today_traffic - a.today_traffic);
        } else {
          this.error = response.message || '获取流量统计失败';
        }
      } catch (error) {
        this.error = error.response?.data?.detail || '获取流量统计失败，请稍后再试';
        console.error('获取流量统计失败:', error);
      } finally {
        this.loading = false;
      }
    },

    async refresh() {
      await this.fetchStats();
    },

    formatTraffic(bytes) {
      return formatTrafficSize(bytes);
    },
  },
};
</script>

<style scoped>
.line-traffic-stats-dialog {
  width: 100%;
  max-width: 1200px;
}

.line-stat-card {
  height: 100%;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.line-stat-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.line-name {
  font-weight: 600;
  font-size: 1.1rem;
}

.traffic-stats {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
}

.stat-label {
  font-size: 0.9rem;
  color: #666;
}

.stat-value {
  font-weight: 600;
  font-size: 1rem;
  color: #1976d2;
}

.section-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: #555;
  margin-bottom: 8px;
}

.top-users {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.top-user-item {
  display: flex;
  align-items: center;
  padding: 4px 0;
  gap: 8px;
}

.rank-chip {
  min-width: 24px;
  text-align: center;
  font-weight: bold;
}

.username {
  flex: 1;
  font-size: 0.875rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.traffic {
  font-size: 0.875rem;
  font-weight: 500;
  color: #1976d2;
}

@media (max-width: 960px) {
  .line-stat-card {
    margin-bottom: 12px;
  }
}

@media (max-width: 600px) {
  .line-name {
    font-size: 1rem;
  }

  .stat-value {
    font-size: 0.9rem;
  }

  .username {
    font-size: 0.8rem;
  }

  .traffic {
    font-size: 0.8rem;
  }
}
</style>
