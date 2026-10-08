import axios from 'axios'

const API_BASE_URL = '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 登录失效 / 需先改初始密码时的全局处理（由 AuthContext 注册）
let authHandlers = { onUnauthorized: null, onMustChangePassword: null }
export const setAuthHandlers = (handlers) => {
  authHandlers = { ...authHandlers, ...handlers }
}

export const MSG_SESSION_EXPIRED = '登录已过期，请重新登录'
export const MSG_MUST_CHANGE_PASSWORD = '请先修改初始密码'

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status
    const url = error?.config?.url || ''
    const detail = error?.response?.data?.detail
    const method = (error?.config?.method || 'get').toLowerCase()
    // 只有登录、退出和启动时的 GET /auth/me 自己处理 401；PUT /auth/me（保存资料）失效时同样跳登录页
    const isAuthCall = url.startsWith('/auth/login') || url.startsWith('/auth/logout') ||
      url.startsWith('/auth/enter') ||
      (url.startsWith('/auth/me') && method === 'get')
    if (status === 401 && !isAuthCall) {
      authHandlers.onUnauthorized?.(MSG_SESSION_EXPIRED)
    } else if (status === 403 && detail === MSG_MUST_CHANGE_PASSWORD) {
      authHandlers.onMustChangePassword?.()
    }
    return Promise.reject(error)
  },
)

// 账号 API
export const authAPI = {
  login: async (username, password) => {
    const response = await api.post('/auth/login', { username, password })
    return response.data
  },

  // 公测：没有会话时由服务端发放体验账号；未开启公测时返回 401
  enter: async () => {
    const response = await api.post('/auth/enter')
    return response.data
  },

  logout: async () => {
    const response = await api.post('/auth/logout')
    return response.data
  },

  me: async () => {
    const response = await api.get('/auth/me')
    return response.data
  },

  updateProfile: async (data) => {
    const response = await api.put('/auth/me', data)
    return response.data
  },

  changePassword: async (oldPassword, newPassword) => {
    const response = await api.post('/auth/change-password', {
      old_password: oldPassword,
      new_password: newPassword,
    })
    return response.data
  },
}

// 作业批改 API
export const homeworkAPI = {
  upload: async (files, referenceAnswer, subject = '数学', onProgress = null) => {
    const formData = new FormData()
    files.forEach(file => {
      formData.append('files', file)
    })
    if (referenceAnswer) {
      formData.append('reference_answer', referenceAnswer)
    }
    formData.append('subject', subject)
    
    const response = await api.post('/grader/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(percentCompleted)
        }
      },
    })
    return response.data
  },
  
  getResult: async (submissionId) => {
    const response = await api.get(`/grader/${submissionId}`)
    return response.data
  },

  uploadWithContext: async (files, options = {}) => {
    const {
      referenceAnswer,
      subject = '数学',
      assignmentId,
      submissionId,
      studentName,
      memberId,
      onProgress = null,
    } = options
    const formData = new FormData()
    files.forEach(file => formData.append('files', file))
    if (referenceAnswer) formData.append('reference_answer', referenceAnswer)
    formData.append('subject', subject)
    if (assignmentId) formData.append('assignment_id', assignmentId)
    if (submissionId) formData.append('submission_id', submissionId)
    if (studentName) formData.append('student_name', studentName)
    if (memberId) formData.append('member_id', memberId)

    const response = await api.post('/grader/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(percentCompleted)
        }
      },
    })
    return response.data
  },

  // 批改记录（后台任务）
  listSubmissions: async (params = {}) => {
    const response = await api.get('/grader/submissions', { params })
    return response.data
  },

  retry: async (submissionId) => {
    const response = await api.post(`/grader/${submissionId}/retry`)
    return response.data
  },

  deleteSubmission: async (submissionId) => {
    const response = await api.delete(`/grader/${submissionId}`)
    return response.data
  },

  markReviewed: async (submissionId) => {
    const response = await api.post(`/grader/${submissionId}/review`, { review_status: 'reviewed' })
    return response.data
  },

  fileUrl: (submissionId, index) => `${API_BASE_URL}/grader/${submissionId}/files/${index}`,
}

// 提取后端返回的中文错误信息
export const getErrorMessage = (error, fallback = '操作失败，请重试') => {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg
  // 没有后端 detail 时不显示 “Network Error / Request failed with status code 500” 这类英文
  if (error?.isAxiosError) {
    if (!error.response) return error.code === 'ECONNABORTED' ? '服务器响应超时，请稍后重试' : '无法连接服务器，请检查网络后重试'
    if (error.response.status >= 500) return '服务器出了点问题，请稍后重试'
    return fallback
  }
  return error?.message || fallback
}

// 错题本 API
export const notebookAPI = {
  upload: async (file, knowledgePoint, subject = '数学') => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('knowledge_point', knowledgePoint)
    formData.append('subject', subject)
    
    const response = await api.post('/notebook/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },
  
  getList: async (params = {}) => {
    const response = await api.get('/notebook/list', { params })
    return response.data
  },
  
  markMastered: async (questionId) => {
    const response = await api.post(`/notebook/${questionId}/mastered`)
    return response.data
  },

  markUnmastered: async (questionId) => {
    const response = await api.post(`/notebook/${questionId}/unmastered`)
    return response.data
  },

  getStats: async (params = {}) => {
    const response = await api.get('/notebook/stats', { params })
    return response.data
  },

  generateVariants: async (questionId, count = 3) => {
    const formData = new FormData()
    formData.append('count', count)
    const response = await api.post(`/notebook/${questionId}/variants`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  remove: async (questionId) => {
    const response = await api.delete(`/notebook/${questionId}`)
    return response.data
  },
}

// 教案生成 API
export const lessonPlanAPI = {
  generate: async (title, period, studentLevel, requirements) => {
    const formData = new FormData()
    formData.append('title', title)
    formData.append('period', period)
    formData.append('student_level', studentLevel)
    formData.append('requirements', requirements)
    
    const response = await api.post('/lessonplan/generate', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },
  
  getById: async (planId) => {
    const response = await api.get(`/lessonplan/${planId}`)
    return response.data
  },

  list: async (params = {}) => {
    const response = await api.get('/lessonplan/list', { params })
    return response.data
  },

  update: async (planId, data) => {
    const response = await api.put(`/lessonplan/${planId}`, data)
    return response.data
  },

  remove: async (planId) => {
    const response = await api.delete(`/lessonplan/${planId}`)
    return response.data
  },

  regenerate: async (planId) => {
    const response = await api.post(`/lessonplan/${planId}/regenerate`)
    return response.data
  },

  exportUrl: (planId, format = 'md') => `${API_BASE_URL}/lessonplan/${planId}/export?format=${format}`,
}

// 班级统计 API
export const classAPI = {
  getList: async () => {
    const response = await api.get('/class/list')
    return response.data
  },

  getStats: async (classSlug = null) => {
    const response = await api.get('/class/stats', {
      params: classSlug ? { class_slug: classSlug } : {},
    })
    return response.data
  },

  getDetail: async (classSlug) => {
    const response = await api.get(`/class/${classSlug}`)
    return response.data
  },

  create: async (data) => {
    const response = await api.post('/class', data)
    return response.data
  },

  update: async (classSlug, data) => {
    const response = await api.put(`/class/${classSlug}`, data)
    return response.data
  },

  remove: async (classSlug) => {
    const response = await api.delete(`/class/${classSlug}`)
    return response.data
  },

  getMembers: async (classSlug) => {
    const response = await api.get(`/class/${classSlug}/members`)
    return response.data
  },

  addMember: async (classSlug, data) => {
    const response = await api.post(`/class/${classSlug}/members`, data)
    return response.data
  },

  importMembers: async (classSlug, { text, file } = {}) => {
    const formData = new FormData()
    if (text) formData.append('text', text)
    if (file) formData.append('file', file)
    const response = await api.post(`/class/${classSlug}/members/import`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  updateMember: async (classSlug, memberId, data) => {
    const response = await api.put(`/class/${classSlug}/members/${memberId}`, data)
    return response.data
  },

  removeMember: async (classSlug, memberId) => {
    const response = await api.delete(`/class/${classSlug}/members/${memberId}`)
    return response.data
  },

  getScoreArchive: async (classSlug) => {
    const response = await api.get(`/class/${classSlug}/score-archive`)
    return response.data
  },
}

// 班级作业 API
export const classHomeworkAPI = {
  getHomeworkList: async (classSlug) => {
    const response = await api.get(`/class/${classSlug}/homework`)
    return response.data
  },

  getHomeworkDetail: async (classSlug, homeworkId) => {
    const response = await api.get(`/class/${classSlug}/homework/${homeworkId}`)
    return response.data
  },

  getSubmissions: async (classSlug, homeworkId) => {
    const response = await api.get(`/class/${classSlug}/homework/${homeworkId}/submissions`)
    return response.data
  },

  getHomeworkStats: async (classSlug) => {
    const response = await api.get(`/class/${classSlug}/homework-stats`)
    return response.data
  },

  getGradingTasks: async (classSlug) => {
    const response = await api.get(`/class/${classSlug}/grading-tasks`)
    return response.data
  },

  getAlertStudents: async (classSlug) => {
    const response = await api.get(`/class/${classSlug}/alert-students`)
    return response.data
  },

  getAllTasks: async () => {
    const response = await api.get('/tasks/all')
    return response.data
  },

  createHomework: async (classSlug, data) => {
    const response = await api.post(`/class/${classSlug}/homework`, data)
    return response.data
  },

  updateHomework: async (classSlug, homeworkId, data) => {
    const response = await api.put(`/class/${classSlug}/homework/${homeworkId}`, data)
    return response.data
  },

  deleteHomework: async (classSlug, homeworkId) => {
    const response = await api.delete(`/class/${classSlug}/homework/${homeworkId}`)
    return response.data
  },

  getAnalysis: async (classSlug, homeworkId) => {
    const response = await api.get(`/class/${classSlug}/homework/${homeworkId}/analysis`)
    return response.data
  },
}

export const questionBankAPI = {
  getList: async (params = {}) => {
    const response = await api.get('/questionbank/list', { params })
    return response.data
  },
  
  getById: async (questionId) => {
    const response = await api.get(`/questionbank/${questionId}`)
    return response.data
  },
  
  search: async (keyword, subject, educationLevel, limit = 10) => {
    const formData = new FormData()
    formData.append('keyword', keyword)
    if (subject) formData.append('subject', subject)
    if (educationLevel) formData.append('education_level', educationLevel)
    formData.append('limit', limit)
    
    const response = await api.post('/questionbank/search', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },
  
  getStats: async () => {
    const response = await api.get('/questionbank/stats')
    return response.data
  },
}

// 模型用量统计 API
export const usageAPI = {
  getSummary: async (params = {}) => {
    const response = await api.get('/usage/summary', { params })
    return response.data
  },

  getCalls: async (params = {}) => {
    const response = await api.get('/usage/calls', { params })
    return response.data
  },
}

// 工作台汇总（R1-006）
export const dashboardAPI = {
  get: async () => {
    const response = await api.get('/dashboard')
    return response.data
  },
}

// 后台任务（顶栏任务抽屉，服务端数据，按教师过滤）
export const jobsAPI = {
  list: async (limit = 20) => {
    const response = await api.get('/tasks/jobs', { params: { limit } })
    return response.data?.items || []
  },
}

export default api
