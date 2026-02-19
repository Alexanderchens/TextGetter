import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getTask, cancelTask, exportTask } from '../api/client'
import type { TaskResponse } from '../api/client'

export default function ExtractDetailPage() {
  const { taskId } = useParams<{ taskId: string }>()
  const [task, setTask] = useState<TaskResponse | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!taskId) return
    const fetchTask = async () => {
      try {
        const t = await getTask(taskId)
        setTask(t)
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取失败')
      }
    }
    fetchTask()
    const done = ['completed', 'failed', 'cancelled']
    const interval = setInterval(async () => {
      const t = await getTask(taskId).catch(() => null)
      if (t) setTask(t)
      if (t && done.includes(t.status)) clearInterval(interval)
    }, 2000)
    return () => clearInterval(interval)
  }, [taskId])

  const handleCancel = async () => {
    if (!taskId) return
    try {
      await cancelTask(taskId)
      setTask((t) => t ? { ...t, status: 'cancelled' } : t)
    } catch {}
  }

  const handleCopy = async () => {
    if (!task?.result?.fullText) return
    await navigator.clipboard.writeText(task.result.fullText)
  }

  const handleExport = async (format: string) => {
    if (!taskId) return
    const { content } = await exportTask(taskId, format)
    const a = document.createElement('a')
    a.href = URL.createObjectURL(new Blob([content]))
    a.download = `extract.${format}`
    a.click()
  }

  if (error) return <div className="text-red-600">{error}</div>
  if (!task) return <div>加载中…</div>

  const done = ['completed', 'failed', 'cancelled'].includes(task.status)

  return (
    <div>
      <Link to="/" className="text-blue-600 hover:underline mb-4 inline-block">← 返回</Link>
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <div className="flex justify-between items-center mb-4">
          <h1 className="text-xl font-bold">任务 #{taskId?.slice(0, 8)}</h1>
          <span className={`px-2 py-1 rounded text-sm ${
            task.status === 'completed' ? 'bg-green-100 text-green-800' :
            task.status === 'failed' ? 'bg-red-100 text-red-800' :
            'bg-slate-100 text-slate-800'
          }`}>
            {task.status}
          </span>
        </div>
        <p className="text-slate-500 text-sm mb-4">平台: {task.platform} · 进度: {task.progress}%</p>

        {!done && task.status !== 'cancelled' && (
          <button onClick={handleCancel} className="text-red-600 hover:underline text-sm">
            取消任务
          </button>
        )}

        {task.stageProgress && Object.keys(task.stageProgress).length > 0 && (
          <div className="mt-4 space-y-2">
            {Object.entries(task.stageProgress).map(([name, sp]) => (
              <div key={name} className="flex items-center gap-2 text-sm">
                <span className="w-24">{name}</span>
                <span className="text-slate-500">{sp.status}</span>
                {sp.progress !== undefined && <span>{sp.progress}%</span>}
              </div>
            ))}
          </div>
        )}

        {task.error && <p className="mt-4 text-red-600">{task.error}</p>}

        {task.result && (
          <div className="mt-6">
            <div className="flex gap-2 mb-4">
              <button onClick={handleCopy} className="px-4 py-2 bg-slate-100 rounded hover:bg-slate-200">
                复制
              </button>
              <button onClick={() => handleExport('txt')} className="px-4 py-2 bg-slate-100 rounded hover:bg-slate-200">
                导出 TXT
              </button>
            </div>
            <div className="border border-slate-200 rounded p-4 bg-slate-50 min-h-[200px]">
              {task.result.segments?.length ? (
                <div className="space-y-3">
                  {task.result.segments.map((s, i) => (
                    <div key={i} className="flex gap-2">
                      <span className="text-xs text-slate-400 shrink-0">
                        [{s.source}] {s.startTime.toFixed(1)}s
                      </span>
                      <span>{s.text}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <pre className="whitespace-pre-wrap font-sans">{task.result.fullText || '（空）'}</pre>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
