async function unregisterServiceWorkers() {
  if (!('serviceWorker' in navigator)) {
    return
  }

  try {
    const registrations = await navigator.serviceWorker.getRegistrations()
    if (!registrations.length) {
      return
    }

    await Promise.all(registrations.map((registration) => registration.unregister()))

    if ('caches' in window) {
      const cacheNames = await caches.keys()
      await Promise.all(cacheNames.map((cacheName) => caches.delete(cacheName)))
    }

    // 清理一次后刷新，让用户尽快拿到最新前端资源，避免继续看到旧版换绑页面。
    if (!window.sessionStorage.getItem('pmsmanagebot_sw_cleared')) {
      window.sessionStorage.setItem('pmsmanagebot_sw_cleared', '1')
      window.location.reload()
    }
  } catch (error) {
    console.error('清理 Service Worker 失败：', error)
  }
}

function registerServiceWorker() {
  window.addEventListener('load', () => {
    unregisterServiceWorkers()
  })
}

export default registerServiceWorker
