<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  capacity: number
  taken: number
}>()

// The text next to the meter carries the numbers, so the bar is decorative.
const ratio = computed(() => (props.capacity > 0 ? Math.min(props.taken / props.capacity, 1) : 1))
const tone = computed(() => {
  if (ratio.value >= 1)
    return 'bg-danger'
  return ratio.value >= 0.8 ? 'bg-warning' : 'bg-success'
})
</script>

<template>
  <div class="rounded-full bg-secondary h-2 overflow-hidden" aria-hidden="true">
    <div
      data-testid="fill"
      class="rounded-full h-full transition-[width] duration-300"
      :class="tone"
      :style="{ width: `${ratio * 100}%` }"
    />
  </div>
</template>
