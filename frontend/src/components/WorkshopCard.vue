<script setup lang="ts">
import type { Registration, Workshop } from '../types'
import { computed } from 'vue'
import { MY_STATUS_LABEL } from '../constants'
import SeatMeter from './SeatMeter.vue'
import StatusBadge from './StatusBadge.vue'

const props = defineProps<{
  workshop: Workshop
  registration?: Registration
  signedIn: boolean
  pending: boolean
  error?: string
}>()

defineEmits<{
  (e: 'register'): void
  (e: 'cancel'): void
}>()

const isFull = computed(() => props.workshop.seats_left === 0)
const myStatus = computed(() => {
  const status = props.registration?.status
  return status && status !== 'cancelled' ? status : null
})

const start = computed(() => new Date(props.workshop.starts_at))
const month = computed(() => start.value.toLocaleDateString(undefined, { month: 'short' }))
const day = computed(() => start.value.getDate())
const when = computed(() => start.value.toLocaleString())
</script>

<template>
  <li class="card flex gap-4">
    <div
      class="text-primary leading-tight py-2 text-center rounded-md bg-primary-subtle shrink-0 w-14 self-start"
      aria-hidden="true"
    >
      <div class="text-xs font-600 uppercase">
        {{ month }}
      </div>
      <div class="text-xl font-700">
        {{ day }}
      </div>
    </div>
    <div class="flex-1 gap-3 grid min-w-0">
      <div>
        <h2 class="text-lg font-600 m-0">
          {{ workshop.title }}
        </h2>
        <p class="text-sm text-muted m-0 mt-1 flex gap-1 items-center">
          <span class="i-lucide-clock" aria-hidden="true" />
          <time :datetime="workshop.starts_at">{{ when }}</time>
        </p>
      </div>
      <div class="gap-1 grid">
        <SeatMeter :capacity="workshop.capacity" :taken="workshop.seats_taken" />
        <p class="text-sm m-0 flex gap-1 items-center" :class="isFull ? 'text-danger' : 'text-muted'" aria-live="polite">
          <span class="i-lucide-armchair" aria-hidden="true" />
          {{ isFull ? 'Full - join the waitlist' : `${workshop.seats_left} of ${workshop.capacity} seats left` }}
        </p>
      </div>
      <div v-if="signedIn" class="flex flex-wrap gap-3 items-center" aria-live="polite">
        <StatusBadge v-if="myStatus" :status="myStatus">
          {{ MY_STATUS_LABEL[myStatus] }}
        </StatusBadge>
        <StatusBadge v-else-if="isFull" status="full">
          Full
        </StatusBadge>
        <button v-if="myStatus" class="btn-ghost-danger" :disabled="pending" @click="$emit('cancel')">
          Cancel
        </button>
        <button v-else class="btn-primary" :disabled="pending" @click="$emit('register')">
          {{ isFull ? 'Join waitlist' : 'Register' }}
        </button>
      </div>
      <p v-if="error" class="text-sm text-danger m-0" role="alert">
        {{ error }}
      </p>
    </div>
  </li>
</template>
