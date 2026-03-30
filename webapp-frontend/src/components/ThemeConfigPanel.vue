<template>
  <div class="theme-config-container">
    <!-- 加载状态 -->
    <div v-if="loading" class="text-center my-10">
      <v-progress-circular indeterminate color="primary"></v-progress-circular>
      <div class="mt-3">加载主题配置中...</div>
    </div>

    <!-- 主题配置内容 -->
    <div v-else>
      <!-- 主题模式切换 -->
      <v-card class="config-card mb-4" elevation="3" rounded="xl">
        <v-card-title class="config-card-header">
          <v-icon start color="white">mdi-theme-light-dark</v-icon>
          主题模式
        </v-card-title>
        <v-card-text class="pa-4">
          <v-btn-toggle
            v-model="themeConfig.theme_mode"
            mandatory
            color="primary"
            rounded="lg"
            class="w-100"
          >
            <v-btn value="light" class="flex-grow-1">
              <v-icon start>mdi-white-balance-sunny</v-icon>
              浅色模式
            </v-btn>
            <v-btn value="dark" class="flex-grow-1">
              <v-icon start>mdi-moon-waning-crescent</v-icon>
              深色模式
            </v-btn>
          </v-btn-toggle>
        </v-card-text>
      </v-card>

      <!-- 颜色配置 -->
      <v-card class="config-card mb-4" elevation="3" rounded="xl">
        <v-card-title class="config-card-header">
          <v-icon start color="white">mdi-palette</v-icon>
          主题颜色
        </v-card-title>
        <v-card-text class="pa-4">
          <v-row>
            <v-col cols="6" sm="4" v-for="colorField in colorFields" :key="colorField.key">
              <div class="color-config-item">
                <div class="color-label mb-2">{{ colorField.label }}</div>
                <div class="color-picker-wrapper">
                  <input
                    type="color"
                    v-model="themeConfig[colorField.key]"
                    class="color-picker"
                  />
                  <v-text-field
                    v-model="themeConfig[colorField.key]"
                    density="compact"
                    variant="outlined"
                    hide-details
                    readonly
                    class="color-input"
                  >
                    <template v-slot:prepend-inner>
                      <div
                        class="color-preview"
                        :style="{ backgroundColor: themeConfig[colorField.key] }"
                      ></div>
                    </template>
                  </v-text-field>
                </div>
              </div>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>

      <!-- 字体大小配置 -->
      <v-card class="config-card mb-4" elevation="3" rounded="xl">
        <v-card-title class="config-card-header">
          <v-icon start color="white">mdi-format-size</v-icon>
          字体大小
        </v-card-title>
        <v-card-text class="pa-4">
          <v-row>
            <v-col cols="12" sm="4">
              <div class="font-config-item">
                <div class="font-label mb-2">基础字体大小</div>
                <v-slider
                  v-model="themeConfig.font_size_base"
                  :min="10"
                  :max="20"
                  :step="1"
                  thumb-label
                  color="primary"
                  hide-details
                >
                  <template v-slot:append>
                    <v-chip size="small" color="primary" variant="flat">
                      {{ themeConfig.font_size_base }}px
                    </v-chip>
                  </template>
                </v-slider>
                <div class="font-preview mt-2" :style="{ fontSize: themeConfig.font_size_base + 'px' }">
                  示例文本 Sample Text
                </div>
              </div>
            </v-col>
            <v-col cols="12" sm="4">
              <div class="font-config-item">
                <div class="font-label mb-2">标题字体大小</div>
                <v-slider
                  v-model="themeConfig.font_size_title"
                  :min="16"
                  :max="36"
                  :step="2"
                  thumb-label
                  color="primary"
                  hide-details
                >
                  <template v-slot:append>
                    <v-chip size="small" color="primary" variant="flat">
                      {{ themeConfig.font_size_title }}px
                    </v-chip>
                  </template>
                </v-slider>
                <div class="font-preview mt-2" :style="{ fontSize: themeConfig.font_size_title + 'px', fontWeight: 'bold' }">
                  标题示例
                </div>
              </div>
            </v-col>
            <v-col cols="12" sm="4">
              <div class="font-config-item">
                <div class="font-label mb-2">副标题字体大小</div>
                <v-slider
                  v-model="themeConfig.font_size_subtitle"
                  :min="12"
                  :max="24"
                  :step="1"
                  thumb-label
                  color="primary"
                  hide-details
                >
                  <template v-slot:append>
                    <v-chip size="small" color="primary" variant="flat">
                      {{ themeConfig.font_size_subtitle }}px
                    </v-chip>
                  </template>
                </v-slider>
                <div class="font-preview mt-2" :style="{ fontSize: themeConfig.font_size_subtitle + 'px', fontWeight: '500' }">
                  副标题示例
                </div>
              </div>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>

      <!-- 样式配置 -->
      <v-card class="config-card mb-4" elevation="3" rounded="xl">
        <v-card-title class="config-card-header">
          <v-icon start color="white">mdi-border-radius</v-icon>
          样式配置
        </v-card-title>
        <v-card-text class="pa-4">
          <v-row>
            <v-col cols="12" sm="6">
              <div class="style-config-item">
                <div class="style-label mb-2">圆角大小</div>
                <v-slider
                  v-model="themeConfig.border_radius"
                  :min="0"
                  :max="24"
                  :step="2"
                  thumb-label
                  color="primary"
                  hide-details
                >
                  <template v-slot:append>
                    <v-chip size="small" color="primary" variant="flat">
                      {{ themeConfig.border_radius }}px
                    </v-chip>
                  </template>
                </v-slider>
                <div class="border-preview mt-3">
                  <v-card
                    :style="{ borderRadius: themeConfig.border_radius + 'px' }"
                    class="preview-card"
                    elevation="2"
                  >
                    <v-card-text class="text-center">
                      预览卡片
                    </v-card-text>
                  </v-card>
                </div>
              </div>
            </v-col>
            <v-col cols="12" sm="6">
              <div class="style-config-item">
                <div class="style-label mb-2">背景与表面</div>
                <div class="mb-3">
                  <div class="color-label mb-2">背景颜色</div>
                  <div class="color-picker-wrapper">
                    <input
                      type="color"
                      v-model="themeConfig.background_color"
                      class="color-picker"
                    />
                    <v-text-field
                      v-model="themeConfig.background_color"
                      density="compact"
                      variant="outlined"
                      hide-details
                      readonly
                      class="color-input"
                    >
                      <template v-slot:prepend-inner>
                        <div
                          class="color-preview"
                          :style="{ backgroundColor: themeConfig.background_color }"
                        ></div>
                      </template>
                    </v-text-field>
                  </div>
                </div>
                <div>
                  <div class="color-label mb-2">表面颜色</div>
                  <div class="color-picker-wrapper">
                    <input
                      type="color"
                      v-model="themeConfig.surface_color"
                      class="color-picker"
                    />
                    <v-text-field
                      v-model="themeConfig.surface_color"
                      density="compact"
                      variant="outlined"
                      hide-details
                      readonly
                      class="color-input"
                    >
                      <template v-slot:prepend-inner>
                        <div
                          class="color-preview"
                          :style="{ backgroundColor: themeConfig.surface_color }"
                        ></div>
                      </template>
                    </v-text-field>
                  </div>
                </div>
              </div>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>

      <!-- 操作按钮 -->
      <v-card class="config-card" elevation="3" rounded="xl">
        <v-card-text class="pa-4">
          <v-row>
            <v-col cols="6">
              <v-btn
                block
                color="warning"
                variant="outlined"
                size="large"
                @click="resetConfig"
                :loading="resetting"
              >
                <v-icon start>mdi-refresh</v-icon>
                重置默认
              </v-btn>
            </v-col>
            <v-col cols="6">
              <v-btn
                block
                color="primary"
                variant="elevated"
                size="large"
                @click="saveConfig"
                :loading="saving"
              >
                <v-icon start>mdi-content-save</v-icon>
                保存配置
              </v-btn>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </div>
  </div>
</template>

<script>
import { getThemeConfig, updateThemeConfig, resetThemeConfig } from '@/services/themeService'

export default {
  name: 'ThemeConfigPanel',
  data() {
    return {
      loading: false,
      saving: false,
      resetting: false,
      themeConfig: {
        theme_mode: 'light',
        primary_color: '#9333ea',
        secondary_color: '#3b82f6',
        success_color: '#10b981',
        warning_color: '#f59e0b',
        error_color: '#ef4444',
        info_color: '#3b82f6',
        background_color: '#f9fafb',
        surface_color: '#ffffff',
        font_size_base: 14,
        font_size_title: 24,
        font_size_subtitle: 16,
        border_radius: 8
      },
      colorFields: [
        { key: 'primary_color', label: '主色调' },
        { key: 'secondary_color', label: '次要色' },
        { key: 'success_color', label: '成功色' },
        { key: 'warning_color', label: '警告色' },
        { key: 'error_color', label: '错误色' },
        { key: 'info_color', label: '信息色' }
      ]
    }
  },
  mounted() {
    this.loadConfig()
  },
  methods: {
    async loadConfig() {
      try {
        this.loading = true
        const response = await getThemeConfig()
        this.themeConfig = response.data.config
      } catch (error) {
        console.error('加载主题配置失败:', error)
        this.showMessage('加载主题配置失败', 'error')
      } finally {
        this.loading = false
      }
    },
    async saveConfig() {
      try {
        this.saving = true
        await updateThemeConfig(this.themeConfig)
        this.showMessage('主题配置保存成功，刷新页面后生效')

        // 通知父组件刷新
        this.$emit('config-saved')
      } catch (error) {
        console.error('保存主题配置失败:', error)
        this.showMessage(error.response?.data?.detail || '保存主题配置失败', 'error')
      } finally {
        this.saving = false
      }
    },
    async resetConfig() {
      if (!confirm('确定要重置为默认主题配置吗？')) {
        return
      }

      try {
        this.resetting = true
        const response = await resetThemeConfig()
        this.themeConfig = response.data.config
        this.showMessage('主题配置已重置为默认值')

        // 通知父组件刷新
        this.$emit('config-reset')
      } catch (error) {
        console.error('重置主题配置失败:', error)
        this.showMessage('重置主题配置失败', 'error')
      } finally {
        this.resetting = false
      }
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
.theme-config-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.config-card {
  border: 1px solid rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.config-card-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 16px 20px;
  font-weight: 600;
}

.color-config-item {
  padding: 8px;
}

.color-label, .font-label, .style-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.7);
}

.color-picker-wrapper {
  position: relative;
}

.color-picker {
  position: absolute;
  opacity: 0;
  width: 100%;
  height: 100%;
  cursor: pointer;
  z-index: 2;
}

.color-input {
  cursor: pointer;
}

.color-preview {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  border: 2px solid rgba(0, 0, 0, 0.1);
}

.font-preview {
  padding: 12px;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 8px;
  text-align: center;
  border: 1px solid rgba(0, 0, 0, 0.08);
}

.preview-card {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  border: 2px solid rgba(102, 126, 234, 0.3);
}

@media (max-width: 600px) {
  .theme-config-container {
    padding: 12px;
  }

  .config-card-header {
    padding: 12px 16px;
  }
}
</style>
