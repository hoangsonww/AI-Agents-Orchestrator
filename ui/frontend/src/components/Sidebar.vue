<template>
  <aside class="w-80 bg-white shadow-sm p-6 overflow-y-auto">
    <div class="space-y-6">
      <!-- Task Input -->
      <div>
        <div class="flex items-center justify-between mb-2">
          <label class="block text-sm font-medium text-gray-700">
            Task Description
          </label>
          <div v-if="store.canFollowUp" class="flex items-center space-x-2">
            <label class="flex items-center space-x-1 cursor-pointer">
              <input
                v-model="conversationMode"
                type="checkbox"
                class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span class="text-xs text-gray-600">Conversation mode</span>
            </label>
          </div>
        </div>
        <textarea
          v-model="store.task"
          rows="4"
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          :placeholder="conversationMode && store.canFollowUp ? 'Continue with...' : 'Describe what you want to build...'"
          :disabled="store.isRunning"
          @keydown.enter.ctrl="handleExecute"
        ></textarea>
        <p v-if="conversationMode && store.canFollowUp" class="mt-1 text-xs text-green-600">
          💬 Messages will continue from previous task
        </p>
      </div>

      <!-- Workflow Selection -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Workflow
        </label>
        <select
          v-model="store.workflow"
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          :disabled="store.isRunning"
        >
          <option value="default">Default (Codex → Gemini → Claude)</option>
          <option value="quick">Quick (Codex only)</option>
          <option value="thorough">Thorough (Multi-review)</option>
          <option value="review-only">Review Only</option>
          <option value="document">Documentation</option>
        </select>
      </div>

      <!-- Max Iterations -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Max Iterations
        </label>
        <input
          type="number"
          v-model.number="store.maxIterations"
          min="1"
          max="10"
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          :disabled="store.isRunning"
        />
      </div>

      <!-- Execute Button -->
      <button
        @click="handleExecute"
        :disabled="store.isRunning || !store.task.trim()"
        class="w-full px-4 py-3 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-400 disabled:cursor-not-allowed transition"
      >
        {{ store.isRunning ? 'Executing...' : (conversationMode && store.canFollowUp ? 'Send Message' : 'Execute Task') }}
      </button>
      <p v-if="!conversationMode" class="mt-2 text-xs text-gray-500 text-center">
        Ctrl+Enter to execute
      </p>

      <!-- Follow-up Section -->
      <div v-if="store.canFollowUp && !store.isRunning" class="pt-6 border-t border-gray-200">
        <div class="flex items-center justify-between mb-2">
          <label class="block text-sm font-medium text-gray-700">
            Follow-up
          </label>
          <span class="text-xs text-green-600">✓ Ready</span>
        </div>
        <p class="text-xs text-gray-500 mb-2">
          Continue working on: "{{ store.lastTask.slice(0, 50) }}..."
        </p>
        <div class="flex space-x-2">
          <input
            v-model="followUpInput"
            type="text"
            placeholder="Add error handling..."
            class="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
            @keyup.enter="handleFollowUp"
          />
          <button
            @click="handleFollowUp"
            :disabled="!followUpInput.trim()"
            class="px-4 py-2 text-sm bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition"
          >
            Go
          </button>
        </div>
      </div>

      <!-- Agents Status -->
      <div class="pt-6 border-t border-gray-200">
        <h3 class="text-sm font-medium text-gray-700 mb-3">Agents Status</h3>
        <div class="space-y-2">
          <div
            v-for="agent in store.agents"
            :key="agent.name"
            class="flex items-center justify-between text-sm"
          >
            <span class="text-gray-700 capitalize">{{ agent.name }}</span>
            <span :class="agent.available ? 'text-green-600' : 'text-gray-400'">
              {{ agent.available ? '✓' : '○' }}
            </span>
          </div>
        </div>
      </div>

      <!-- Live Progress Logs -->
      <div v-if="store.hasLogs && store.isRunning" class="pt-6 border-t border-gray-200">
        <div class="flex items-center justify-between mb-2">
          <h3 class="text-sm font-medium text-gray-700">Live Progress</h3>
          <span class="text-xs text-blue-600 animate-pulse">● Running</span>
        </div>
        <div class="bg-gray-900 rounded-lg p-3 max-h-40 overflow-y-auto font-mono text-xs">
          <div
            v-for="log in store.logs.slice(-5)"
            :key="log.id"
            :class="{
              'text-blue-400': log.level === 'info',
              'text-green-400': log.level === 'success',
              'text-yellow-400': log.level === 'warn' || log.level === 'warning',
              'text-red-400': log.level === 'error',
              'text-gray-400': !['info', 'success', 'warn', 'warning', 'error'].includes(log.level)
            }"
            class="mb-1"
          >
            {{ log.message }}
          </div>
        </div>
        <p class="mt-1 text-xs text-gray-500 text-center">
          View all logs in the Logs tab
        </p>
      </div>

      <!-- Files Created -->
      <div v-if="store.hasFiles" class="pt-6 border-t border-gray-200">
        <h3 class="text-sm font-medium text-gray-700 mb-3">Generated Files</h3>
        <div class="space-y-1">
          <button
            v-for="file in store.files"
            :key="file"
            @click="store.loadFile(file)"
            class="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition"
          >
            📄 {{ file }}
          </button>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useOrchestratorStore } from '../stores/orchestrator'

const store = useOrchestratorStore()
const followUpInput = ref('')
const conversationMode = ref(false)

// Auto-enable conversation mode when follow-up becomes available
watch(() => store.canFollowUp, (canFollowUp) => {
  if (canFollowUp && !conversationMode.value) {
    // Don't auto-enable, let user choose
  }
})

const handleExecute = () => {
  if (conversationMode.value && store.canFollowUp) {
    // Execute as follow-up
    store.executeFollowUp(store.task)
  } else {
    // Execute as new task
    store.executeTask()
    conversationMode.value = false // Reset conversation mode
  }
}

const handleFollowUp = () => {
  if (followUpInput.value.trim()) {
    store.executeFollowUp(followUpInput.value)
    followUpInput.value = ''
  }
}
</script>
