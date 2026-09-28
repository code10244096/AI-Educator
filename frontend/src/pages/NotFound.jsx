import React, { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Compass, LayoutDashboard } from 'lucide-react'

// 404（R1-014 / L-U08）：未知路由不白屏，提供回到工作台的入口
const NotFound = () => {
  const navigate = useNavigate()
  useEffect(() => {
    document.title = '页面不存在 - AI 教学助手'
    return () => { document.title = 'AI 教学助手' }
  }, [])

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center" data-testid="not-found">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-blue-50">
        <Compass className="h-7 w-7 text-blue-500" />
      </div>
      <h1 className="mt-5 text-xl font-semibold text-gray-900">页面不存在</h1>
      <p className="mt-2 max-w-sm text-sm text-gray-500">链接可能已失效，或者页面已被移动。</p>
      <div className="mt-6 flex flex-wrap justify-center gap-3">
        <button
          type="button"
          onClick={() => navigate('/', { replace: true })}
          className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          <LayoutDashboard className="h-4 w-4" />
          回到工作台
        </button>
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          返回上一页
        </button>
      </div>
    </div>
  )
}

export default NotFound
