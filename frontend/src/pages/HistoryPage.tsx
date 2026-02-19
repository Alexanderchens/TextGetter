import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listTasks } from '../api/client'
import type { TaskResponse } from '../api/client'

export default function HistoryPage() {
  const [tasks, setTasks] = useState<TaskResponse[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listTasks({ limit: 50 })
      .then((r) => setTasks(r.items))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div>加载中…</div>

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-slate-800">历史记录</h1>
        <Link to="/" className="text-blue-600 hover:underline">返回首页</Link>
      </div>
      {tasks.length === 0 ? (
        <p className="text-slate-500">暂无历史任务</p>
      ) : (
        <div className="space-y-3">
          {tasks.map((t) => (
            <Link
              key={t.id}
              to={`/extract/${t.id}`}
              className="block p-4 bg-white border border-slate-200 rounded-lg hover:border-blue-300 hover:shadow-sm"
            >
              <div className="flex justify-between">
                <span className="font-medium truncate flex-1">
                  {(t.metadata as { title?: string })?.title || t.input?.slice(0, 60) || t.id}
                </span>
                <span className={`ml-2 px-2 py-0.5 rounded text-xs ${
                  t.status === 'completed' ? 'bg-green-100 text-green-800' :
                  t.status === 'failed' ? 'bg-red-100 text-red-800' :
                  'bg-slate-100 text-slate-600'
                }`}>
                  {t.status}
                </span>
              </div>
              <p className="text-sm text-slate-500 mt-1">
                {t.platform} · {t.createdAt ? new Date(t.createdAt).toLocaleString() : ''}
              </p>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
