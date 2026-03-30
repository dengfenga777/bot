import { createApp } from "vue"
import App from "./App.vue"
import router from "./router"
import axios from "axios"
// 引入 Vuetify (HBO 主题配置)
import vuetify from "./plugins/vuetify"
import "vuetify/styles"
import "@mdi/font/css/materialdesignicons.css"
// 引入 HBO 全局样式
import "./styles/hbo-global.scss"
// 引入 Service Worker 注册
import registerServiceWorker from "./registerServiceWorker"

// 获取正确的环境变量
const apiBaseUrl = ""  // use same origin (tgbot.misaya.org)

// API 配置
const apiConfig = {
  baseURL: apiBaseUrl,
  timeout: 120000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json"
  }
}

// 创建 axios 实例
const apiClient = axios.create(apiConfig)

// Telegram SDK 初始化状态
let telegramInitialized = false
let initDataCache = null

// 等待 Telegram SDK 初始化的 Promise
function waitForTelegram(maxWait = 8000) {
  return new Promise((resolve) => {
    // 如果已经初始化，直接返回
    if (window.Telegram?.WebApp?.initData) {
      telegramInitialized = true
      initDataCache = window.Telegram.WebApp.initData
      resolve(initDataCache)
      return
    }

    const startTime = Date.now()
    const checkInterval = setInterval(() => {
      if (window.Telegram?.WebApp?.initData) {
        clearInterval(checkInterval)
        telegramInitialized = true
        initDataCache = window.Telegram.WebApp.initData
        console.log("Telegram SDK 初始化完成，initData 长度:", initDataCache?.length)
        resolve(initDataCache)
      } else if (Date.now() - startTime > maxWait) {
        clearInterval(checkInterval)
        // 超时后也标记为已初始化，防止每次请求都重复等待 8 秒
        telegramInitialized = true
        console.warn("Telegram SDK 初始化超时，可能不在 Telegram 环境中")
        resolve(null)
      }
    }, 50)
  })
}

// 添加请求拦截器
apiClient.interceptors.request.use(
  async (config) => {
    // 如果还没有初始化，等待一下
    if (!telegramInitialized) {
      await waitForTelegram()
    }

    // 获取最新的 initData（每次都从 window 读取最新值，initDataCache 作为降级）
    let initData = window.Telegram?.WebApp?.initData || initDataCache
    let userId = window.Telegram?.WebApp?.initDataUnsafe?.user?.id

    // 开发环境模拟数据
    if (process.env.NODE_ENV === "development" && !initData) {
      // 创建模拟的 Telegram 认证数据
      const mockUser = {
        id: 123456789,
        first_name: "Test",
        last_name: "User",
        username: "testuser",
        language_code: "zh"
      }

      // 创建模拟的 initData
      const mockInitData = new URLSearchParams({
        user: JSON.stringify(mockUser),
        auth_date: Math.floor(Date.now() / 1000).toString(),
        hash: "mock_hash_for_development"
      }).toString()

      initData = mockInitData
      userId = mockUser.id

      console.log("使用开发环境模拟认证数据")
    }

    // 只有当 initData 有值时才设置 header
    if (initData && initData !== "undefined") {
      config.headers["X-Telegram-Init-Data"] = initData
    }
    if (userId) {
      config.headers["X-Telegram-User-ID"] = userId
    }
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 添加响应拦截器
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("API请求错误:", error)
    return Promise.reject(error)
  }
)

// 导出 API 客户端以便在其他文件中使用
export { apiClient }

// 初始化应用
async function initApp() {
  // 先等待 Telegram SDK
  await waitForTelegram()

  // 确保 Telegram WebApp 已准备就绪
  if (window.Telegram && window.Telegram.WebApp) {
    const tgApp = window.Telegram.WebApp
    tgApp.ready()
    tgApp.expand()

    // 设置后退按钮事件处理
    tgApp.BackButton.onClick(() => {
      if (router.currentRoute.value.path !== "/") {
        router.back()
      }
    })
  }

  // 注册 Service Worker
  registerServiceWorker()

  // 创建并挂载应用
  const app = createApp(App)
  app.use(router)
  app.use(vuetify)

  // 将 API 客户端注册为全局属性
  app.config.globalProperties.$apiClient = apiClient

  app.mount("#app")

  // 设置初始路由
  if (window.location.hash === "" || window.location.hash === "#/") {
    router.replace({ name: "home" })
  }
}

// 等待 DOM 加载完成后初始化
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initApp)
} else {
  initApp()
}
