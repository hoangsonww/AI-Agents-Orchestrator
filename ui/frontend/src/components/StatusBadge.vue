<template>
  <span :class="['status-badge', `status-${status}`]">
    {{ statusText }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: {
    type: String,
    required: true
  }
})

const statusText = computed(() => {
  return props.status.charAt(0).toUpperCase() + props.status.slice(1)
})
</script>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
}

.status-idle {
  background-color: #e5e7eb;
  color: #374151;
}

.status-running {
  background-color: #fef3c7;
  color: #92400e;
  animation: pulse 2s ease-in-out infinite;
}

.status-completed {
  background-color: #d1fae5;
  color: #065f46;
}

.status-error,
.status-failed {
  background-color: #fee2e2;
  color: #991b1b;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}
</style>
