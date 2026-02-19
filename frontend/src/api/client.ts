const API_BASE = 'http://localhost:8000'

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || err.message || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function createTask(input: string) {
  return api<{ taskId: string; status: string; message: string }>('/api/tasks', {
    method: 'POST',
    body: JSON.stringify({ input }),
  })
}

export async function uploadTask(file: File) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_BASE}/api/tasks/upload`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getTask(taskId: string) {
  return api<TaskResponse>(`/api/tasks/${taskId}`)
}

export async function listTasks(params?: { limit?: number; offset?: number }) {
  const q = new URLSearchParams(params as Record<string, string>)
  return api<{ items: TaskResponse[]; total: number }>(`/api/tasks?${q}`)
}

export async function cancelTask(taskId: string) {
  return api(`/api/tasks/${taskId}/cancel`, { method: 'POST' })
}

export async function exportTask(taskId: string, format: string) {
  return api<{ content: string; format: string }>(`/api/tasks/${taskId}/export?format=${format}`)
}

export interface TaskResponse {
  id: string
  input: string
  platform: string
  status: string
  progress: number
  stageProgress: Record<string, { status: string; progress: number }>
  metadata: Record<string, unknown>
  error: string | null
  result?: {
    fullText: string
    segments: { source: string; startTime: number; endTime: number; text: string }[]
    stats: Record<string, { segmentCount: number; charCount: number }>
  }
  createdAt: string
  updatedAt: string
}
