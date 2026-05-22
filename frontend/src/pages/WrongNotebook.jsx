import React, { useState, useEffect } from 'react'
import { Plus, Filter, Calendar, CheckCircle, ExternalLink, BookOpen, FileText, FileSpreadsheet, File, AlertCircle } from 'lucide-react'
import { notebookAPI } from '../utils/api'
import ReactMarkdown from 'react-markdown'
import PageBackground from '../components/PageBackground'

const SUPPORTED_FORMATS = {
  'image/*': ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'],
  'application/pdf': ['pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['docx'],
  'application/msword': ['doc'],
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['xlsx'],
  'application/vnd.ms-excel': ['xls'],
  'text/markdown': ['md'],
  'text/plain': ['txt'],
}

const FILE_TYPE_ICONS = {
  image: FileText,
  pdf: FileText,
  word: FileText,
  excel: FileSpreadsheet,
  text: File,
}

const FILE_TYPE_LABELS = {
  image: '图片',
  pdf: 'PDF',
  word: 'Word',
  excel: 'Excel',
  text: '文本',
}

const ERROR_MESSAGES = {
  empty: '哎呀，这个文件好像有点"害羞"，什么都没解析出来呢~ 换个文件试试看？',
  invalid_format: '这个文件格式我不太认识呢，试试图片、PDF、Word、Excel 或 TXT 文件吧~',
  parse_failed: '解析遇到了一点小麻烦，可能是文件内容不太清晰，重新上传试试？',
  no_questions: '翻遍了整个文件，也没找到错题的踪迹~ 确认一下文件里有没有题目内容哦',
  general: '出了点小状况，稍后再试一次吧~',
}

const WrongNotebook = () => {
  const [questions, setQuestions] = useState([])
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState({ knowledgePoint: '', subject: '数学' })
  const [isVisible, setIsVisible] = useState(false)
  const [parseError, setParseError] = useState(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadedFileName, setUploadedFileName] = useState('')
  
  useEffect(() => {
    setIsVisible(true)
  }, [])
  
  const getFileType = (file) => {
    const ext = file.name.split('.').pop().toLowerCase()
    if (['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'].includes(ext)) return 'image'
    if (ext === 'pdf') return 'pdf'
    if (['doc', 'docx'].includes(ext)) return 'word'
    if (['xls', 'xlsx'].includes(ext)) return 'excel'
    if (['md', 'txt'].includes(ext)) return 'text'
    return 'unknown'
  }
  
  const handleUpload = async (event) => {
    const file = event.target.files[0]
    if (!file) return
    
    const fileType = getFileType(file)
    
    if (fileType === 'unknown') {
      setParseError({ type: 'invalid_format', message: ERROR_MESSAGES.invalid_format })
      return
    }
    
    setLoading(true)
    setParseError(null)
    setUploadProgress(0)
    setUploadedFileName(file.name)
    
    const progressInterval = setInterval(() => {
      setUploadProgress(prev => {
        if (prev >= 90) {
          clearInterval(progressInterval)
          return 90
        }
        return prev + 10
      })
    }, 200)
    
    try {
      const response = await notebookAPI.upload(
        file,
        filter.knowledgePoint || '未分类',
        filter.subject
      )
      
      clearInterval(progressInterval)
      setUploadProgress(100)
      
      if (response && response.questions && response.questions.length > 0) {
        setQuestions(prev => [...response.questions, ...prev])
        setUploadedFileName('')
      } else if (response && response.error) {
        setParseError({ type: response.error_type || 'general', message: response.error || ERROR_MESSAGES.general })
      } else {
        setParseError({ type: 'no_questions', message: ERROR_MESSAGES.no_questions })
      }
    } catch (error) {
      console.error('录入失败:', error)
      clearInterval(progressInterval)
      setParseError({ type: 'parse_failed', message: ERROR_MESSAGES.parse_failed })
    } finally {
      setLoading(false)
    }
  }
  
  const handleMarkMastered = async (id) => {
    try {
      await notebookAPI.markMastered(id)
      setQuestions(prev =>
        prev.map(q => (q.id === id ? { ...q, is_mastered: true } : q))
      )
    } catch (error) {
      console.error('标记失败:', error)
    }
  }
  
  return (
    <PageBackground gradient="notebook">
      <div className={`max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 pb-12 transition-all duration-1000 ${
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-12'
      }`}>
        <div className="bg-white/90 backdrop-blur-md rounded-2xl shadow-xl p-8 border border-white/20">
          <div className="flex items-center space-x-3 mb-6">
            <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-emerald-500 rounded-xl flex items-center justify-center shadow-lg">
              <BookOpen className="h-6 w-6 text-white" />
            </div>
            <div>
              <h2 className="text-3xl font-bold bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
                AI 错题本管家
              </h2>
              <p className="text-sm text-gray-600">智能整理，变式练习，举一反三</p>
            </div>
          </div>
          
          <div className="flex flex-wrap gap-3 mb-6">
            <label className="flex items-center space-x-2 bg-gradient-to-r from-green-500 to-emerald-500 text-white px-5 py-2.5 rounded-xl cursor-pointer hover:from-green-600 hover:to-emerald-600 shadow-md hover:shadow-lg transition-all duration-300 hover:scale-[1.02]">
              <Plus className="h-5 w-5" />
              <span className="font-medium">录入错题</span>
              <input
                type="file"
                accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.md,.txt"
                onChange={handleUpload}
                className="hidden"
                id="upload-wrong"
              />
            </label>
            
            <select
              value={filter.knowledgePoint}
              onChange={(e) => setFilter(prev => ({ ...prev, knowledgePoint: e.target.value }))}
              className="border border-gray-300 rounded-xl px-4 py-2.5 bg-white hover:border-green-400 focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all cursor-pointer"
            >
              <option value="">按知识点筛选</option>
              <option value="三角函数">三角函数</option>
              <option value="导数">导数</option>
              <option value="函数">函数</option>
            </select>
            
            <select
              value={filter.subject}
              onChange={(e) => setFilter(prev => ({ ...prev, subject: e.target.value }))}
              className="border border-gray-300 rounded-xl px-4 py-2.5 bg-white hover:border-green-400 focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all cursor-pointer"
            >
              <option value="数学">数学</option>
              <option value="物理">物理</option>
              <option value="化学">化学</option>
            </select>
          </div>
        
        {loading && (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <BookOpen className="h-8 w-8 text-green-500 animate-pulse" />
            </div>
            <p className="text-gray-600 font-medium">正在录入错题...</p>
            {uploadedFileName && (
              <p className="text-sm text-gray-500 mt-2">正在解析：{uploadedFileName}</p>
            )}
            <div className="mt-4 max-w-xs mx-auto">
              <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-green-500 to-emerald-500 h-full rounded-full transition-all duration-300 ease-out"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          </div>
        )}
        
        {parseError && !loading && (
          <div className="mb-6 p-6 bg-gradient-to-r from-amber-50 to-orange-50 rounded-xl border border-amber-200 text-center">
            <div className="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <AlertCircle className="h-8 w-8 text-amber-500" />
            </div>
            <p className="text-amber-800 font-medium text-lg">{parseError.message}</p>
            <p className="text-amber-600 text-sm mt-2">支持格式：图片、PDF、Word、Excel、Markdown、TXT</p>
          </div>
        )}
        
        <div className="space-y-4">
          {questions.map((q) => (
            <div
              key={q.id}
              className={`border rounded-xl p-5 transition-all duration-300 hover:shadow-md ${
                q.is_mastered ? 'border-green-200 bg-gradient-to-r from-green-50 to-emerald-50' : 'border-gray-200 bg-white hover:border-green-300'
              }`}
            >
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center space-x-2">
                  <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
                    <Calendar className="h-4 w-4 text-green-600" />
                  </div>
                  <span className="text-sm text-gray-600">
                    {new Date(q.error_date).toLocaleDateString('zh-CN')}
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
                    {q.knowledge_point}
                  </span>
                  <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-xs font-medium">
                    {q.subject}
                  </span>
                </div>
              </div>
              
              <div className="mb-4 bg-gray-50 rounded-xl p-4">
                <p className="text-sm font-medium text-gray-600 mb-2 flex items-center">
                  <span className="w-1.5 h-1.5 bg-green-500 rounded-full mr-2"></span>
                  原题
                </p>
                <p className="text-gray-900 leading-relaxed">{q.question_text}</p>
              </div>
              
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="bg-red-50 rounded-xl p-4 border border-red-100">
                  <p className="text-sm font-medium text-red-600 mb-1 flex items-center">
                    <span className="w-1.5 h-1.5 bg-red-500 rounded-full mr-2"></span>
                    我的答案
                  </p>
                  <p className="text-red-700">{q.user_answer || '未作答'}</p>
                </div>
                <div className="bg-green-50 rounded-xl p-4 border border-green-100">
                  <p className="text-sm font-medium text-green-600 mb-1 flex items-center">
                    <span className="w-1.5 h-1.5 bg-green-500 rounded-full mr-2"></span>
                    正确答案
                  </p>
                  <p className="text-green-700">{q.correct_answer}</p>
                </div>
              </div>
              
              {q.variant_questions && q.variant_questions.length > 0 && (
                <div className="mb-4">
                  <p className="text-sm font-medium text-gray-700 mb-3 flex items-center">
                    <span className="w-1.5 h-1.5 bg-blue-500 rounded-full mr-2"></span>
                    变式练习
                  </p>
                  <div className="space-y-3">
                    {q.variant_questions.map((v, idx) => (
                      <div key={idx} className="bg-gradient-to-r from-blue-50 to-cyan-50 p-4 rounded-xl border border-blue-100">
                        <p className="text-sm text-gray-800">
                          <span className="font-medium text-blue-600">变式{idx + 1}:</span> {v.question_text}
                        </p>
                        <p className="text-sm text-gray-600 mt-2 bg-white/60 rounded-lg px-3 py-2">
                          <span className="font-medium">答案:</span> {v.answer}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              <div className="flex space-x-3 pt-2 border-t border-gray-100">
                <button className="flex items-center text-blue-600 hover:text-blue-700 text-sm font-medium hover:bg-blue-50 px-3 py-1.5 rounded-lg transition-all">
                  <ExternalLink className="h-4 w-4 mr-1" />
                  查看变式题
                </button>
                {!q.is_mastered && (
                  <button
                    onClick={() => handleMarkMastered(q.id)}
                    className="flex items-center text-green-600 hover:text-green-700 text-sm font-medium hover:bg-green-50 px-3 py-1.5 rounded-lg transition-all"
                  >
                    <CheckCircle className="h-4 w-4 mr-1" />
                    标记已掌握
                  </button>
                )}
                {q.is_mastered && (
                  <span className="text-green-600 text-sm flex items-center font-medium bg-green-100 px-3 py-1.5 rounded-lg">
                    <CheckCircle className="h-4 w-4 mr-1" />
                    已掌握
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
        
        {questions.length === 0 && !loading && (
          <div className="text-center py-16">
            <div className="w-24 h-24 bg-gradient-to-br from-green-100 to-emerald-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <BookOpen className="h-12 w-12 text-green-500" />
            </div>
            <p className="text-gray-500 text-lg font-medium">暂无错题记录</p>
            <p className="text-sm text-gray-400 mt-2">点击上方"录入错题"按钮添加</p>
          </div>
        )}
        
        {questions.length > 0 && (
          <div className="mt-6 text-center">
            <button className="text-primary-600 hover:text-primary-700">
              加载更多
            </button>
          </div>
        )}
        </div>
      </div>
    </PageBackground>
  )
}

export default WrongNotebook
