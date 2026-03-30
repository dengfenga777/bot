<template>
  <v-dialog v-model="dialog" max-width="800" scrollable class="line-switch-history-dialog">
    <v-card>
      <v-card-title class="text-center">
        <v-icon start color="blue-darken-2">mdi-history</v-icon>
        线路切换历史
      </v-card-title>

      <v-card-text>
        <div v-if="loading" class="text-center my-4">
          <v-progress-circular indeterminate size="small" color="primary"></v-progress-circular>
          <span class="ml-2">加载历史记录中...</span>
        </div>

        <div v-else-if="error" class="mb-4">
          <v-alert type="error" density="compact">{{ error }}</v-alert>
        </div>

        <div v-else>
          <v-table density="comfortable">
            <thead>
              <tr>
                <th class="text-left">用户</th>
                <th class="text-left">服务</th>
                <th class="text-left">原线路</th>
                <th class="text-center">→</th>
                <th class="text-left">新线路</th>
                <th class="text-right">切换时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in history" :key="index">
                <td class="username-cell">{{ item.username }}</td>
                <td>
                  <v-chip size="x-small" :color="item.service === 'emby' ? 'green' : 'purple'">
                    {{ item.service.toUpperCase() }}
                  </v-chip>
                </td>
                <td>
                  <v-chip size="small" variant="outlined">
                    {{ item.old_line || '无' }}
                  </v-chip>
                </td>
                <td class="text-center">
                  <v-icon size="small" color="grey">mdi-arrow-right</v-icon>
                </td>
                <td>
                  <v-chip size="small" color="primary" variant="flat">
                    {{ item.new_line || '无' }}
                  </v-chip>
                </td>
                <td class="text-right time-cell">{{ formatTime(item.switch_date) }}</td>
              </tr>
              <tr v-if="history.length === 0">
                <td colspan="6" class="text-center text-grey py-4">暂无历史记录</td>
              </tr>
            </tbody>
          </v-table>
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
import { getLineSwitchHistory } from '@/services/allLinesTrafficService';

export default {
  name: 'LineSwitchHistoryDialog',
  data() {
    return {
      dialog: false,
      loading: false,
      error: null,
      history: [],
      limit: 20,
    };
  },
  methods: {
    async open() {
      this.dialog = true;
      await this.fetchHistory();
    },

    close() {
      this.dialog = false;
      this.error = null;
    },

    async fetchHistory() {
      this.loading = true;
      this.error = null;

      try {
        const response = await getLineSwitchHistory(this.limit);
        if (response.success) {
          this.history = response.data || [];
        } else {
          this.error = response.message || '获取历史记录失败';
        }
      } catch (error) {
        this.error = error.response?.data?.detail || '获取历史记录失败，请稍后再试';
        console.error('获取历史记录失败:', error);
      } finally {
        this.loading = false;
      }
    },

    async refresh() {
      await this.fetchHistory();
    },

    formatTime(timeStr) {
      if (!timeStr) return '';
      // 假设格式为 "YYYY-MM-DD HH:MM:SS"
      return timeStr.substring(0, 16); // 去掉秒数
    },
  },
};
</script>

<style scoped>
.line-switch-history-dialog {
  width: 100%;
  max-width: 800px;
}

.username-cell {
  font-weight: 500;
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.time-cell {
  font-size: 0.875rem;
  color: #666;
}

@media (max-width: 600px) {
  .username-cell {
    max-width: 100px;
  }

  .time-cell {
    font-size: 0.8rem;
  }
}
</style>
