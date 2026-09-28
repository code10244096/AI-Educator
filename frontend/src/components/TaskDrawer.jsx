import React, { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ListChecks, FileCheck, FileText, Loader2, CheckCircle2, XCircle, ChevronRight, RotateCw } from 'lucide-react'
import { useTask } from '../context/TaskContext'
import { useLayout } from '../context/LayoutContext'
import { formatRelative } from '../utils/time'

// 顶栏“后台任务”：进行中数字角标；点开显示最近的批改 / 教案任务、进度、失败原因，可跳转（R1-006）
const StatusIcon = ({ status }) => {
  if (status === 'running') return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
  if (status === 'failed') return <XCircle className="h-4 w-4 text-red-500" />
  return <CheckCircle2 className="h-4 w-4 text-green-500" />
}

const targetOf = (task) => {
  if (task.type === 'lessonplan') return task.planId ? `/lessonplan?id=${task.planId}` : '/lessonplan'
  if (task.submissionId) return `/tasks/sub-${task.submissionId}`
  return '/grader'
}

const TaskDrawer = () => {
  const navigate = useNavigate()
  const { closeSidebar } = useLayout()
  const { tasks, runningCount, unseenCount, markSeen, refresh } = useTask()
  const [open, setOpen] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    markSeen()
    const onClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    const onKey = (e) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', onClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [open, markSeen])

  const go = (task) => {
    setOpen(false)
    navigate(targetOf(task))
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await refresh()
    } finally {
      setRefreshing(false)
    }
  }

  const list = tasks.slice(0, 20)

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(v => {
          const next = !v
          if (next) closeSidebar()
          return next
        })}
        className="relative rounded-lg p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-800"
        aria-label={runningCount ? `后台任务，${runningCount} 个进行中` : '后台任务'}
        aria-haspopup="dialog"
        aria-expanded={open}
        title="后台任务"
        data-testid="task-drawer-button"
      >
        <ListChecks className="h-5 w-5" />
        {runningCount > 0 ? (
          <span className="absolute -right-0.5 -top-0.5 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-blue-600 px-1 text-[11px] font-medium leading-none text-white">
            {runningCount > 99 ? '99+' : runningCount}
          </span>
        ) : unseenCount > 0 ? (
          <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-green-500" aria-hidden="true" />
        ) : null}
      </button>

      {open && (
        <div
          className="fixed left-2 right-2 top-16 z-[60] mt-1 overflow-hidden rounded-xl border border-gray-200 bg-white shadow-lg sm:left-auto sm:w-96"
          role="dialog"
          aria-label="后台任务"
        >
          <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
            <div>
              <div className="text-sm font-semibold text-gray-900">后台任务</div>
              <div className="text-xs text-gray-400">{runningCount ? `${runningCount} 个进行中，可以离开页面，完成后会提示` : '批改和教案生成都在后台进行'}</div>
            </div>
            <button
              type="button"
              onClick={handleRefresh}
              className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
              aria-label="刷新"
              title="刷新"
            >
              <RotateCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            </button>
          </div>
          <div className="max-h-[60vh] overflow-y-auto">
            {list.length === 0 ? (
              <div className="px-4 py-10 text-center">
                <p className="text-sm text-gray-500">还没有后台任务</p>
                <p className="mt-1 text-xs text-gray-400">上传作业批改或生成教案后，进度会显示在这里</p>
              </div>
            ) : (
              <ul className="divide-y divide-gray-50">
                {list.map((task) => {
                  const TypeIcon = task.type === 'lessonplan' ? FileText : FileCheck
                  return (
                    <li key={task.id}>
                      <button
                        type="button"
                        onClick={() => go(task)}
                        className="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-gray-50"
                      >
                        <TypeIcon className="mt-0.5 h-4 w-4 flex-shrink-0 text-gray-400" />
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="truncate text-sm text-gray-900">{task.title}</span>
                          </div>
                          {task.status === 'running' && (
                            <div className="mt-1.5">
                              <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-100">
                                <div className="h-full rounded-full bg-blue-500 transition-all" style={{ width: `${Math.max(5, task.progress || 0)}%` }} />
                              </div>
                              <div className="mt-1 text-xs text-gray-500">{task.progressLabel || '处理中'}</div>
                            </div>
                          )}
                          {task.status === 'failed' && (
                            <div className="mt-1 line-clamp-2 text-xs text-red-600">{task.error}</div>
                          )}
                          {task.status === 'completed' && (
                            <div className="mt-1 text-xs text-gray-400">
                              {task.type === 'grader' ? '批改完成' : '教案已生成'}
                              {task.createdAt ? ` · ${formatRelative(task.createdAt)}` : ''}
                            </div>
                          )}
                        </div>
                        <div className="flex flex-shrink-0 items-center gap-1 pt-0.5">
                          <StatusIcon status={task.status} />
                          <ChevronRight className="h-4 w-4 text-gray-300" />
                        </div>
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default TaskDrawer
