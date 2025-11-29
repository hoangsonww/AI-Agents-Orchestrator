<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm sticky top-0 z-50">
      <div class="px-6 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-4">
            <h1 class="text-2xl font-bold text-gray-900">🤖 AI Orchestrator</h1>
            <span class="text-sm text-gray-500">Collaborative AI Development</span>
          </div>
          <div class="flex items-center space-x-4">
            <StatusBadge :status="orchestratorStore.status" />
            <button
              @click="clearAll"
              class="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-md transition"
            >
              Clear
            </button>
          </div>
        </div>
      </div>
    </header>

    <div v-if="orchestratorStore.hasError" class="px-6 pt-4">
      <div class="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-md flex items-start justify-between">
        <div class="pr-4">
          <p class="text-sm font-semibold">Connection issue</p>
          <p class="text-sm mt-1">{{ orchestratorStore.errorMessage }}</p>
        </div>
        <button
          @click="orchestratorStore.clearError()"
          class="text-sm text-red-700 hover:text-red-900 ml-4"
        >
          Dismiss
        </button>
      </div>
    </div>

    <!-- Main Layout -->
    <div class="flex h-[calc(100vh-4rem)]">
      <!-- Sidebar -->
      <Sidebar />

      <!-- Main Content -->
      <main class="flex-1 overflow-auto">
        <MainContent />
      </main>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useOrchestratorStore } from './stores/orchestrator'
import Sidebar from './components/Sidebar.vue'
import MainContent from './components/MainContent.vue'
import StatusBadge from './components/StatusBadge.vue'

const orchestratorStore = useOrchestratorStore()

onMounted(() => {
  orchestratorStore.init()
})

const clearAll = () => {
  orchestratorStore.clear()
}
</script>
