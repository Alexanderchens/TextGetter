import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createTask, uploadTask } from '../api/client'

export default function HomePage() {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { taskId } = await createTask(input.trim())
      navigate(`/extract/${taskId}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建失败')
    } finally {
      setLoading(false)
    }
  }

  const handleFile = async (file: File) => {
    if (!file.type.startsWith('video/') && !file.type.startsWith('image/')) {
      setError('请上传视频或图片文件')
      return
    }
    setError('')
    setLoading(true)
    try {
      const { taskId } = await uploadTask(file)
      navigate(`/extract/${taskId}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : '上传失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">提取视频文案</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-600 mb-2">链接或本地路径</label>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="B站链接(如 https://www.bilibili.com/video/BVxxx) 或本地路径(如 /Users/xxx/video.mp4)"
            className="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? '处理中…' : '开始提取'}
        </button>
      </form>

      <div className="mt-8">
        <p className="text-sm text-slate-500 mb-2">或拖拽文件到此处上传</p>
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragOver(false)
            const f = e.dataTransfer.files[0]
            if (f) handleFile(f)
          }}
          className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
            dragOver ? 'border-blue-500 bg-blue-50' : 'border-slate-300'
          }`}
        >
          <p className="text-slate-500">将视频或图片拖放到此处</p>
        </div>
        <input
          type="file"
          accept="video/*,image/*"
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          className="mt-2"
        />
      </div>

      {error && <p className="mt-4 text-red-600">{error}</p>}

      <a href="/history" className="mt-8 inline-block text-blue-600 hover:underline">
        查看历史记录 →
      </a>
    </div>
  )
}
