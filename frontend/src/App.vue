<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchWorkshops, type Workshop } from './api'

const workshops = ref<Workshop[]>([])
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    workshops.value = await fetchWorkshops()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Something went wrong'
  }
})
</script>

<template>
  <main>
    <h1>Seatlock</h1>
    <p class="lead">Workshops with limited seats. No overselling, ever.</p>
    <p v-if="error" class="error">{{ error }}</p>
    <ul v-else class="cards">
      <li v-for="w in workshops" :key="w.id">
        <h2>{{ w.title }}</h2>
        <time :datetime="w.starts_at">{{ new Date(w.starts_at).toLocaleString() }}</time>
        <p class="seats" :class="{ full: w.seats_left === 0 }">
          {{ w.seats_left === 0 ? 'Full - join the waitlist' : `${w.seats_left} of ${w.capacity} seats left` }}
        </p>
      </li>
    </ul>
  </main>
</template>
