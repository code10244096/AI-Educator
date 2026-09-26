import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react'
import { homeworkAPI, lessonPlanAPI } from '../utils/api'

const TaskContext = createContext()

const POLL_INTERVAL = 3000

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

const saveTasks = (tasks) => {
  try {
    localStorage.setItem('globalTasks', JSON.stringify(tasks))
  } catch (e) {
    console.error('保存任务失败:', e)
  }
}

export const TaskProvider = ({ children }) => {
  const [tasks, setTasks] = useState(() => {
    try {
      const saved = localStorage.getItem('globalTasks')
      return saved ? JSON.parse(saved) : []
    } catch (e) {
      console.error('加载任务失败:', e)
      return []
    }
  })
  const [taskBarExpanded, setTaskBarExpanded] = useState(false)
  const tasksRef = useRef(tasks)
  tasksRef.current = tasks

  const addTask = (task) => {
    const newId = Date.now().toString()
    const newTask = {
      id: newId,
      progress: 0,
      progressLabel: '',
      createdAt: new Date().toISOString(),
      ...task
    }
    setTasks(prev => {
      const updatedTasks = [newTask, ...prev]
      saveTasks(updatedTasks)
      return updatedTasks
    })
    return newId
  }

  const updateTask = useCallback((taskId, updates) => {
    setTasks(prev => {
      const updatedTasks = prev.map(task =>
        task.id === taskId ? { ...task, ...updates } : task
      )
      saveTasks(updatedTasks)
      return updatedTasks
    })
  }, [])

  const removeTask = (taskId) => {
    setTasks(prev => {
      const updatedTasks = prev.filter(task => task.id !== taskId)
      saveTasks(updatedTasks)
      return updatedTasks
    })
  }

  const clearCompleted = () => {
    setTasks(prev => {
      const updatedTasks = prev.filter(task => task.status !== 'completed')
      saveTasks(updatedTasks)
      return updatedTasks
    })
  }

  // 轮询后台任务（作业批改 / 教案生成）的状态，页面切换或刷新后仍会继续
  useEffect(() => {
    let stopped = false
    const poll = async () => {
      const running = tasksRef.current.filter(
        t => t.status === 'running' && (t.submissionId || t.planId)
      )
      for (const task of running) {
        try {
          const data = task.submissionId
            ? await homeworkAPI.getResult(task.submissionId)
            : await lessonPlanAPI.getById(task.planId)
          if (stopped) return
          const status = data.status === 'processing' ? 'running' : data.status === 'failed' ? 'failed' : 'completed'
          const stage = data.progress_stage || (status === 'completed' ? '已完成' : '处理中')
          updateTask(task.id, {
            status,
            progress: estimateProgress(data.progress_stage, data.status),
            progressLabel: stage,
            error: status === 'failed' ? (data.error_message || '任务失败') : undefined,
            ...(task.submissionId && status === 'completed' ? { score: data.score } : {}),
          })
          window.dispatchEvent(new CustomEvent('jobUpdated', { detail: { taskId: task.id, data } }))
          if (task.submissionId && status !== 'running' && data.class_slug && data.homework_id) {
            window.dispatchEvent(new CustomEvent('homeworkGraded', {
              detail: { classId: data.class_slug, homeworkId: data.homework_id },
            }))
          }
        } catch (err) {
          if (err?.response?.status === 404) {
            updateTask(task.id, { status: 'failed', error: '记录已被删除' })
          }
        }
      }
    }
    poll()
    const timer = setInterval(poll, POLL_INTERVAL)
    return () => {
      stopped = true
      clearInterval(timer)
    }
  }, [updateTask])

  return (
    <TaskContext.Provider value={{
      tasks,
      taskBarExpanded,
      setTaskBarExpanded,
      addTask,
      updateTask,
      removeTask,
      clearCompleted
    }}>
      {children}
    </TaskContext.Provider>
  )
}
