import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { classAPI } from '../utils/api'

const ClassContext = createContext()

export const useClass = () => {
  const context = useContext(ClassContext)
  if (!context) {
    throw new Error('useClass must be used within ClassProvider')
  }
  return context
}

const normalize = (c) => ({
  id: c.id,
  name: c.name,
  students: c.students,
  subject: c.subject,
  grade: c.grade,
  slug: c.slug || `class${c.id}`,
  homeworkCount: c.homework_count,
})

export const ClassProvider = ({ children }) => {
  const [classes, setClasses] = useState([])
  const [loaded, setLoaded] = useState(false)
  const [loadError, setLoadError] = useState(null)

  const reloadClasses = useCallback(async () => {
    try {
      const data = await classAPI.getList()
      setClasses((data.items || []).map(normalize))
      setLoadError(null)
    } catch (e) {
      setLoadError('班级列表加载失败')
    } finally {
      setLoaded(true)
    }
  }, [])

  useEffect(() => {
    reloadClasses()
    const onChanged = () => reloadClasses()
    window.addEventListener('classesChanged', onChanged)
    return () => window.removeEventListener('classesChanged', onChanged)
  }, [reloadClasses])

  // 以下方法都会写入后端，失败时抛出异常由调用方提示
  const addClass = async (newClass) => {
    const created = await classAPI.create({
      name: newClass.name,
      subject: newClass.subject,
      grade: newClass.grade,
    })
    await reloadClasses()
    return normalize(created)
  }

  const updateClass = async (id, updates) => {
    const cls = classes.find(c => c.id === id)
    const slug = cls?.slug || `class${id}`
    const updated = await classAPI.update(slug, {
      name: updates.name,
      subject: updates.subject,
      grade: updates.grade,
    })
    await reloadClasses()
    return normalize(updated)
  }

  const deleteClass = async (id) => {
    const cls = classes.find(c => c.id === id)
    await classAPI.remove(cls?.slug || `class${id}`)
    await reloadClasses()
  }

  const getClassBySlug = (slug) => classes.find(c => c.slug === slug || `class${c.id}` === slug)

  return (
    <ClassContext.Provider value={{
      classes, loaded, loadError, addClass, updateClass, deleteClass, reloadClasses, getClassBySlug,
    }}>
      {children}
    </ClassContext.Provider>
  )
}
