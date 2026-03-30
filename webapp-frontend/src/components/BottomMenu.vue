<template>
  <div class="hbo-bottom-nav">
    <!-- 主页 -->
    <div
      class="hbo-nav-item"
      :class="{ active: activeTab === 'home' }"
      @click="navigateTo('home')"
    >
      <v-icon class="hbo-nav-icon">mdi-home</v-icon>
      <div class="hbo-nav-label">主页</div>
    </div>

    <!-- 我的 -->
    <div
      class="hbo-nav-item"
      :class="{ active: activeTab === 'user-info' }"
      @click="navigateTo('user-info')"
    >
      <v-icon class="hbo-nav-icon">mdi-account</v-icon>
      <div class="hbo-nav-label">我的</div>
    </div>

    <!-- 娱乐 -->
    <div
      class="hbo-nav-item"
      :class="{ active: activeTab === 'activities' }"
      @click="navigateTo('activities')"
    >
      <v-icon class="hbo-nav-icon">mdi-gamepad-variant</v-icon>
      <div class="hbo-nav-label">娱乐</div>
    </div>

    <!-- 排行 -->
    <div
      class="hbo-nav-item"
      :class="{ active: activeTab === 'rankings' }"
      @click="navigateTo('rankings')"
    >
      <v-icon class="hbo-nav-icon">mdi-trophy</v-icon>
      <div class="hbo-nav-label">排行</div>
    </div>

    <!-- 设置 (仅管理员可见) -->
    <div
      class="hbo-nav-item"
      :class="{ active: activeTab === 'management' }"
      @click="navigateTo('management')"
    >
      <v-icon class="hbo-nav-icon">mdi-cog</v-icon>
      <div class="hbo-nav-label">设置</div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'BottomMenu',
  props: {
    // 当前激活的标签，从父组件传入
    currentActiveTab: {
      type: String,
      default: 'home'
    }
  },
  data() {
    return {
      // 内部状态
      activeTab: this.currentActiveTab
    }
  },
  watch: {
    // 监听父组件传入的当前标签更新
    currentActiveTab(newValue) {
      this.activeTab = newValue;
    }
  },
  methods: {
    navigateTo(route) {
      // 通知父组件进行导航
      this.$emit('navigate', route);
      this.activeTab = route;
    }
  }
}
</script>

<style scoped>
/* MisayaMedia 风格底部导航 */
.hbo-bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 70px;
  display: flex;
  justify-content: space-around;
  align-items: center;

  /* MisayaMedia 深色玻璃效果 */
  background: rgba(10, 10, 10, 0.95);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);

  /* 顶部紫色渐变边框 */
  border-top: 1px solid rgba(123, 44, 191, 0.3);

  /* 阴影 */
  box-shadow:
    0 -4px 24px rgba(0, 0, 0, 0.4),
    0 -1px 0 rgba(123, 44, 191, 0.2) inset;

  padding: 0 var(--hbo-spacing-4);
  z-index: var(--hbo-z-fixed);

  /* 平滑过渡 */
  transition: all var(--hbo-transition-base) cubic-bezier(0.4, 0, 0.2, 1);
}

/* 导航项 */
.hbo-nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--hbo-spacing-1);
  padding: var(--hbo-spacing-2);
  cursor: pointer;
  position: relative;
  min-width: 60px;
  border-radius: var(--hbo-radius-md);
  transition: all var(--hbo-transition-base) cubic-bezier(0.4, 0, 0.2, 1);
}

/* 顶部指示条 */
.hbo-nav-item::before {
  content: '';
  position: absolute;
  top: -8px;
  left: 50%;
  transform: translateX(-50%) scaleX(0);
  width: 40px;
  height: 3px;
  background: linear-gradient(135deg, var(--hbo-purple-primary), var(--hbo-gold));
  border-radius: var(--hbo-radius-full);
  transition: transform var(--hbo-transition-base) ease-out;
}

/* Hover 效果 */
.hbo-nav-item:hover {
  background: rgba(123, 44, 191, 0.1);
}

.hbo-nav-item:hover .hbo-nav-icon {
  transform: translateY(-2px);
  color: var(--hbo-purple-light);
}

/* Active 状态 */
.hbo-nav-item.active::before {
  transform: translateX(-50%) scaleX(1);
}

.hbo-nav-item.active {
  background: rgba(123, 44, 191, 0.15);
}

.hbo-nav-item.active .hbo-nav-icon {
  color: var(--hbo-gold);
  transform: scale(1.1) translateY(-1px);
  filter: drop-shadow(0 0 8px rgba(255, 214, 10, 0.6));
  animation: hbo-icon-bounce 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.hbo-nav-item.active .hbo-nav-label {
  color: var(--hbo-gold);
  font-weight: 600;
}

/* 图标 */
.hbo-nav-icon {
  color: var(--hbo-text-secondary);
  font-size: 24px;
  transition: all var(--hbo-transition-base) cubic-bezier(0.34, 1.56, 0.64, 1);
}

/* 标签 */
.hbo-nav-label {
  color: var(--hbo-text-secondary);
  font-size: 10px;
  font-weight: 500;
  transition: all var(--hbo-transition-base) cubic-bezier(0.4, 0, 0.2, 1);
  text-align: center;
  white-space: nowrap;
  letter-spacing: 0.5px;
}

/* 点击反馈动画 */
.hbo-nav-item:active {
  transform: scale(0.95);
  transition: transform 0.1s;
}

/* 图标弹跳动画 */
@keyframes hbo-icon-bounce {
  0% {
    transform: scale(1) translateY(0);
  }
  50% {
    transform: scale(1.2) translateY(-4px);
  }
  100% {
    transform: scale(1.1) translateY(-1px);
  }
}

/* 响应式 - 小屏幕 */
@media (max-width: 360px) {
  .hbo-bottom-nav {
    padding: 0 var(--hbo-spacing-2);
  }

  .hbo-nav-item {
    min-width: 50px;
    padding: var(--hbo-spacing-1);
  }

  .hbo-nav-icon {
    font-size: 22px;
  }

  .hbo-nav-label {
    font-size: 9px;
  }
}

/* 响应式 - 大屏幕 */
@media (min-width: 960px) {
  .hbo-bottom-nav {
    /* 在桌面端可以考虑改为侧边导航 */
    /* 暂时保持底部导航 */
  }
}
</style>
