import React, { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTask } from '../context/TaskContext'
import { useClass } from '../context/ClassContext'
import TaskBar from './TaskBar'
import { fetchAllGradingTasks } from '../services/homeworkService'

const GlobalTaskBar = () => {
  const navigate = useNavigate()
  const { tasks, taskBarExpanded, setTaskBarExpanded, removeTask } = useTask()
  const { classes } = useClass()
  const [classTasks, setClassTasks] = React.useState([])

  const refreshClassTasks = React.useCallback(() => {
    fetchAllGradingTasks().then(setClassTasks).catch(() => setClassTasks([]))
  }, [])

  React.useEffect(() => {
    refreshClassTasks()
    const interval = setInterval(refreshClassTasks, 30000)
    const onGraded = () => refreshClassTasks()
    window.addEventListener('homeworkGraded', onGraded)
    return () => {
      clearInterval(interval)
      window.removeEventListener('homeworkGraded', onGraded)
    }
  }, [classes, refreshClassTasks])

  const allTasks = useMemo(() => {
    const merged = [...classTasks.filter(t => t.status === 'pending' || t.status === 'running'), ...tasks]
    const seen = new Set()
    return merged.filter(t => {
      if (seen.has(t.id)) return false
      seen.add(t.id)
      return t.status === 'running' || t.status === 'pending' || t.status === 'completed'
    }).slice(0, 20)
  }, [classTasks, tasks])

  const handleViewTask = (task) => {
    if (task.type === 'homework-grading') {
      navigate(`/class/${task.classId}/homework/${task.homeworkId}`)
    } else if (task.type === 'grader') {
      window.dispatchEvent(new CustomEvent('viewTask', { detail: task }))
      navigate('/grader')
    } else if (task.type === 'lessonplan') {
      window.dispatchEvent(new CustomEvent('viewTask', { detail: task }))
      navigate('/lessonplan')
    } else {
      navigate('/tasks')
    }
    setTaskBarExpanded(false)
  }

  const handleRemoveTask = (id) => {
    if (String(id).startsWith('hw-')) return
    removeTask(id)
  }

  return (
    <TaskBar
      tasks={allTasks}
      onRemoveTask={handleRemoveTask}
      onViewTask={handleViewTask}
      expanded={taskBarExpanded}
      onToggle={() => setTaskBarExpanded(!taskBarExpanded)}
    />
  )
}

export default GlobalTaskBar
