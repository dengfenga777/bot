import { createRouter, createWebHashHistory } from 'vue-router'
import Home from '../views/Home.vue'
import UserInfo from '../views/UserInfo.vue'
import Activities from '../views/Activities.vue'
import Rankings from '../views/Rankings.vue'
import Management from '../views/Management.vue'

const routes = [
  {
    path: '/',
    redirect: '/home'
  },
  {
    path: '/home',
    name: 'home',
    component: Home
  },
  {
    path: '/user-info',
    name: 'user-info',
    component: UserInfo
  },
  {
    path: '/activities',
    name: 'activities',
    component: Activities
  },
  {
    path: '/rankings',
    name: 'rankings',
    component: Rankings
  },
  {
    path: '/management',
    name: 'management',
    component: Management
  }
]

const router = createRouter({
  history: createWebHashHistory(process.env.BASE_URL),
  routes
})

// 确保初始化时路由正确
router.beforeEach((to, from, next) => {
  if (to.path === '/' && to.hash === '') {
    next({ path: '/home' });
  } else {
    next();
  }
});

export default router
