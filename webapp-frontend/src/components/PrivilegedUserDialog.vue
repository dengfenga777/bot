<template>
  <v-dialog v-model="dialog" max-width="800px" persistent>
    <v-card>
      <v-card-title class="d-flex justify-space-between align-center bg-purple-darken-2 text-white">
        <div class="d-flex align-center">
          <v-icon class="mr-2">mdi-crown</v-icon>
          <span>特权用户管理</span>
        </div>
        <v-btn icon size="small" variant="text" @click="close">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pt-4">
        <!-- 说明文字 -->
        <v-alert type="info" density="compact" class="mb-4">
          <div class="text-caption">
            特权用户离开群组后不会被自动注销账号。管理员也自动享有特权。
          </div>
        </v-alert>

        <!-- 添加特权用户 -->
        <v-card variant="outlined" class="mb-4">
          <v-card-title class="text-subtitle-1">
            <v-icon class="mr-2" size="small">mdi-account-plus</v-icon>
            添加特权用户
          </v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="12" md="8">
                <v-text-field
                  v-model="newUserId"
                  label="Telegram用户ID"
                  type="number"
                  variant="outlined"
                  density="compact"
                  hide-details="auto"
                  :error-messages="addErrorMsg"
                ></v-text-field>
              </v-col>
              <v-col cols="12" md="4">
                <v-btn
                  color="purple-darken-2"
                  block
                  :loading="adding"
                  :disabled="!newUserId"
                  @click="addPrivilegedUser"
                >
                  <v-icon start>mdi-plus</v-icon>
                  添加
                </v-btn>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>

        <!-- 特权用户列表 -->
        <v-card variant="outlined">
          <v-card-title class="text-subtitle-1">
            <v-icon class="mr-2" size="small">mdi-format-list-bulleted</v-icon>
            特权用户列表
          </v-card-title>
          <v-card-text>
            <!-- 加载状态 -->
            <div v-if="loading" class="text-center py-4">
              <v-progress-circular indeterminate color="purple-darken-2"></v-progress-circular>
              <div class="mt-2 text-caption">加载中...</div>
            </div>

            <!-- 错误状态 -->
            <v-alert v-else-if="error" type="error" density="compact">
              {{ error }}
            </v-alert>

            <!-- 空状态 -->
            <div v-else-if="privilegedUsers.length === 0" class="text-center text-grey py-4">
              <v-icon size="48" color="grey-lighten-1">mdi-account-off</v-icon>
              <div class="mt-2">暂无特权用户</div>
            </div>

            <!-- 用户列表 -->
            <v-list v-else density="compact">
              <v-list-item
                v-for="(user, index) in privilegedUsers"
                :key="user.tg_id"
                :class="{ 'border-b': index < privilegedUsers.length - 1 }"
              >
                <template v-slot:prepend>
                  <v-avatar color="purple-lighten-4" size="32">
                    <v-icon size="18" color="purple-darken-2">mdi-account</v-icon>
                  </v-avatar>
                </template>

                <v-list-item-title>
                  {{ user.username }}
                </v-list-item-title>
                <v-list-item-subtitle>
                  ID: {{ user.tg_id }}
                </v-list-item-subtitle>

                <template v-slot:append>
                  <v-btn
                    icon
                    size="small"
                    variant="text"
                    color="red-darken-2"
                    :loading="deletingId === user.tg_id"
                    @click="confirmDelete(user)"
                  >
                    <v-icon size="20">mdi-delete</v-icon>
                  </v-btn>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-card-text>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="text" @click="close">关闭</v-btn>
      </v-card-actions>
    </v-card>

    <!-- 删除确认对话框 -->
    <v-dialog v-model="deleteDialog" max-width="400px">
      <v-card>
        <v-card-title class="text-h6">确认删除</v-card-title>
        <v-card-text>
          确定要将 <strong>{{ deleteUser?.username }}</strong> (ID: {{ deleteUser?.tg_id }}) 从特权用户列表中移除吗？
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="deleteDialog = false">取消</v-btn>
          <v-btn color="red-darken-2" variant="text" :loading="deleting" @click="deletePrivilegedUser">
            确定
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-dialog>
</template>

<script>
import { getPrivilegedUsers, addPrivilegedUser, removePrivilegedUser } from '@/services/systemService';

export default {
  name: 'PrivilegedUserDialog',
  props: {
    modelValue: Boolean
  },
  emits: ['update:modelValue'],
  data() {
    return {
      loading: false,
      error: null,
      privilegedUsers: [],
      newUserId: '',
      adding: false,
      addErrorMsg: '',
      deleteDialog: false,
      deleteUser: null,
      deleting: false,
      deletingId: null
    };
  },
  computed: {
    dialog: {
      get() {
        return this.modelValue;
      },
      set(value) {
        this.$emit('update:modelValue', value);
      }
    }
  },
  watch: {
    dialog(val) {
      if (val) {
        this.loadPrivilegedUsers();
      } else {
        this.reset();
      }
    }
  },
  methods: {
    async loadPrivilegedUsers() {
      this.loading = true;
      this.error = null;
      try {
        const response = await getPrivilegedUsers();
        this.privilegedUsers = response.data || [];
      } catch (error) {
        console.error('加载特权用户列表失败:', error);
        this.error = error.response?.data?.detail || '加载特权用户列表失败';
      } finally {
        this.loading = false;
      }
    },
    async addPrivilegedUser() {
      if (!this.newUserId) {
        this.addErrorMsg = '请输入用户ID';
        return;
      }

      this.adding = true;
      this.addErrorMsg = '';
      try {
        const userId = parseInt(this.newUserId);
        const response = await addPrivilegedUser(userId);

        if (response.success) {
          this.$emit('success', response.message || '添加成功');
          this.newUserId = '';
          await this.loadPrivilegedUsers();
        } else {
          this.addErrorMsg = response.message || '添加失败';
        }
      } catch (error) {
        console.error('添加特权用户失败:', error);
        this.addErrorMsg = error.response?.data?.detail || '添加失败';
      } finally {
        this.adding = false;
      }
    },
    confirmDelete(user) {
      this.deleteUser = user;
      this.deleteDialog = true;
    },
    async deletePrivilegedUser() {
      if (!this.deleteUser) return;

      this.deleting = true;
      this.deletingId = this.deleteUser.tg_id;
      try {
        const response = await removePrivilegedUser(this.deleteUser.tg_id);

        if (response.success) {
          this.$emit('success', response.message || '删除成功');
          this.deleteDialog = false;
          await this.loadPrivilegedUsers();
        } else {
          this.$emit('error', response.message || '删除失败');
        }
      } catch (error) {
        console.error('删除特权用户失败:', error);
        this.$emit('error', error.response?.data?.detail || '删除失败');
      } finally {
        this.deleting = false;
        this.deletingId = null;
      }
    },
    reset() {
      this.newUserId = '';
      this.addErrorMsg = '';
      this.error = null;
      this.deleteUser = null;
      this.deleteDialog = false;
    },
    close() {
      this.dialog = false;
    }
  }
};
</script>

<style scoped>
.border-b {
  border-bottom: 1px solid rgba(0, 0, 0, 0.12);
}
</style>
