import { useState, useEffect, useCallback } from 'react'
import { useClass } from '../context/ClassContext'
import { classAPI } from '../utils/api'
import {
  fetchHomeworkList,
  fetchHomeworkById,
  fetchStudentSubmissions,
  fetchHomeworkStats,
  fetchGradingTasks,
  fetchAlertStudents,
  clearHomeworkCache,
} from '../services/homeworkService'

export function useHomeworkList(classId) {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const reload = useCallback(() => {
    if (!classId) return
    setLoading(true)
    fetchHomeworkList(classId)
      .then(setData)
      .catch(err => setError(err.message || '加载失败'))
      .finally(() => setLoading(false))
  }, [classId])

  useEffect(() => { reload() }, [reload])

  return { data, loading, error, reload }
}

export function useHomeworkDetail(classId, homeworkId) {
  const [homework, setHomework] = useState(null)
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const reload = useCallback((silent = false) => {
    if (!classId || !homeworkId) return
    if (silent !== true) setLoading(true)
    Promise.all([
      fetchHomeworkById(classId, homeworkId),
      fetchStudentSubmissions(classId, homeworkId),
    ])
      .then(([hw, subs]) => {
        setHomework(hw)
        setStudents(subs)
        setError(null)
      })
      .catch(err => {
        // 静默刷新失败时保留已有数据，不打断老师操作
        if (silent !== true) setError(err)
      })
      .finally(() => setLoading(false))
  }, [classId, homeworkId])

  useEffect(() => { reload() }, [reload])

  const invalidate = useCallback(() => {
    clearHomeworkCache(classId, homeworkId)
    reload(true)
  }, [classId, homeworkId, reload])

  // 有学生作业正在后台批改时，定时静默刷新
  const hasProcessing = students.some(s => s.status === 'processing' || s.status === 'queued')
  useEffect(() => {
    if (!hasProcessing) return
    const timer = setInterval(() => reload(true), 4000)
    return () => clearInterval(timer)
  }, [hasProcessing, reload])

  useEffect(() => {
    const onGraded = (e) => {
      const d = e.detail
      if (d?.classId === classId && String(d?.homeworkId) === String(homeworkId)) {
        invalidate()
      }
    }
    window.addEventListener('homeworkGraded', onGraded)
    return () => window.removeEventListener('homeworkGraded', onGraded)
  }, [classId, homeworkId, invalidate])

  return { homework, students, loading, error, reload, invalidate }
}

export function useHomeworkBoard(classId) {
  const [stats, setStats] = useState(null)
  const [homeworkList, setHomeworkList] = useState([])
  const [gradingTasks, setGradingTasks] = useState([])
  const [alertStudents, setAlertStudents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const reload = useCallback(() => {
    if (!classId) return
    setLoading(true)
    Promise.all([
      fetchHomeworkStats(classId),
      fetchHomeworkList(classId),
      fetchGradingTasks(classId),
      fetchAlertStudents(classId),
    ])
      .then(([s, list, tasks, alerts]) => {
        setStats(s)
        setHomeworkList(list)
        setGradingTasks(tasks)
        setAlertStudents(alerts)
      })
      .catch(err => setError(err.message || '加载失败'))
      .finally(() => setLoading(false))
  }, [classId])

  useEffect(() => { reload() }, [reload])

  useEffect(() => {
    const onGraded = (e) => {
      if (e.detail?.classId === classId) reload()
    }
    window.addEventListener('homeworkGraded', onGraded)
    return () => window.removeEventListener('homeworkGraded', onGraded)
  }, [classId, reload])

  return { stats, homeworkList, gradingTasks, alertStudents, loading, error, reload }
}

// 班级基本信息：优先用全局班级列表，没有时向后端单独查询
export const useClassInfo = (classId) => {
  const { getClassBySlug, loaded } = useClass()
  const fromContext = getClassBySlug(classId)
  const [detail, setDetail] = useState(null)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    if (fromContext || !classId) return
    setNotFound(false)
    classAPI.getDetail(classId)
      .then(d => { setDetail(d); setNotFound(false) })
      .catch(() => setNotFound(true))
  }, [classId, fromContext])

  const info = fromContext || detail
  return {
    info: info || { name: '', subject: '', students: 0 },
    loading: !info && !notFound,
    notFound: !fromContext && notFound && loaded,
  }
}
