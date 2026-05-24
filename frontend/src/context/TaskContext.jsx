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
      localStorage.setItem('globalTasks', JSON.stringify(updatedTasks))
      return updatedTasks
    })
    return newId
  }
  
  const updateTask = (taskId, updates) => {
    setTasks(prev => {
      const updatedTasks = prev.map(task => 
        task.id === taskId ? { ...task, ...updates } : task
      )
      localStorage.setItem('globalTasks', JSON.stringify(updatedTasks))
      return updatedTasks
    })
  }
  
  const removeTask = (taskId) => {
    setTasks(prev => {
      const updatedTasks = prev.filter(task => task.id !== taskId)
      localStorage.setItem('globalTasks', JSON.stringify(updatedTasks))
      return updatedTasks
    })
  }
  
  const clearCompleted = () => {
    setTasks(prev => {
      const updatedTasks = prev.filter(task => task.status !== 'completed')
      localStorage.setItem('globalTasks', JSON.stringify(updatedTasks))
      return updatedTasks
    })
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
