import React, { createContext, useContext, useState } from 'react'

const ClassContext = createContext()

export const useClass = () => {
  const context = useContext(ClassContext)
  if (!context) {
    throw new Error('useClass must be used within ClassProvider')
  }
  return context
}

export const ClassProvider = ({ children }) => {
  const [classes, setClasses] = useState([
    { id: 1, name: '高三(1)班', students: 45, subject: '数学', grade: '高三' },
    { id: 2, name: '高三(2)班', students: 42, subject: '数学', grade: '高三' },
    { id: 3, name: '高三(3)班', students: 40, subject: '数学', grade: '高三' },
  ])

  const addClass = (newClass) => {
    const newId = classes.length > 0 ? Math.max(...classes.map(c => c.id)) + 1 : 1
    setClasses(prev => [...prev, { ...newClass, id: newId }])
  }

  const updateClass = (id, updates) => {
    setClasses(prev => prev.map(c => c.id === id ? { ...c, ...updates } : c))
  }

  const deleteClass = (id) => {
    setClasses(prev => prev.filter(c => c.id !== id))
  }

  return (
    <ClassContext.Provider value={{ classes, addClass, updateClass, deleteClass }}>
      {children}
    </ClassContext.Provider>
  )
}
