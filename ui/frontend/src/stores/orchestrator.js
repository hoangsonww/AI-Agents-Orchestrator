import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { io } from 'socket.io-client'
import axios from 'axios'

const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:5001'
const socketBaseUrl = apiBaseUrl
const socketPath = import.meta.env.VITE_SOCKET_PATH || '/socket.io'
const socketTransportsEnv = import.meta.env.VITE_SOCKET_TRANSPORTS
const socketTransports = socketTransportsEnv
  ? socketTransportsEnv.split(',').map((t) => t.trim()).filter(Boolean)
  : ['websocket', 'polling']
const api = axios.create({ baseURL: apiBaseUrl })

export const useOrchestratorStore = defineStore('orchestrator', () => {
  // State
  const socket = ref(null)
  const status = ref('idle') // idle, running, completed, error
  const task = ref('')
  const workflow = ref('default')
  const maxIterations = ref(3)
  const output = ref('')
  const files = ref([])
  const iterations = ref([])
  const agents = ref([])
  const workflows = ref([])
  const currentFile = ref(null)
  const fileContent = ref('')
  const lastTask = ref('')
  const lastOutput = ref('')
  const canFollowUp = ref(false)
  const errorMessage = ref('')
  const logs = ref([])
  let logCounter = 0

  // Computed
  const isRunning = computed(() => status.value === 'running')
  const hasOutput = computed(() => output.value.length > 0)
  const hasFiles = computed(() => files.value.length > 0)
  const hasError = computed(() => errorMessage.value.length > 0)
  const hasLogs = computed(() => logs.value.length > 0)

  const buildApiErrorMessage = (error, context) => {
    if (error?.response) {
      if (error.response.status === 403) {
        return `${context}: Forbidden (403). Start the backend on ${apiBaseUrl} and ensure it allows browser requests.`
      }
      return `${context}: Server responded with ${error.response.status}`
    }
    if (error?.request) {
      return `${context}: Unable to reach the backend. Is it running on ${apiBaseUrl}?`
    }
    return `${context}: ${error?.message || 'Unknown error'}`
  }

  const setError = (message) => {
    errorMessage.value = message
  }

  const addLog = (message, level = 'info') => {
    logs.value.push({
      id: ++logCounter,
      message,
      level,
      time: new Date().toLocaleTimeString()
    })
  }

  // Actions
  function init() {
    const attachSocket = (transports) => {
      if (socket.value) {
        socket.value.removeAllListeners()
        socket.value.disconnect()
      }

      const socketOptions = {
        path: socketPath,
        transports,
        forceNew: true,
        withCredentials: false
      }

      console.info('Connecting to Socket.IO', {
        url: `${socketBaseUrl}${socketPath}`,
        transports
      })

      socket.value = io(socketBaseUrl, socketOptions)

      socket.value.on('connect', () => {
        console.log('Connected to server')
        status.value = 'idle'
        setError('')
        addLog('Connected to backend', 'success')
      })

      socket.value.on('disconnect', () => {
        console.log('Disconnected from server')
        setError(`Lost connection to the backend. Check that it is running on ${apiBaseUrl}.`)
        addLog('Disconnected from backend', 'warn')
      })

      socket.value.on('connect_error', (error) => {
        console.error('Socket connection error:', error)
        setError(`Unable to reach the backend (WebSocket/polling). URL: ${socketBaseUrl}${socketPath} via [${transports.join(', ')}]. Ensure the server at ${apiBaseUrl} is accessible.`)
        status.value = 'error'
        addLog('Socket connection error; check backend availability.', 'error')
      })

      socket.value.on('task_started', (data) => {
        console.log('Task started:', data)
        status.value = 'running'
        addLog(`Task started (workflow: ${data.workflow || workflow.value})`, 'info')
      })

      socket.value.on('progress_log', (data) => {
        console.log('>>> PROGRESS LOG RECEIVED <<<', data)
        console.log('Current logs count:', logs.value.length)
        addLog(data.message, data.level)
        console.log('After addLog, logs count:', logs.value.length)
      })

      socket.value.on('task_completed', (data) => {
        console.log('Task completed:', data)
        status.value = data.success ? 'completed' : 'error'
        output.value = data.output || ''
        files.value = data.files || []
        iterations.value = data.iterations || []

        // Store for follow-ups
        lastTask.value = data.task
        lastOutput.value = data.output || ''
        canFollowUp.value = data.success !== false
        addLog(`Task completed ${data.success === false ? '(failed)' : 'successfully'}`, data.success === false ? 'warn' : 'success')
      })

      socket.value.on('task_error', (data) => {
        console.error('Task error:', data)
        status.value = 'error'
        output.value = `Error: ${data.error}`
        addLog(`Task error: ${data.error}`, 'error')
      })
    }

    // Initialize Socket.IO (default to websocket+polling)
    attachSocket(socketTransports.length ? socketTransports : ['websocket', 'polling'])

    // Load agents and workflows
    loadAgents()
    loadWorkflows()
  }

  async function loadAgents() {
    try {
      const response = await api.get('/api/agents')
      agents.value = response.data.agents
      setError('')
    } catch (error) {
      console.error('Failed to load agents:', error)
      setError(buildApiErrorMessage(error, 'Failed to load agents'))
    }
  }

  async function loadWorkflows() {
    try {
      const response = await api.get('/api/workflows')
      workflows.value = response.data.workflows
      setError('')
    } catch (error) {
      console.error('Failed to load workflows:', error)
      setError(buildApiErrorMessage(error, 'Failed to load workflows'))
    }
  }

  async function executeTask() {
    if (!task.value.trim()) {
      alert('Please enter a task description')
      return
    }

    // Clear previous logs for new task
    logs.value = []
    logCounter = 0

    try {
      const response = await api.post('/api/execute', {
        task: task.value,
        workflow: workflow.value,
        max_iterations: maxIterations.value,
        is_followup: false
      })
      console.log('Task submitted:', response.data)
      addLog('Task submitted to backend', 'info')
      // Clear task input after submission
      task.value = ''
      setError('')
    } catch (error) {
      console.error('Failed to execute task:', error)
      setError(buildApiErrorMessage(error, 'Failed to execute task'))
      alert('Failed to execute task')
    }
  }

  async function loadFile(filename) {
    try {
      const response = await api.get(`/api/files/${filename}`)
      currentFile.value = response.data
      fileContent.value = response.data.content
      setError('')
    } catch (error) {
      console.error('Failed to load file:', error)
      setError(buildApiErrorMessage(error, 'Failed to load file'))
      alert('Failed to load file')
    }
  }

  async function executeFollowUp(followUpInstructions) {
    if (!lastTask.value) {
      alert('No previous task to follow up on')
      return
    }

    try {
      const response = await api.post('/api/execute', {
        task: followUpInstructions,
        workflow: workflow.value,
        max_iterations: maxIterations.value,
        is_followup: true
      })
      console.log('Follow-up submitted:', response.data)
      addLog('Follow-up submitted to backend', 'info')
      // Clear task input after submission
      task.value = ''
      setError('')
    } catch (error) {
      console.error('Failed to execute follow-up:', error)
      setError(buildApiErrorMessage(error, 'Failed to execute follow-up'))
      alert('Failed to execute follow-up')
    }
  }

  function clear() {
    task.value = ''
    output.value = ''
    files.value = []
    iterations.value = []
    currentFile.value = null
    fileContent.value = ''
    status.value = 'idle'
    lastTask.value = ''
    lastOutput.value = ''
    canFollowUp.value = false
    setError('')
    logs.value = []
    logCounter = 0
  }

  function downloadFile(filename, content) {
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename.split('/').pop()
    a.click()
    URL.revokeObjectURL(url)
  }

  return {
    // State
    status,
    task,
    workflow,
    maxIterations,
    output,
    files,
    iterations,
    agents,
    workflows,
    currentFile,
    fileContent,
    lastTask,
    lastOutput,
    canFollowUp,
    errorMessage,
    logs,
    // Computed
    isRunning,
    hasOutput,
    hasFiles,
    hasError,
    hasLogs,
    // Actions
    init,
    executeTask,
    executeFollowUp,
    loadFile,
    clear,
    clearError: () => setError(''),
    downloadFile
  }
})
