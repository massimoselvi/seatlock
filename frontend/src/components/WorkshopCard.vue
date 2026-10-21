<script setup lang="ts">
import type { Registration, Workshop } from '../types'
import { computed } from 'vue'
import { MY_STATUS_LABEL } from '../constants'

const props = defineProps<{
  workshop: Workshop
  registration?: Registration
  signedIn: boolean
  pending: boolean
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
</script>

<template>
  <li>
    <h2>{{ workshop.title }}</h2>
    <time :datetime="workshop.starts_at">{{ new Date(workshop.starts_at).toLocaleString() }}</time>
    <p class="seats" :class="{ full: isFull }">
      {{ isFull ? 'Full - join the waitlist' : `${workshop.seats_left} of ${workshop.capacity} seats left` }}
    </p>
    <template v-if="signedIn">
      <p v-if="myStatus" class="badge" :class="myStatus">
        {{ MY_STATUS_LABEL[myStatus] }}
      </p>
      <button v-if="myStatus" :disabled="pending" @click="$emit('cancel')">
        Cancel
      </button>
      <button v-else :disabled="pending" @click="$emit('register')">
        {{ isFull ? 'Join waitlist' : 'Register' }}
      </button>
    </template>
  </li>
</template>
