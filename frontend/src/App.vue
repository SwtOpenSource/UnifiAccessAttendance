<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'

const auth = useAuthStore()
const router = useRouter()
const showNav = computed(() => auth.isLoggedIn)

function doLogout() {
  auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <header v-if="showNav" class="topbar">
    <div class="topbar-brand">🏆 打卡英雄榜</div>
    <nav class="topbar-nav">
      <router-link to="/board">排行榜</router-link>
      <router-link to="/leave">請假</router-link>
      <a href="javascript:void(0)" @click="doLogout">登出（{{ auth.displayName }}）</a>
    </nav>
  </header>
  <main>
    <router-view />
  </main>
</template>
