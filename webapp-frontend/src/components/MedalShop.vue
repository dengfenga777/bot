<template>
  <div class="medal-shop">
    <div v-if="loading" class="medal-shop-loading">
      <v-progress-circular indeterminate color="warning" size="46" />
      <div class="mt-3">正在加载勋章商店...</div>
    </div>

    <div v-else-if="error" class="medal-shop-error">
      <v-alert type="error" variant="tonal">{{ error }}</v-alert>
      <v-btn class="mt-3" color="warning" variant="flat" @click="fetchShop">重试</v-btn>
    </div>

    <div v-else>
      <div class="shop-summary-card">
        <div>
          <div class="summary-label">当前勋章加成</div>
          <div class="summary-value">x{{ currentMultiplier.toFixed(2) }}</div>
          <div class="summary-subtitle">已拥有 {{ ownedMedals.length }} 枚勋章</div>
        </div>
        <div class="summary-credits">
          <div class="summary-label">当前积分</div>
          <div class="summary-value credits">{{ currentCredits.toFixed(2) }}</div>
        </div>
      </div>

      <div v-if="ownedMedals.length" class="owned-medals-section">
        <div class="section-title">
          <v-icon size="18" color="warning" class="mr-2">mdi-medal-outline</v-icon>
          已拥有勋章
        </div>
        <UserMedals :medals="ownedMedals" show-names />
      </div>

      <div class="section-title mt-6">
        <v-icon size="18" color="warning" class="mr-2">mdi-storefront-outline</v-icon>
        勋章商店
      </div>

      <v-row>
        <v-col
          v-for="item in shopItems"
          :key="item.code"
          cols="12"
          md="6"
        >
          <v-card class="shop-item-card" rounded="xl">
            <div class="shop-item-hero">
              <img
                v-if="item.icon_url"
                :src="item.icon_url"
                :alt="item.name"
                class="shop-item-image"
              >
              <div class="shop-item-copy">
                <div class="shop-item-title">{{ item.name }}</div>
                <div class="shop-item-desc">{{ item.description }}</div>
              </div>
            </div>

            <div class="shop-item-meta">
              <v-chip color="warning" variant="flat" size="small">
                积分加成 x{{ Number(item.multiplier || 1).toFixed(2) }}
              </v-chip>
              <v-chip color="deep-orange" variant="tonal" size="small">
                售价 {{ Number(item.price || 0).toFixed(0) }} 积分
              </v-chip>
            </div>

            <v-card-actions class="pt-0">
              <v-btn
                color="warning"
                variant="flat"
                block
                :disabled="Boolean(item.owned) || purchasingCode === item.code || currentCredits < Number(item.price || 0)"
                :loading="purchasingCode === item.code"
                @click="handlePurchase(item)"
              >
                <v-icon start>{{ item.owned ? 'mdi-check-decagram' : 'mdi-cart-outline' }}</v-icon>
                <span v-if="item.owned">已拥有</span>
                <span v-else-if="currentCredits < Number(item.price || 0)">积分不足</span>
                <span v-else>立即购入</span>
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-col>
      </v-row>
    </div>
  </div>
</template>

<script>
import UserMedals from '@/components/UserMedals.vue'
import { getMedalShop, purchaseMedal } from '@/services/medalService'

export default {
  name: 'MedalShop',
  components: {
    UserMedals
  },
  data() {
    return {
      loading: true,
      error: null,
      purchasingCode: '',
      currentCredits: 0,
      currentMultiplier: 1,
      ownedMedals: [],
      shopItems: []
    }
  },
  mounted() {
    this.fetchShop()
  },
  methods: {
    async fetchShop() {
      try {
        this.loading = true
        this.error = null
        const response = await getMedalShop()
        this.applyPayload(response.data?.data || {})
      } catch (error) {
        this.error = error.response?.data?.detail || '获取勋章商店失败'
      } finally {
        this.loading = false
      }
    },

    applyPayload(payload) {
      this.currentCredits = Number(payload.current_credits || 0)
      this.currentMultiplier = Number(payload.current_multiplier || 1)
      this.ownedMedals = payload.owned_medals || []
      this.shopItems = payload.shop_items || []
      this.$emit('credits-updated', this.currentCredits)
    },

    async handlePurchase(item) {
      try {
        this.purchasingCode = item.code
        const response = await purchaseMedal(item.code)
        this.applyPayload(response.data?.data || {})
        this.$emit('message', {
          text: response.data?.message || `已购入 ${item.name}`,
          color: 'success'
        })
      } catch (error) {
        this.$emit('message', {
          text: error.response?.data?.detail || '购买勋章失败',
          color: 'error'
        })
      } finally {
        this.purchasingCode = ''
      }
    }
  }
}
</script>

<style scoped>
.medal-shop {
  width: 100%;
}

.medal-shop-loading,
.medal-shop-error {
  min-height: 280px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.shop-summary-card {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 20px;
  border-radius: 24px;
  background:
    radial-gradient(circle at top left, rgba(255, 201, 71, 0.18), transparent 40%),
    linear-gradient(135deg, rgba(18, 18, 28, 0.92), rgba(42, 26, 10, 0.92));
  border: 1px solid rgba(255, 201, 71, 0.18);
  box-shadow: 0 22px 60px rgba(0, 0, 0, 0.28);
}

.summary-label {
  font-size: 12px;
  color: rgba(255, 244, 214, 0.72);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.summary-value {
  margin-top: 6px;
  font-size: 32px;
  font-weight: 700;
  color: #ffd166;
}

.summary-value.credits {
  color: #7ae582;
}

.summary-subtitle {
  margin-top: 4px;
  color: rgba(255, 255, 255, 0.72);
}

.owned-medals-section,
.section-title {
  margin-top: 20px;
}

.section-title {
  display: flex;
  align-items: center;
  font-size: 15px;
  font-weight: 700;
  color: #fff3d4;
}

.shop-item-card {
  height: 100%;
  padding: 18px;
  background:
    linear-gradient(180deg, rgba(33, 33, 48, 0.92), rgba(18, 18, 28, 0.96));
  border: 1px solid rgba(255, 201, 71, 0.14);
}

.shop-item-hero {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.shop-item-image {
  width: 76px;
  height: 76px;
  border-radius: 20px;
  object-fit: cover;
  box-shadow: 0 12px 30px rgba(244, 185, 66, 0.18);
}

.shop-item-copy {
  flex: 1;
}

.shop-item-title {
  font-size: 18px;
  font-weight: 700;
  color: #fff8e6;
}

.shop-item-desc {
  margin-top: 8px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.72);
}

.shop-item-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

@media (max-width: 600px) {
  .shop-summary-card {
    flex-direction: column;
  }
}
</style>
