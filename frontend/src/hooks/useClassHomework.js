import { useState, useEffect, useCallback } from 'react'
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

  const reload = useCallback(() => {
    if (!classId || !homeworkId) return
    setLoading(true)
    Promise.all([
      fetchHomeworkById(classId, homeworkId),
      fetchStudentSubmissions(classId, homeworkId),
    ])
      .then(([hw, subs]) => {
        setHomework(hw)
        setStudents(subs)
      })
      .catch(err => setError(err.message || '加载失败'))
      .finally(() => setLoading(false))
  }, [classId, homeworkId])

  useEffect(() => { reload() }, [reload])

  const invalidate = useCallback(() => {
    clearHomeworkCache(classId, homeworkId)
    reload()
  }, [classId, homeworkId, reload])

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
