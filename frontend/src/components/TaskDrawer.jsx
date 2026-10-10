import React, { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ListChecks, FileCheck, FileText, Loader2, CheckCircle2, XCircle, ChevronRight, RotateCw, Trash2 } from 'lucide-react'
import { useTask } from '../context/TaskContext'
import { useLayout } from '../context/LayoutContext'
import { useToast } from './Toast'
import ConfirmDialog from './ConfirmDialog'
import { homeworkAPI, lessonPlanAPI, getErrorMessage } from '../utils/api'
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

// 真正删除记录：批改走 /grader/{id}（连同同步到错题本的错题），教案走 /lessonplan/{id}
const deleteRecord = (task) => {
  if (task.type === 'grader' && task.submissionId) return homeworkAPI.deleteSubmission(task.submissionId)
  if (task.type === 'lessonplan' && task.planId) return lessonPlanAPI.remove(task.planId)
  return Promise.resolve() // 刚提交、服务端还没建档的占位任务：只从面板移除
}

const TaskDrawer = () => {
  const navigate = useNavigate()
  const { closeSidebar } = useLayout()
  const { tasks, runningCount, unseenCount, markSeen, refresh, removeTask } = useTask()
  const { addToast } = useToast()
  const [open, setOpen] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [clearConfirm, setClearConfirm] = useState(false)
  const [deleting, setDeleting] = useState(false)
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
  // 已结束（完成 / 失败）的记录才可以删除与清空；进行中的任务不动
  const finishedList = list.filter(t => t.status !== 'running')

  const handleDeleteOne = async () => {
    if (!deleteTarget || deleting) return
    setDeleting(true)
    try {
      await deleteRecord(deleteTarget)
      removeTask(deleteTarget.id)
      addToast('记录已删除', 'success')
    } catch (err) {
      addToast(getErrorMessage(err, '删除失败，请重试'), 'error')
    } finally {
      setDeleting(false)
      setDeleteTarget(null)
    }
  }

  const handleClearFinished = async () => {
    if (deleting) return
    setDeleting(true)
    const results = await Promise.allSettled(finishedList.map(deleteRecord))
    let failed = 0
    results.forEach((r, i) => {
      if (r.status === 'fulfilled') removeTask(finishedList[i].id)
      else failed += 1
    })
    if (failed) {
      addToast(`已删除 ${finishedList.length - failed} 条，${failed} 条删除失败，请重试`, 'error')
    } else {
      addToast(`已清空 ${finishedList.length} 条记录`, 'success')
    }
    setDeleting(false)
    setClearConfirm(false)
  }

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
            <div className="flex items-center gap-1">
              {finishedList.length > 0 && (
                <button
                  type="button"
                  onClick={() => setClearConfirm(true)}
                  className="rounded-lg px-2 py-1.5 text-xs text-gray-400 hover:bg-red-50 hover:text-red-600"
                  title="删除所有已完成和已失败的记录（进行中的任务不受影响）"
                >
                  清空已完成
                </button>
              )}
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
                  const running = task.status === 'running'
                  return (
                    <li key={task.id} className="group relative">
                      <div
                        role="button"
                        tabIndex={0}
                        onClick={() => go(task)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault()
                            go(task)
                          }
                        }}
                        className="flex w-full cursor-pointer items-start gap-3 px-4 py-3 text-left hover:bg-gray-50"
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
                      </div>
                      {running ? (
                        <span
                          className="absolute right-14 top-3 rounded-lg p-1.5 text-gray-200 opacity-0 transition-opacity group-hover:opacity-100"
                          title="任务进行中，完成后才能删除"
                          aria-hidden="true"
                        >
                          <Trash2 className="h-4 w-4" />
                        </span>
                      ) : (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            setDeleteTarget(task)
                          }}
                          className="absolute right-14 top-3 rounded-lg p-1.5 text-gray-300 opacity-0 transition-opacity hover:bg-red-50 hover:text-red-500 focus:opacity-100 group-hover:opacity-100"
                          title="删除这条记录"
                          aria-label={`删除记录：${task.title}`}
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </li>
                  )
                })}
              </ul>
            )}
          </div>
        </div>
      )}

      <ConfirmDialog
        isOpen={!!deleteTarget}
        title="删除这条记录"
        message={deleteTarget
          ? `确定删除「${deleteTarget.title}」吗？${deleteTarget.type === 'grader' ? '同步到错题本的对应错题也会一并移除，' : ''}删除后无法恢复。`
          : ''}
        onConfirm={handleDeleteOne}
        onCancel={() => !deleting && setDeleteTarget(null)}
        confirmText={deleting ? '删除中…' : '确认删除'}
        cancelText="再想想"
      />
      <ConfirmDialog
        isOpen={clearConfirm}
        title="清空已完成"
        message={`将删除面板里 ${finishedList.length} 条已完成 / 已失败的记录（进行中的任务不受影响），确定吗？`}
        onConfirm={handleClearFinished}
        onCancel={() => !deleting && setClearConfirm(false)}
        confirmText={deleting ? '清空中…' : '全部删除'}
        cancelText="再想想"
      />
    </div>
  )
}

export default TaskDrawer
