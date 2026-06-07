import { classHomeworkAPI } from '../utils/api'

const cache = {}

export async function fetchHomeworkList(classId) {
  const data = await classHomeworkAPI.getHomeworkList(classId)
  cache[`list-${classId}`] = data.items || []
  return cache[`list-${classId}`]
}

export async function fetchHomeworkById(classId, homeworkId) {
  const data = await classHomeworkAPI.getHomeworkDetail(classId, homeworkId)
  cache[`hw-${classId}-${homeworkId}`] = data
  return data
}

export async function fetchStudentSubmissions(classId, homeworkId) {
  const data = await classHomeworkAPI.getSubmissions(classId, homeworkId)
  cache[`subs-${classId}-${homeworkId}`] = data.items || []
  return cache[`subs-${classId}-${homeworkId}`]
}

export async function fetchHomeworkStats(classId) {
  return classHomeworkAPI.getHomeworkStats(classId)
}

export async function fetchGradingTasks(classId) {
  const data = await classHomeworkAPI.getGradingTasks(classId)
  return data.items || []
}

export async function fetchAlertStudents(classId) {
  const data = await classHomeworkAPI.getAlertStudents(classId)
  return data.items || []
}

export async function fetchAllGradingTasks() {
  const data = await classHomeworkAPI.getAllTasks()
  return data.items || []
}

export function clearHomeworkCache(classId, homeworkId) {
  delete cache[`list-${classId}`]
  delete cache[`hw-${classId}-${homeworkId}`]
  delete cache[`subs-${classId}-${homeworkId}`]
}
