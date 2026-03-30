<template>
  <div v-if="normalizedMedals.length" class="user-medals" :class="{ compact }">
    <div
      v-for="medal in normalizedMedals"
      :key="`${medal.code}-${medal.acquired_at || medal.name}`"
      class="medal-badge"
      :class="{ compact, special: medal.is_special }"
      :title="`${medal.name} · 积分加成 x${formatMultiplier(medal.multiplier)}`"
      role="button"
      tabindex="0"
      :aria-label="`${medal.name}，积分加成 x${formatMultiplier(medal.multiplier)}`"
      @click="openMedalDetail(medal)"
      @keydown.enter.prevent="openMedalDetail(medal)"
      @keydown.space.prevent="openMedalDetail(medal)"
    >
      <div class="medal-icon-wrap">
        <img
          v-if="medal.icon_url"
          :src="medal.icon_url"
          :alt="medal.name"
          class="medal-icon"
        >
        <v-icon v-else size="18">mdi-medal</v-icon>
      </div>
      <span v-if="showNames" class="medal-name">{{ medal.name }}</span>
    </div>

    <v-dialog v-model="detailDialog" max-width="360">
      <v-card class="medal-detail-card" rounded="xl">
        <v-card-text v-if="selectedMedal" class="pa-5">
          <div class="medal-detail-header">
            <div class="medal-detail-icon-wrap">
              <img
                v-if="selectedMedal.icon_url"
                :src="selectedMedal.icon_url"
                :alt="selectedMedal.name"
                class="medal-detail-icon"
              >
              <v-icon v-else size="28" color="amber-darken-2">mdi-medal</v-icon>
            </div>
            <div class="medal-detail-copy">
              <div class="medal-detail-name">{{ selectedMedal.name }}</div>
              <div class="medal-detail-multiplier">
                积分加成 x{{ formatMultiplier(selectedMedal.multiplier) }}
              </div>
            </div>
          </div>

          <v-chip
            v-if="selectedMedal.is_special"
            color="amber-darken-1"
            variant="tonal"
            size="small"
            class="mb-3"
          >
            特殊勋章
          </v-chip>

          <div v-if="selectedMedal.description" class="medal-detail-description">
            {{ selectedMedal.description }}
          </div>
        </v-card-text>

        <v-card-actions class="px-5 pb-4 pt-0">
          <v-spacer />
          <v-btn color="amber-darken-2" variant="text" @click="closeMedalDetail">
            知道了
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
export default {
  name: 'UserMedals',
  data() {
    return {
      detailDialog: false,
      selectedMedal: null
    }
  },
  props: {
    medals: {
      type: Array,
      default: () => []
    },
    compact: {
      type: Boolean,
      default: false
    },
    showNames: {
      type: Boolean,
      default: false
    }
  },
  computed: {
    normalizedMedals() {
      return Array.isArray(this.medals) ? this.medals : []
    }
  },
  methods: {
    formatMultiplier(multiplier) {
      return Number(multiplier || 1).toFixed(2)
    },
    openMedalDetail(medal) {
      this.selectedMedal = medal
      this.detailDialog = true
    },
    closeMedalDetail() {
      this.detailDialog = false
      this.selectedMedal = null
    }
  }
}
</script>

<style scoped>
.user-medals {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.user-medals.compact {
  gap: 6px;
  margin-top: 6px;
}

.medal-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px 4px 6px;
  border-radius: 999px;
  background: linear-gradient(135deg, rgba(244, 185, 66, 0.2), rgba(255, 243, 205, 0.08));
  border: 1px solid rgba(244, 185, 66, 0.35);
  box-shadow: 0 8px 20px rgba(244, 185, 66, 0.12);
  cursor: pointer;
  transition: transform 0.16s ease, box-shadow 0.16s ease;
}

.medal-badge.special {
  background: linear-gradient(135deg, rgba(255, 201, 71, 0.3), rgba(180, 83, 9, 0.12));
  border-color: rgba(255, 201, 71, 0.45);
}

.medal-badge:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(244, 185, 66, 0.2);
}

.medal-badge:focus-visible {
  outline: 2px solid rgba(255, 201, 71, 0.85);
  outline-offset: 2px;
}

.medal-badge.compact {
  padding: 3px 6px;
  gap: 0;
}

.medal-icon-wrap {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.85);
}

.compact .medal-icon-wrap {
  width: 22px;
  height: 22px;
}

.medal-icon {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.medal-name {
  font-size: 12px;
  line-height: 1;
  color: #f8ecd1;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.medal-detail-card {
  background: var(--hbo-bg-card, #1f1f1f) !important;
  color: var(--hbo-text-primary, #fff);
  border: 1px solid rgba(255, 201, 71, 0.28);
}

.medal-detail-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 12px;
}

.medal-detail-icon-wrap {
  width: 56px;
  height: 56px;
  border-radius: 18px;
  overflow: hidden;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(255, 244, 214, 0.92));
}

.medal-detail-icon {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.medal-detail-copy {
  min-width: 0;
}

.medal-detail-name {
  font-size: 16px;
  font-weight: 700;
  color: var(--hbo-text-primary, #fff);
}

.medal-detail-multiplier {
  margin-top: 4px;
  font-size: 14px;
  font-weight: 600;
  color: #ffcf5c;
}

.medal-detail-description {
  font-size: 13px;
  line-height: 1.6;
  color: var(--hbo-text-secondary, rgba(255,255,255,0.75));
}
</style>
