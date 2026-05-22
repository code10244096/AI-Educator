import React, { createContext, useContext, useState, useEffect } from 'react'

const TaskContext = createContext()

export const useTask = () => {
  const context = useContext(TaskContext)
  if (!context) {
    throw new Error('useTask must be used within TaskProvider')
  }
  return context
}

export const TaskProvider = ({ children }) => {
  const [tasks, setTasks] = useState([])
  const [taskBarExpanded, setTaskBarExpanded] = useState(false)
  
  useEffect(() => {
    const savedTasks = localStorage.getItem('globalTasks')
    if (savedTasks) {
      try {
        const parsedTasks = JSON.parse(savedTasks)
        setTasks(parsedTasks)
      } catch (e) {
        console.error('加载任务失败:', e)
      }
    }
  }, [])
  
  const addTask = (task) => {
    const newTask = {
      id: Date.now().toString(),
      progress: 0,
      progressLabel: '',
      createdAt: new Date().toISOString(),
      ...task
    }
    const updatedTasks = [newTask, ...tasks]
    setTasks(updatedTasks)
    localStorage.setItem('globalTasks', JSON.stringify(updatedTasks))
    return newTask.id
  }
  
  const updateTask = (taskId, updates) => {
    const updatedTasks = tasks.map(task => 
      task.id === taskId ? { ...task, ...updates } : task
    )
    setTasks(updatedTasks)
    localStorage.setItem('globalTasks', JSON.stringify(updatedTasks))
  }
  
  const removeTask = (taskId) => {
    const updatedTasks = tasks.filter(task => task.id !== taskId)
    setTasks(updatedTasks)
    localStorage.setItem('globalTasks', JSON.stringify(updatedTasks))
  }
  
  const clearCompleted = () => {
    const updatedTasks = tasks.filter(task => task.status !== 'completed')
    setTasks(updatedTasks)
    localStorage.setItem('globalTasks', JSON.stringify(updatedTasks))
  }
  
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
