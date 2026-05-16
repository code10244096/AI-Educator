import React, { useState, useEffect } from 'react'
import { Plus, Filter, Calendar, CheckCircle, ExternalLink, BookOpen } from 'lucide-react'
import { notebookAPI } from '../utils/api'
import ReactMarkdown from 'react-markdown'
import PageBackground from '../components/PageBackground'

const WrongNotebook = () => {
  const [questions, setQuestions] = useState([])
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState({ knowledgePoint: '', subject: '数学' })
  const [isVisible, setIsVisible] = useState(false)
  
  useEffect(() => {
    setIsVisible(true)
  }, [])
  
  const handleUpload = async (event) => {
    const file = event.target.files[0]
    if (!file) return
    
    setLoading(true)
    try {
      const response = await notebookAPI.upload(
        file,
        filter.knowledgePoint || '未分类',
        filter.subject
      )
      setQuestions(prev => [response, ...prev])
    } catch (error) {
      console.error('录入失败:', error)
      alert('录入失败，请重试')
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
      <div className={`max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12 transition-all duration-1000 ${
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-12'
      }`}>
        <div className="bg-white/90 backdrop-blur-md rounded-2xl shadow-xl p-8 border border-white/20">
          <div className="flex items-center space-x-3 mb-8">
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
          
          <div className="flex justify-between items-center mb-6">
          <div className="flex space-x-4">
            <label className="flex items-center space-x-2">
              <Plus className="h-5 w-5" />
              <span>录入错题</span>
              <input
                type="file"
                accept="image/*"
                onChange={handleUpload}
                className="hidden"
                id="upload-wrong"
              />
              <label
                htmlFor="upload-wrong"
                className="bg-primary-600 text-white px-4 py-2 rounded-lg cursor-pointer hover:bg-primary-700"
              >
                上传
              </label>
            </label>
            
            <select
              value={filter.knowledgePoint}
              onChange={(e) => setFilter(prev => ({ ...prev, knowledgePoint: e.target.value }))}
              className="border border-gray-300 rounded-lg px-3 py-2"
            >
              <option value="">按知识点筛选</option>
              <option value="三角函数">三角函数</option>
              <option value="导数">导数</option>
              <option value="函数">函数</option>
            </select>
            
            <select
              value={filter.subject}
              onChange={(e) => setFilter(prev => ({ ...prev, subject: e.target.value }))}
              className="border border-gray-300 rounded-lg px-3 py-2"
            >
              <option value="数学">数学</option>
              <option value="物理">物理</option>
              <option value="化学">化学</option>
            </select>
          </div>
        </div>
        
        {loading && (
          <div className="text-center py-8">
            <p className="text-gray-600">正在录入错题...</p>
          </div>
        )}
        
        <div className="space-y-4">
          {questions.map((q) => (
            <div
              key={q.id}
              className={`border rounded-lg p-4 ${
                q.is_mastered ? 'border-green-200 bg-green-50' : 'border-gray-200'
              }`}
            >
              <div className="flex justify-between items-start mb-3">
                <div className="flex items-center space-x-2">
                  <Calendar className="h-4 w-4 text-gray-500" />
                  <span className="text-sm text-gray-600">
                    {new Date(q.error_date).toLocaleDateString('zh-CN')}
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                    {q.knowledge_point}
                  </span>
                  <span className="px-2 py-1 bg-gray-100 text-gray-800 rounded text-xs">
                    {q.subject}
                  </span>
                </div>
              </div>
              
              <div className="mb-3">
                <p className="text-sm font-medium text-gray-700 mb-1">原题:</p>
                <p className="text-gray-900">{q.question_text}</p>
              </div>
              
              <div className="grid grid-cols-2 gap-4 mb-3">
                <div>
                  <p className="text-sm font-medium text-gray-700 mb-1">我的答案:</p>
                  <p className="text-red-600">{q.user_answer || '未作答'}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-700 mb-1">正确答案:</p>
                  <p className="text-green-600">{q.correct_answer}</p>
                </div>
              </div>
              
              {q.variant_questions && q.variant_questions.length > 0 && (
                <div className="mb-3">
                  <p className="text-sm font-medium text-gray-700 mb-2">变式题:</p>
                  <div className="space-y-2">
                    {q.variant_questions.map((v, idx) => (
                      <div key={idx} className="bg-white p-3 rounded border">
                        <p className="text-sm text-gray-800">
                          <span className="font-medium">变式{idx + 1}:</span> {v.question_text}
                        </p>
                        <p className="text-sm text-gray-600 mt-1">
                          <span className="font-medium">答案:</span> {v.answer}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              <div className="flex space-x-3">
                <button className="flex items-center text-primary-600 hover:text-primary-700 text-sm">
                  <ExternalLink className="h-4 w-4 mr-1" />
                  查看变式题
                </button>
                {!q.is_mastered && (
                  <button
                    onClick={() => handleMarkMastered(q.id)}
                    className="flex items-center text-green-600 hover:text-green-700 text-sm"
                  >
                    <CheckCircle className="h-4 w-4 mr-1" />
                    标记已掌握
                  </button>
                )}
                {q.is_mastered && (
                  <span className="text-green-600 text-sm flex items-center">
                    <CheckCircle className="h-4 w-4 mr-1" />
                    已掌握
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
        
        {questions.length === 0 && !loading && (
          <div className="text-center py-12">
            <p className="text-gray-500">暂无错题记录</p>
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
