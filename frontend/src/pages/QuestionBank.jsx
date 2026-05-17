import React, { useState, useEffect } from 'react'
import { Search, BookOpen, Star, Filter, ChevronDown, Eye, BookMarked } from 'lucide-react'
import { questionBankAPI } from '../utils/api'

const QuestionBank = () => {
  const [questions, setQuestions] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [filters, setFilters] = useState({
    subject: '',
    education_level: '',
    exam_type: '',
    year: '',
    difficulty: '',
  })
  const [stats, setStats] = useState(null)
  const [selectedQuestion, setSelectedQuestion] = useState(null)
  const [showDetail, setShowDetail] = useState(false)
  const [showFilters, setShowFilters] = useState(false)

  useEffect(() => {
    loadQuestions()
    loadStats()
  }, [])

  const loadQuestions = async (params = {}) => {
    setLoading(true)
    try {
      const data = await questionBankAPI.getList({
        ...filters,
        ...params,
        limit: 50
      })
      setQuestions(data)
    } catch (error) {
      console.error('加载题目失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadStats = async () => {
    try {
      const data = await questionBankAPI.getStats()
      setStats(data)
    } catch (error) {
      console.error('加载统计失败:', error)
    }
  }

  const handleSearch = () => {
    if (searchKeyword.trim()) {
      loadQuestions({ knowledge_point: searchKeyword })
    } else {
      loadQuestions()
    }
  }

  const handleFilterChange = (key, value) => {
    const newFilters = { ...filters, [key]: value }
    setFilters(newFilters)
    loadQuestions(newFilters)
  }

  const handleViewDetail = async (questionId) => {
    try {
      const data = await questionBankAPI.getById(questionId)
      setSelectedQuestion(data)
      setShowDetail(true)
    } catch (error) {
      console.error('加载题目详情失败:', error)
    }
  }

  const getDifficultyStars = (difficulty) => {
    return '★'.repeat(difficulty) + '☆'.repeat(5 - difficulty)
  }

  const getDifficultyColor = (difficulty) => {
    const colors = {
      1: 'text-green-500',
      2: 'text-blue-500',
      3: 'text-yellow-500',
      4: 'text-orange-500',
      5: 'text-red-500'
    }
    return colors[difficulty] || 'text-gray-500'
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
            题库管理
          </h1>
          <p className="text-gray-600">
            浏览、搜索和管理题库中的题目
          </p>
        </div>

        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 shadow-lg border border-white/20">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">题目总数</p>
                  <p className="text-3xl font-bold text-blue-600">{stats.total}</p>
                </div>
                <BookOpen className="h-10 w-10 text-blue-500" />
              </div>
            </div>
            
            <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 shadow-lg border border-white/20">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">学科分布</p>
                  <p className="text-lg font-semibold text-purple-600">
                    {Object.keys(stats.by_subject || {}).join(', ') || '数学'}
                  </p>
                </div>
                <BookMarked className="h-10 w-10 text-purple-500" />
              </div>
            </div>

            <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 shadow-lg border border-white/20">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">学龄分布</p>
                  <p className="text-lg font-semibold text-pink-600">
                    {Object.keys(stats.by_education_level || {}).join(', ') || '高中'}
                  </p>
                </div>
                <Star className="h-10 w-10 text-pink-500" />
              </div>
            </div>
          </div>
        )}

        <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 shadow-lg border border-white/20 mb-6">
          <div className="flex gap-4 mb-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="搜索题目、知识点..."
                value={searchKeyword}
                onChange={(e) => setSearchKeyword(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                className="w-full pl-10 pr-4 py-3 rounded-xl border border-gray-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all"
              />
            </div>
            <button
              onClick={handleSearch}
              className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-xl hover:shadow-lg transition-all"
            >
              搜索
            </button>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="px-4 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-all flex items-center gap-2"
            >
              <Filter className="h-5 w-5" />
              筛选
              <ChevronDown className={`h-4 w-4 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
            </button>
          </div>

          {showFilters && (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 pt-4 border-t border-gray-200">
              <div>
                <label className="block text-sm text-gray-600 mb-1">学科</label>
                <select
                  value={filters.subject}
                  onChange={(e) => handleFilterChange('subject', e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:border-blue-500"
                >
                  <option value="">全部</option>
                  <option value="数学">数学</option>
                  <option value="物理">物理</option>
                  <option value="化学">化学</option>
                  <option value="语文">语文</option>
                  <option value="英语">英语</option>
                </select>
              </div>

              <div>
                <label className="block text-sm text-gray-600 mb-1">学龄</label>
                <select
                  value={filters.education_level}
                  onChange={(e) => handleFilterChange('education_level', e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:border-blue-500"
                >
                  <option value="">全部</option>
                  <option value="小学">小学</option>
                  <option value="初中">初中</option>
                  <option value="高中">高中</option>
                </select>
              </div>

              <div>
                <label className="block text-sm text-gray-600 mb-1">考试类型</label>
                <select
                  value={filters.exam_type}
                  onChange={(e) => handleFilterChange('exam_type', e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:border-blue-500"
                >
                  <option value="">全部</option>
                  <option value="高考">高考</option>
                  <option value="中考">中考</option>
                  <option value="月考">月考</option>
                </select>
              </div>

              <div>
                <label className="block text-sm text-gray-600 mb-1">难度</label>
                <select
                  value={filters.difficulty}
                  onChange={(e) => handleFilterChange('difficulty', e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:border-blue-500"
                >
                  <option value="">全部</option>
                  <option value="1">★</option>
                  <option value="2">★★</option>
                  <option value="3">★★★</option>
                  <option value="4">★★★★</option>
                  <option value="5">★★★★★</option>
                </select>
              </div>

              <div>
                <label className="block text-sm text-gray-600 mb-1">年份</label>
                <select
                  value={filters.year}
                  onChange={(e) => handleFilterChange('year', e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:border-blue-500"
                >
                  <option value="">全部</option>
                  <option value="2024">2024</option>
                  <option value="2023">2023</option>
                  <option value="2022">2022</option>
                  <option value="2021">2021</option>
                  <option value="2020">2020</option>
                </select>
              </div>
            </div>
          )}
        </div>

        {loading ? (
          <div className="flex justify-center items-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          </div>
        ) : (
          <div className="space-y-4">
            {questions.map((question) => (
              <div
                key={question.id}
                className="bg-white/80 backdrop-blur-sm rounded-xl p-6 shadow-lg border border-white/20 hover:shadow-xl transition-all"
              >
                <div className="flex justify-between items-start mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-lg">
                        {question.subject}
                      </span>
                      <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded-lg">
                        {question.education_level}
                      </span>
                      {question.exam_type && (
                        <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-lg">
                          {question.exam_type}
                        </span>
                      )}
                      {question.year && (
                        <span className="px-2 py-1 bg-orange-100 text-orange-700 text-xs rounded-lg">
                          {question.year}年
                        </span>
                      )}
                      {question.region && (
                        <span className="px-2 py-1 bg-pink-100 text-pink-700 text-xs rounded-lg">
                          {question.region}
                        </span>
                      )}
                    </div>
                    <p className="text-gray-900 font-medium">{question.question_text}</p>
                  </div>
                  <button
                    onClick={() => handleViewDetail(question.id)}
                    className="ml-4 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center gap-2"
                  >
                    <Eye className="h-4 w-4" />
                    详情
                  </button>
                </div>

                <div className="flex items-center justify-between text-sm text-gray-600">
                  <div className="flex items-center gap-4">
                    <span className="flex items-center gap-1">
                      <span className={getDifficultyColor(question.difficulty)}>
                        {getDifficultyStars(question.difficulty)}
                      </span>
                    </span>
                    {question.score && (
                      <span className="text-gray-500">{question.score}分</span>
                    )}
                    {question.knowledge_points && question.knowledge_points.length > 0 && (
                      <span className="text-gray-500">
                        知识点: {question.knowledge_points.join(', ')}
                      </span>
                    )}
                  </div>
                  {question.is_verified && (
                    <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-lg">
                      已审核
                    </span>
                  )}
                </div>
              </div>
            ))}

            {questions.length === 0 && (
              <div className="text-center py-20">
                <BookOpen className="h-16 w-16 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500">暂无题目</p>
              </div>
            )}
          </div>
        )}

        {showDetail && selectedQuestion && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-2xl">
              <div className="sticky top-0 bg-white border-b border-gray-200 p-6 rounded-t-2xl">
                <div className="flex justify-between items-start">
                  <h2 className="text-2xl font-bold text-gray-900">题目详情</h2>
                  <button
                    onClick={() => setShowDetail(false)}
                    className="text-gray-400 hover:text-gray-600 text-2xl"
                  >
                    ×
                  </button>
                </div>
              </div>

              <div className="p-6 space-y-6">
                <div>
                  <h3 className="text-sm font-semibold text-gray-500 mb-2">题目信息</h3>
                  <div className="flex flex-wrap gap-2 mb-3">
                    <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-lg">
                      {selectedQuestion.subject}
                    </span>
                    <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded-lg">
                      {selectedQuestion.education_level}
                    </span>
                    <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-lg">
                      {selectedQuestion.question_type}
                    </span>
                    {selectedQuestion.exam_type && (
                      <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-lg">
                        {selectedQuestion.exam_type}
                      </span>
                    )}
                    {selectedQuestion.year && (
                      <span className="px-2 py-1 bg-orange-100 text-orange-700 text-xs rounded-lg">
                        {selectedQuestion.year}年 {selectedQuestion.region}
                      </span>
                    )}
                  </div>
                  <p className="text-gray-900 whitespace-pre-wrap">{selectedQuestion.question_text}</p>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-gray-500 mb-2">答案</h3>
                  <p className="text-gray-900 whitespace-pre-wrap bg-green-50 p-4 rounded-lg">
                    {selectedQuestion.answer}
                  </p>
                </div>

                {selectedQuestion.solution && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-500 mb-2">详细解析</h3>
                    <p className="text-gray-900 whitespace-pre-wrap bg-blue-50 p-4 rounded-lg">
                      {selectedQuestion.solution}
                    </p>
                  </div>
                )}

                {selectedQuestion.knowledge_points && selectedQuestion.knowledge_points.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-500 mb-2">知识点</h3>
                    <div className="flex flex-wrap gap-2">
                      {selectedQuestion.knowledge_points.map((kp, index) => (
                        <span key={index} className="px-3 py-1 bg-purple-100 text-purple-700 rounded-lg text-sm">
                          {kp}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex items-center gap-4">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-500 mb-1">难度</h3>
                    <span className={getDifficultyColor(selectedQuestion.difficulty)}>
                      {getDifficultyStars(selectedQuestion.difficulty)}
                    </span>
                  </div>
                  {selectedQuestion.score && (
                    <div>
                      <h3 className="text-sm font-semibold text-gray-500 mb-1">分值</h3>
                      <span className="text-gray-900">{selectedQuestion.score}分</span>
                    </div>
                  )}
                </div>

                {selectedQuestion.teaching_tips && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-500 mb-2">教学建议</h3>
                    <p className="text-gray-900 whitespace-pre-wrap bg-yellow-50 p-4 rounded-lg">
                      {selectedQuestion.teaching_tips}
                    </p>
                  </div>
                )}

                {selectedQuestion.common_mistakes && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-500 mb-2">常见错误</h3>
                    <p className="text-gray-900 whitespace-pre-wrap bg-red-50 p-4 rounded-lg">
                      {selectedQuestion.common_mistakes}
                    </p>
                  </div>
                )}

                {selectedQuestion.variants && selectedQuestion.variants.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-500 mb-2">变式题</h3>
                    <div className="space-y-3">
                      {selectedQuestion.variants.map((variant) => (
                        <div key={variant.id} className="bg-gray-50 p-4 rounded-lg">
                          <p className="text-gray-900 mb-2">{variant.question_text}</p>
                          <p className="text-sm text-gray-600">答案: {variant.answer}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default QuestionBank
