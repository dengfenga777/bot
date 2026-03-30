<template>
  <v-dialog
    v-model="dialog"
    :max-width="$vuetify.display.xs ? '100vw' : '600px'"
    :fullscreen="$vuetify.display.xs"
    persistent
    scrollable
  >
    <v-card class="tg-binding-card">
      <v-toolbar color="blue-darken-2" dark flat>
        <v-btn icon dark @click="close">
          <v-icon>mdi-close</v-icon>
        </v-btn>
        <v-toolbar-title>
          <v-icon class="mr-2">mdi-account-switch</v-icon>
          更换 TG 绑定
        </v-toolbar-title>
      </v-toolbar>

      <v-card-text class="pa-6 tg-binding-card__content">
        <v-form ref="form" v-model="valid">
          <v-row>
            <!-- 旧的TG ID -->
            <v-col cols="12">
              <v-text-field
                v-model.number="formData.old_tg_id"
                label="原 TG ID（可选）"
                type="number"
                outlined
                dense
                :rules="[
                  v => !v || v > 0 || 'TG ID必须是正整数'
                ]"
                placeholder="知道旧 TG ID 时可直接填写"
              >
                <template v-slot:prepend-inner>
                  <v-icon size="small" color="orange">mdi-telegram</v-icon>
                </template>
              </v-text-field>
            </v-col>

            <v-col cols="12">
              <v-alert
                type="info"
                density="compact"
                variant="tonal"
                class="mb-0"
              >
                如果旧 TG 账号已经异常、被封或者不方便查 TG ID，可以改填下面任意一个媒体账号信息来定位旧绑定。
              </v-alert>
            </v-col>

            <v-col cols="12" md="6">
              <v-text-field
                v-model.trim="formData.plex_email"
                label="Plex 邮箱（可选）"
                outlined
                dense
                placeholder="例如 user@example.com"
              >
                <template v-slot:prepend-inner>
                  <v-icon size="small" color="indigo">mdi-email-outline</v-icon>
                </template>
              </v-text-field>
            </v-col>

            <v-col cols="12" md="6">
              <v-text-field
                v-model.trim="formData.plex_username"
                label="Plex 用户名（可选）"
                outlined
                dense
                placeholder="不知道邮箱时可填用户名"
              >
                <template v-slot:prepend-inner>
                  <v-icon size="small" color="indigo">mdi-account-outline</v-icon>
                </template>
              </v-text-field>
            </v-col>

            <v-col cols="12">
              <v-text-field
                v-model.trim="formData.emby_username"
                label="Emby 用户名（可选）"
                outlined
                dense
                placeholder="例如 emby_user"
              >
                <template v-slot:prepend-inner>
                  <v-icon size="small" color="teal">mdi-account-circle-outline</v-icon>
                </template>
              </v-text-field>
            </v-col>

            <!-- 新的TG ID -->
            <v-col cols="12">
              <v-text-field
                v-model.number="formData.new_tg_id"
                label="新的 TG ID"
                type="number"
                outlined
                dense
                required
                :rules="[
                  v => !!v || '请输入新的TG ID',
                  v => (v && v > 0) || 'TG ID必须是正整数'
                ]"
                placeholder="请输入新的Telegram用户ID"
              >
                <template v-slot:prepend-inner>
                  <v-icon size="small" color="blue">mdi-telegram</v-icon>
                </template>
              </v-text-field>
            </v-col>

            <!-- 备注信息 -->
            <v-col cols="12">
              <v-textarea
                v-model="formData.note"
                label="备注信息（可选）"
                outlined
                dense
                rows="2"
                placeholder="请输入换绑备注信息..."
                hint="备注信息将随通知发送给用户"
                persistent-hint
              >
                <template v-slot:prepend-inner>
                  <v-icon size="small">mdi-note-text</v-icon>
                </template>
              </v-textarea>
            </v-col>

            <!-- 积分说明 -->
            <v-col cols="12">
              <v-alert
                type="warning"
                density="compact"
                variant="tonal"
                class="mb-0"
              >
                <div class="d-flex align-center">
                  <v-icon start>mdi-alert-circle</v-icon>
                  <div>
                    <strong>换绑说明：</strong>
                    <ul class="mt-1 mb-0 pl-4">
                      <li>换绑操作将从<strong>原用户</strong>扣除 <strong>100 积分</strong></li>
                      <li>积分不足时允许换绑，差额记为<strong>欠积分</strong></li>
                      <li>欠积分在每日观看收益中<strong>自动扣还</strong>，超 <strong>3 个月</strong>未还清封禁账号</li>
                      <li>将更新该 TG 用户的所有服务绑定（Plex、Emby、Overseerr）</li>
                      <li>会一并迁移签到、勋章、邀请码和活动历史数据</li>
                      <li>原用户和新用户都会收到通知消息</li>
                    </ul>
                  </div>
                </div>
              </v-alert>
            </v-col>
          </v-row>
        </v-form>
      </v-card-text>

      <v-card-actions class="pa-6 pt-0 tg-binding-card__actions">
        <v-spacer></v-spacer>
        <v-btn @click="close" variant="text" :disabled="loading">
          取消
        </v-btn>
        <v-btn
          @click="submit"
          color="blue-darken-2"
          variant="flat"
          :loading="loading"
          :disabled="!valid"
        >
          <v-icon start>mdi-check</v-icon>
          确认换绑
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { changeTgBinding } from '@/services/adminService'

export default {
  name: 'TgBindingDialog',
  data() {
    return {
      dialog: false,
      valid: false,
      loading: false,
      formData: {
        old_tg_id: null,
        plex_email: '',
        plex_username: '',
        emby_username: '',
        new_tg_id: null,
        note: ''
      }
    }
  },
  methods: {
    open() {
      this.dialog = true
      this.resetForm()
    },

    close() {
      this.dialog = false
      this.resetForm()
    },

    resetForm() {
      this.formData = {
        old_tg_id: null,
        plex_email: '',
        plex_username: '',
        emby_username: '',
        new_tg_id: null,
        note: ''
      }
      this.valid = false
      if (this.$refs.form) {
        this.$refs.form.resetValidation()
      }
    },

    async submit() {
      // 验证表单
      const { valid } = await this.$refs.form.validate()
      if (!valid) {
        this.showMessage('表单验证失败，请检查输入', 'error')
        return
      }

      const hasSource = !!(
        this.formData.old_tg_id ||
        this.formData.plex_email ||
        this.formData.plex_username ||
        this.formData.emby_username
      )
      if (!hasSource) {
        this.showMessage('请至少填写原 TG ID、Plex 邮箱、Plex 用户名或 Emby 用户名中的一个', 'error')
        return
      }

      try {
        this.loading = true

        // 构建请求数据
        const requestData = {
          old_tg_id: this.formData.old_tg_id,
          plex_email: this.formData.plex_email || null,
          plex_username: this.formData.plex_username || null,
          emby_username: this.formData.emby_username || null,
          new_tg_id: this.formData.new_tg_id,
          note: this.formData.note || ''
        }

        // 调用API
        const response = await changeTgBinding(requestData)

        // 显示成功消息
        this.showMessage(response.message || '换绑成功', 'success')

        // 关闭对话框
        this.close()

        // 触发换绑完成事件
        this.$emit('binding-changed', response)

      } catch (error) {
        console.error('换绑失败:', error)
        console.error('错误详情:', error.response)

        let errorMessage = '换绑操作失败'

        if (error.response) {
          // 服务器返回了错误响应
          if (error.response.data) {
            if (error.response.data.detail) {
              errorMessage = error.response.data.detail
            } else if (error.response.data.message) {
              errorMessage = error.response.data.message
            }
          }
          errorMessage += `\n状态码: ${error.response.status}`
        } else if (error.request) {
          // 请求已发出但没有收到响应
          errorMessage = '网络错误：无法连接到服务器'
        } else {
          // 其他错误
          errorMessage = error.message || errorMessage
        }

        this.showMessage(errorMessage, 'error')
      } finally {
        this.loading = false
      }
    },

    showMessage(message, type = 'success') {
      if (window.Telegram?.WebApp) {
        window.Telegram.WebApp.showPopup({
          title: type === 'error' ? '错误' : type === 'info' ? '提示' : '成功',
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
.tg-binding-card {
  max-height: min(calc(100vh - 32px), calc(100dvh - 32px));
  display: flex;
  flex-direction: column;
}

.tg-binding-card > .v-toolbar {
  flex-shrink: 0;
}

.tg-binding-card__content {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
}

.tg-binding-card__actions {
  flex-shrink: 0;
  background: inherit;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}

.tg-binding-card__content ul {
  font-size: 14px;
  line-height: 1.6;
}

.tg-binding-card__content ul li {
  margin-bottom: 4px;
}

@media (max-width: 600px) {
  .tg-binding-card {
    height: 100dvh;
    max-height: 100dvh;
    border-radius: 0 !important;
  }

  .tg-binding-card__content {
    padding: 16px !important;
  }

  .tg-binding-card__actions {
    padding: 16px !important;
    padding-top: 0 !important;
  }
}
</style>
