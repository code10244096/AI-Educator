import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { homeworkAPI, jobsAPI } from '../utils/api'
import { useAuth } from './AuthContext'
import { useToast } from '../components/Toast'

/*
 * 后台任务（作业批改 / 教案生成）—— 以服务端 /api/tasks/jobs 为准（R1-006）
 * 不再存浏览器本地：换浏览器、换设备登录同一账号看到同样的任务。
 *
 * useTask() 返回：
 *   tasks            任务列表（最新在前）：{ id, type, title, status: running|completed|failed, progress,
 *                    progressLabel, error, submissionId | planId, score, classId, assignmentId, createdAt }
 *   runningCount     进行中的任务数（顶栏角标）
 *   unseenCount      打开任务抽屉后新完成/失败的任务数
 *   markSeen()       打开抽屉时调用
 *   refresh()        立即刷新
 *   addTask(task)    提交了新任务：先在列表里占位（服务端列表出现后以服务端为准），返回任务 id
 *   removeTask(id)   从列表里隐藏（记录本身的删除走各自接口）
 */

const TaskContext = createContext()

const FAST_POLL = 3000
const IDLE_POLL = 20000
const OPTIMISTIC_TTL = 60000

export const useTask = () => {
  const context = useContext(TaskContext)
  if (!context) {
    throw new Error('useTask must be used within TaskProvider')
  }
  return context
}

// 根据后端的进度文字估算进度百分比
export const estimateProgress = (stage, status) => {
  if (status === 'completed') return 100
  if (!stage) return 5
  const ocr = stage.match(/识别中\s*(\d+)\/(\d+)/)
  if (ocr) {
    const done = Number(ocr[1])
    const total = Number(ocr[2]) || 1
    return Math.round(10 + (done / total) * 50)
  }
  if (stage.includes('批改中')) return 75
  if (stage.includes('检索')) return 15
  if (stage.includes('生成中')) return 50
  if (stage.includes('排队')) return 5
  return 10
}

const RUNNING_STATUSES = ['queued', 'processing', 'pending', 'running']

const normalizeStatus = (status) => {
  if (status === 'failed') return 'failed'
  if (RUNNING_STATUSES.includes(status)) return 'running'
  return 'completed'
}

export const taskKey = (type, id) => `${type === 'grader' ? 'grader' : 'lessonplan'}-${id}`

const fromJob = (job) => {
  const status = normalizeStatus(job.status)
  const isGrader = job.job_type === 'grader'
  const stage = job.progress_stage || (status === 'running' ? (job.status === 'queued' ? '排队中' : '处理中') : status === 'failed' ? '失败' : '已完成')
  return {
    id: taskKey(job.job_type, job.id),
    type: isGrader ? 'grader' : 'lessonplan',
    title: job.title || (isGrader ? '作业批改' : '教案生成'),
    status,
    rawStatus: job.status,
    progress: estimateProgress(job.progress_stage, status === 'completed' ? 'completed' : job.status),
    progressLabel: stage,
    error: status === 'failed' ? (job.error_message || '任务失败，请重试') : undefined,
    submissionId: isGrader ? job.id : undefined,
    planId: isGrader ? undefined : job.id,
    score: job.score,
    classId: job.class_id ?? null,
    assignmentId: job.assignment_id ?? null,
    createdAt: job.created_at,
  }
}

export const TaskProvider = ({ children }) => {
  const { user } = useAuth()
  const { addToast } = useToast()
  const userId = user && !user.must_change_password ? user.id : null

  const [jobs, setJobs] = useState([])
  const [optimistic, setOptimistic] = useState([])
  const [hidden, setHidden] = useState(() => new Set())
  const [unseen, setUnseen] = useState(() => new Set())
  const prevStatus = useRef(new Map())
  const timerRef = useRef(null)
  const loopRef = useRef(null)
  const hasRunningRef = useRef(false)

  // 退出或换账号：清空
  useEffect(() => {
    setJobs([])
    setOptimistic([])
    setHidden(new Set())
    setUnseen(new Set())
    prevStatus.current = new Map()
  }, [userId])

  const notifyFinished = useCallback((task) => {
    setUnseen(prev => new Set(prev).add(task.id))
    if (task.type === 'grader') {
      addToast(task.status === 'failed' ? `批改失败：${task.title}` : `批改完成：${task.title}`, task.status === 'failed' ? 'error' : 'success')
      const dispatch = (classId, homeworkId) => {
        if (classId === null || classId === undefined || !homeworkId) return
        window.dispatchEvent(new CustomEvent('homeworkGraded', { detail: { classId: String(classId), homeworkId } }))
      }
      if (task.classId !== null && task.assignmentId) {
        dispatch(task.classId, task.assignmentId)
        dispatch(`class${task.classId}`, task.assignmentId)
      } else if (task.submissionId) {
        // 旧接口没有 class_id 时查一次批改记录
        homeworkAPI.getResult(task.submissionId)
          .then(data => dispatch(data.class_slug, data.homework_id))
          .catch(() => { /* 记录已删除：无需通知 */ })
      }
    } else {
      addToast(task.status === 'failed' ? `教案生成失败：${task.title}` : `教案已生成：${task.title}`, task.status === 'failed' ? 'error' : 'success')
    }
  }, [addToast])

  const refresh = useCallback(async () => {
    if (!userId) return
    try {
      const items = await jobsAPI.list(20)
      const tasks = items.map(fromJob)
      const seen = prevStatus.current
      const firstLoad = seen.size === 0
      for (const t of tasks) {
        const before = seen.get(t.id)
        if (!firstLoad && before === 'running' && t.status !== 'running') notifyFinished(t)
        seen.set(t.id, t.status)
      }
      setOptimistic(prev => {
        const serverIds = new Set(tasks.map(t => t.id))
        return prev.filter(o => !serverIds.has(o.id) && Date.now() - o.addedAt < OPTIMISTIC_TTL)
      })
      setJobs(tasks)
    } catch {
      // 网络波动：保留上次的数据，下次轮询再试
    }
  }, [userId, notifyFinished])

  // 轮询：有进行中任务时 3 秒一次，否则 20 秒一次；页面隐藏时暂停
  useEffect(() => {
    if (!userId) return undefined
    let stopped = false
    let generation = 0
    // 每次“立即刷新”开启新一轮，旧的一轮在下次检查时自行结束，保证同时只有一条轮询链
    const loop = async (gen) => {
      if (stopped || gen !== generation) return
      if (document.visibilityState !== 'hidden') await refresh()
      if (stopped || gen !== generation) return
      timerRef.current = setTimeout(() => loop(gen), hasRunningRef.current ? FAST_POLL : IDLE_POLL)
    }
    const kick = () => {
      generation += 1
      clearTimeout(timerRef.current)
      loop(generation)
    }
    loopRef.current = kick
    kick()
    const onVisible = () => {
      if (document.visibilityState === 'visible') kick()
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      stopped = true
      loopRef.current = null
      clearTimeout(timerRef.current)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [userId, refresh])

  const tasks = useMemo(() => {
    const serverIds = new Set(jobs.map(t => t.id))
    const pending = optimistic.filter(o => !serverIds.has(o.id))
    return [...pending, ...jobs].filter(t => !hidden.has(t.id))
  }, [jobs, optimistic, hidden])

  const runningCount = tasks.filter(t => t.status === 'running').length
  hasRunningRef.current = runningCount > 0

  const addTask = useCallback((task) => {
    const type = task.type === 'lessonplan' || task.planId ? 'lessonplan' : 'grader'
    const rawId = type === 'grader' ? task.submissionId : task.planId
    const id = rawId !== undefined && rawId !== null ? taskKey(type, rawId) : `local-${Date.now()}`
    setOptimistic(prev => [{
      progress: 0,
      progressLabel: '排队中',
      createdAt: new Date().toISOString(),
      ...task,
      id,
      type,
      status: task.status || 'running',
      addedAt: Date.now(),
    }, ...prev.filter(o => o.id !== id)])
    prevStatus.current.set(id, 'running')
    setHidden(prev => {
      if (!prev.has(id)) return prev
      const next = new Set(prev)
      next.delete(id)
      return next
    })
    hasRunningRef.current = true
    // 稍后立刻刷新一次，并切到快速轮询
    setTimeout(() => loopRef.current?.(), 800)
    return id
  }, [])

  const removeTask = useCallback((id) => {
    setHidden(prev => new Set(prev).add(id))
  }, [])

  // 兼容旧调用：状态以服务端为准，这里只更新占位任务
  const updateTask = useCallback((id, updates) => {
    setOptimistic(prev => prev.map(o => (o.id === id ? { ...o, ...updates } : o)))
  }, [])

  const markSeen = useCallback(() => setUnseen(new Set()), [])

  const value = useMemo(() => ({
    tasks,
    runningCount,
    unseenCount: unseen.size,
    markSeen,
    refresh,
    addTask,
    updateTask,
    removeTask,
  }), [tasks, runningCount, unseen, markSeen, refresh, addTask, updateTask, removeTask])

  return <TaskContext.Provider value={value}>{children}</TaskContext.Provider>
}
