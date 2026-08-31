<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { publicBoardApi } from '@/api'
import type { PublicBoardRow } from '@/types'

const route = useRoute()
const slug = route.params.slug as string

function today(): string {
  return new Date().toISOString().slice(0, 10)
}
function daysAgo(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString().slice(0, 10)
}

const rows = ref<PublicBoardRow[]>([])
const loading = ref(true)
const notFound = ref(false)

function rankBadgeClass(i: number): string {
  return i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : ''
}

onMounted(async () => {
  try {
    rows.value = await publicBoardApi.fetch(slug, daysAgo(6), today())
  } catch {
    notFound.value = true
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div style="max-width: 640px; margin: 40px auto;">
    <h1 style="text-align:center; color: var(--brand);">🏆 打卡英雄榜</h1>
    <p style="text-align:center; color:var(--muted); font-size:13px;">近 7 天準時率排行（公開唯讀）</p>

    <div v-if="loading" class="card">載入中…</div>
    <div v-else-if="notFound" class="card">此排行榜連結不存在或已關閉</div>
    <div v-else class="card">
      <table>
        <thead><tr><th>排名</th><th>姓名</th><th>部門</th><th>準時率</th><th>連續全勤</th></tr></thead>
        <tbody>
          <tr v-for="(r, i) in rows" :key="i">
            <td><span class="rank-badge" :class="rankBadgeClass(i)">{{ i + 1 }}</span></td>
            <td>{{ r.display_name }}</td>
            <td>{{ r.department || '-' }}</td>
            <td>{{ r.on_time_rate }}%</td>
            <td>{{ r.streak }} 天</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
