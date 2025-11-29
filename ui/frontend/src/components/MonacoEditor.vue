<template>
  <div ref="editorContainer" class="code-editor h-[600px]"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as monaco from 'monaco-editor'
import { useOrchestratorStore } from '../stores/orchestrator'

const store = useOrchestratorStore()
const editorContainer = ref(null)
let editor = null

onMounted(() => {
  if (editorContainer.value) {
    editor = monaco.editor.create(editorContainer.value, {
      value: '// Code will appear here...',
      language: 'python',
      theme: 'vs-dark',
      automaticLayout: true,
      minimap: { enabled: true },
      fontSize: 14,
      lineNumbers: 'on',
      renderWhitespace: 'selection',
      scrollBeyondLastLine: false,
      readOnly: false
    })

    // Update store when editor content changes
    editor.onDidChangeModelContent(() => {
      store.fileContent = editor.getValue()
    })
  }
})

onUnmounted(() => {
  if (editor) {
    editor.dispose()
  }
})

// Watch for file changes
watch(() => store.currentFile, (newFile) => {
  if (editor && newFile) {
    editor.setValue(newFile.content)
    monaco.editor.setModelLanguage(editor.getModel(), newFile.language)
  }
})

// Watch for fileContent changes from store
watch(() => store.fileContent, (newContent) => {
  if (editor && newContent !== editor.getValue()) {
    editor.setValue(newContent)
  }
})
</script>

<style scoped>
.code-editor {
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  overflow: hidden;
}
</style>
