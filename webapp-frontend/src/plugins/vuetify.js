/**
 * Vuetify Plugin Configuration
 * HBO Max Design System Theme
 */

import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { aliases, mdi } from 'vuetify/iconsets/mdi'

// HBO Max 颜色系统
const hboColors = {
  // 主色调 - 紫色系
  purpleLight: '#9D4EDD',
  purplePrimary: '#7B2CBF',
  purpleDeep: '#5A189A',
  purpleDarkest: '#10002B',

  // 强调色
  gold: '#FFD60A',
  goldDark: '#FFC300',
  cyan: '#06FFA5',
  cyanDark: '#00E68A',
  pink: '#FF006E',
  pinkDark: '#D90050',

  // 服务品牌色
  orange: '#FF9800',
  orangeDark: '#F57C00',
  blue: '#2196F3',
  blueDark: '#1976D2',
  green: '#4CAF50',
  greenDark: '#388E3C',

  // 背景色
  bgBlack: '#000000',
  bgDark: '#0A0A0A',
  bgPurpleDark: '#1A0033',
  bgCard: '#1E1E1E',
  bgElevated: '#2A2A2A',

  // 文字色
  textPrimary: '#FFFFFF',
  textSecondary: 'rgba(255, 255, 255, 0.7)',
  textDisabled: 'rgba(255, 255, 255, 0.4)',

  // 边框色
  borderSubtle: 'rgba(255, 255, 255, 0.1)',
  borderMedium: 'rgba(255, 255, 255, 0.2)',

  // 语义色
  success: '#06FFA5',
  successBg: 'rgba(6, 255, 165, 0.1)',
  warning: '#FFD60A',
  warningBg: 'rgba(255, 214, 10, 0.1)',
  error: '#FF006E',
  errorBg: 'rgba(255, 0, 110, 0.1)',
  info: '#2196F3',
  infoBg: 'rgba(33, 150, 243, 0.1)',
}

export default createVuetify({
  components,
  directives,
  icons: {
    defaultSet: 'mdi',
    aliases,
    sets: {
      mdi,
    },
  },

  theme: {
    defaultTheme: 'hboDark',
    themes: {
      // HBO 深色主题
      hboDark: {
        dark: true,
        colors: {
          // Vuetify 标准颜色
          primary: hboColors.purplePrimary,
          secondary: hboColors.purpleDeep,
          accent: hboColors.gold,
          success: hboColors.success,
          warning: hboColors.warning,
          error: hboColors.error,
          info: hboColors.info,

          // 背景色
          background: hboColors.bgBlack,
          surface: hboColors.bgCard,
          'surface-variant': hboColors.bgElevated,

          // 文字色
          'on-background': hboColors.textPrimary,
          'on-surface': hboColors.textPrimary,
          'on-primary': hboColors.gold,
          'on-secondary': hboColors.textPrimary,
          'on-success': hboColors.bgBlack,
          'on-warning': hboColors.bgBlack,
          'on-error': hboColors.textPrimary,
          'on-info': hboColors.textPrimary,

          // HBO 自定义颜色
          'purple-light': hboColors.purpleLight,
          'purple-primary': hboColors.purplePrimary,
          'purple-deep': hboColors.purpleDeep,
          'purple-darkest': hboColors.purpleDarkest,
          'gold': hboColors.gold,
          'gold-dark': hboColors.goldDark,
          'cyan': hboColors.cyan,
          'cyan-dark': hboColors.cyanDark,
          'pink': hboColors.pink,
          'pink-dark': hboColors.pinkDark,
          'orange': hboColors.orange,
          'orange-dark': hboColors.orangeDark,
          'blue': hboColors.blue,
          'blue-dark': hboColors.blueDark,
          'green': hboColors.green,
          'green-dark': hboColors.greenDark,
        },
      },

      // HBO 浅色主题 (备用)
      hboLight: {
        dark: false,
        colors: {
          primary: hboColors.purplePrimary,
          secondary: hboColors.purpleDeep,
          accent: hboColors.gold,
          success: hboColors.green,
          warning: hboColors.warning,
          error: hboColors.error,
          info: hboColors.info,

          background: '#FFFFFF',
          surface: '#F5F5F5',
          'surface-variant': '#EEEEEE',

          'on-background': '#000000',
          'on-surface': '#000000',
          'on-primary': '#FFFFFF',
          'on-secondary': '#FFFFFF',
        },
      },
    },
  },

  // 默认配置
  defaults: {
    // 全局默认属性
    global: {
      ripple: true,
    },

    // 按钮默认属性
    VBtn: {
      variant: 'elevated',
      rounded: 'lg',
      style: {
        textTransform: 'none',
        fontWeight: 600,
      },
    },

    // 卡片默认属性
    VCard: {
      rounded: 'xl',
      elevation: 8,
      style: {
        backdropFilter: 'blur(10px)',
      },
    },

    // Tab默认属性
    VTabs: {
      color: 'primary',
      bgColor: 'transparent',
      grow: false,
    },

    VTab: {
      rounded: 'lg',
    },

    // Dialog默认属性
    VDialog: {
      rounded: 'xl',
    },

    // Chip默认属性
    VChip: {
      rounded: 'pill',
    },

    // TextField默认属性
    VTextField: {
      variant: 'outlined',
      rounded: 'lg',
      color: 'primary',
    },

    // Select默认属性
    VSelect: {
      variant: 'outlined',
      rounded: 'lg',
      color: 'primary',
    },

    // List默认属性
    VList: {
      rounded: 'lg',
    },

    VListItem: {
      rounded: 'lg',
    },

    // Progress默认属性
    VProgressCircular: {
      color: 'primary',
      width: 4,
    },

    VProgressLinear: {
      color: 'primary',
      height: 8,
      rounded: true,
    },

    // Alert默认属性
    VAlert: {
      rounded: 'lg',
      variant: 'tonal',
    },

    // Snackbar默认属性
    VSnackbar: {
      location: 'top',
      rounded: 'lg',
    },
  },
})
