import React, { createContext, useContext, useState, useEffect } from 'react'
import { classAPI } from '../utils/api'

const ClassContext = createContext()

const DEFAULT_CLASSES = [
  { id: 1, name: '高三(1)班', students: 45, subject: '数学', grade: '高三', slug: 'class1' },
  { id: 2, name: '高三(2)班', students: 42, subject: '数学', grade: '高三', slug: 'class2' },
  { id: 3, name: '高三(3)班', students: 40, subject: '数学', grade: '高三', slug: 'class3' },
]

export const useClass = () => {
  const context = useContext(ClassContext)
  if (!context) {
    throw new Error('useClass must be used within ClassProvider')
  }
  return context
}

export const ClassProvider = ({ children }) => {
  const [classes, setClasses] = useState(DEFAULT_CLASSES)

  useEffect(() => {
    classAPI.getList()
      .then(data => {
        if (data.items?.length) {
          setClasses(data.items.map(c => ({
            id: c.id,
            name: c.name,
            students: c.students,
            subject: c.subject,
            grade: c.grade,
            slug: c.slug,
          })))
        }
      })
      .catch(() => {})
  }, [])

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
