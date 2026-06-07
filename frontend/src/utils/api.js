import axios from 'axios'

const API_BASE_URL = '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

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

  getDatasetList: async () => {
    const response = await api.get('/homework/dataset')
    return response.data
  },

  getDatasetDetail: async (fileId) => {
    const response = await api.get(`/homework/dataset/${fileId}`)
    return response.data
  },

  gradeDataset: async (fileId, options = {}) => {
    const { subject = '数学', assignmentId, submissionId, studentName, classId, homeworkId } = options
    const formData = new FormData()
    formData.append('subject', subject)
    if (assignmentId) formData.append('assignment_id', assignmentId)
    if (submissionId) formData.append('submission_id', submissionId)
    if (studentName) formData.append('student_name', studentName)
    if (classId) formData.append('class_slug', classId)
    if (homeworkId) formData.append('homework_id', homeworkId)
    const response = await api.post(`/grader/upload-dataset/${fileId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  uploadWithContext: async (files, options = {}) => {
    const {
      referenceAnswer,
      subject = '数学',
      assignmentId,
      submissionId,
      studentName,
      onProgress = null,
    } = options
    const formData = new FormData()
    files.forEach(file => formData.append('files', file))
    if (referenceAnswer) formData.append('reference_answer', referenceAnswer)
    formData.append('subject', subject)
    if (assignmentId) formData.append('assignment_id', assignmentId)
    if (submissionId) formData.append('submission_id', submissionId)
    if (studentName) formData.append('student_name', studentName)

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

export default api
