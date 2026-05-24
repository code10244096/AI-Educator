import React, { useState } from 'react'
import { Routes, Route, useNavigate } from 'react-router-dom'
import {
  Upload,
  Database,
  BrainCircuit,
  Search,
  Filter,
  Plus,
  Eye,
  Trash2,
  Edit,
  Sparkles,
  BookOpen,
  Tag,
  MapPin,
  Calendar,
  Star,
  ChevronDown,
  X,
  FileText,
  Image,
  CheckCircle,
  Loader2
} from 'lucide-react'

const MyQuestionBank = () => {
  const [searchTerm, setSearchTerm] = useState('')
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [uploadType, setUploadType] = useState('single')
  const [uploading, setUploading] = useState(false)
  
  const myQuestions = [
    { id: 1, title: '三角函数综合题', type: '选择题', subject: '数学', grade: '高三', date: '2024-01-15', difficulty: 3, tags: ['三角函数', '综合'] },
    { id: 2, title: '数列求和专项训练', type: '填空题', subject: '数学', grade: '高三', date: '2024-01-12', difficulty: 4, tags: ['数列', '求和'] },
    { id: 3, title: '立体几何证明题', type: '解答题', subject: '数学', grade: '高二', date: '2024-01-10', difficulty: 5, tags: ['立体几何', '证明'] },
    { id: 4, title: '概率统计应用题', type: '解答题', subject: '数学', grade: '高三', date: '2024-01-08', difficulty: 3, tags: ['概率', '统计'] },
    { id: 5, title: '导数与函数单调性', type: '选择题', subject: '数学', grade: '高三', date: '2024-01-05', difficulty: 4, tags: ['导数', '函数'] },
  ]
  
  const handleUpload = () => {
    setUploading(true)
    setTimeout(() => {
      setUploading(false)
      setShowUploadModal(false)
    }, 2000)
  }
  
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">我的题库</h2>
          <p className="text-sm text-gray-500 mt-1">管理个人上传的题目资源</p>
        </div>
        <button
          onClick={() => setShowUploadModal(true)}
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
        >
          <Plus className="h-4 w-4 mr-2" />
          上传题目
        </button>
      </div>
      
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="p-5 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="搜索题目..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div className="flex items-center space-x-2">
              <button className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50">
                <Filter className="h-4 w-4 mr-2" />
                筛选
              </button>
            </div>
          </div>
        </div>
        
        <div className="divide-y divide-gray-200">
          {myQuestions.map((q) => (
            <div key={q.id} className="p-5 hover:bg-gray-50">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-2">
                    <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">{q.subject}</span>
                    <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded">{q.grade}</span>
                    <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded">{q.type}</span>
                  </div>
                  <h4 className="text-sm font-medium text-gray-900">{q.title}</h4>
                  <div className="flex items-center space-x-4 mt-2">
                    <div className="flex items-center space-x-1">
                      {[1,2,3,4,5].map(i => (
                        <Star key={i} className={`h-3 w-3 ${i <= q.difficulty ? 'text-yellow-400 fill-yellow-400' : 'text-gray-200'}`} />
                      ))}
                    </div>
                    <span className="text-xs text-gray-400">{q.date}</span>
                  </div>
                  <div className="flex items-center space-x-2 mt-2">
                    {q.tags.map((tag, idx) => (
                      <span key={idx} className="inline-flex items-center px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded">
                        <Tag className="h-3 w-3 mr-1" />
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <button className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg">
                    <Eye className="h-4 w-4" />
                  </button>
                  <button className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg">
                    <Edit className="h-4 w-4" />
                  </button>
                  <button className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
      
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl w-full max-w-lg mx-4">
            <div className="p-5 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">上传题目</h3>
              <button onClick={() => setShowUploadModal(false)} className="text-gray-400 hover:text-gray-600">
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div className="flex space-x-4">
                <button
                  onClick={() => setUploadType('single')}
                  className={`flex-1 p-4 rounded-lg border-2 text-center ${
                    uploadType === 'single' ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                  }`}
                >
                  <FileText className="h-8 w-8 mx-auto mb-2 text-gray-400" />
                  <span className="text-sm font-medium">单个上传</span>
                </button>
                <button
                  onClick={() => setUploadType('batch')}
                  className={`flex-1 p-4 rounded-lg border-2 text-center ${
                    uploadType === 'batch' ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                  }`}
                >
                  <Image className="h-8 w-8 mx-auto mb-2 text-gray-400" />
                  <span className="text-sm font-medium">批量上传</span>
                </button>
              </div>
              
              {uploadType === 'single' ? (
                <div className="space-y-3">
                  <input type="text" placeholder="题目标题" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                  <textarea placeholder="题目内容" rows={4} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                  <textarea placeholder="答案与解析" rows={3} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                </div>
              ) : (
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
                  <Upload className="h-10 w-10 mx-auto text-gray-400 mb-3" />
                  <p className="text-sm text-gray-500">拖拽文件到此处或点击上传</p>
                  <p className="text-xs text-gray-400 mt-1">支持 PDF、图片、Word 格式</p>
                </div>
              )}
            </div>
            <div className="p-5 border-t border-gray-200 flex justify-end space-x-3">
              <button
                onClick={() => setShowUploadModal(false)}
                className="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50"
              >
                取消
              </button>
              <button
                onClick={handleUpload}
                disabled={uploading}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50 inline-flex items-center"
              >
                {uploading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    上传中...
                  </>
                ) : (
                  '确认上传'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const RealQuestionBank = () => {
  const [selectedYear, setSelectedYear] = useState('2024')
  const [selectedRegion, setSelectedRegion] = useState('全部')
  
  const years = ['2024', '2023', '2022', '2021', '2020', '2019', '2018', '2017', '2016', '2015']
  const regions = ['全部', '全国甲卷', '全国乙卷', '新高考I卷', '新高考II卷', '北京', '上海', '天津', '浙江', '江苏']
  
  const questionSets = [
    { id: 1, year: '2024', region: '新高考I卷', type: '数学', count: 22, hasAnswer: true, format: 'JSON' },
    { id: 2, year: '2024', region: '全国甲卷', type: '数学', count: 22, hasAnswer: true, format: 'JSON' },
    { id: 3, year: '2024', region: '全国乙卷', type: '数学', count: 22, hasAnswer: true, format: 'JSON' },
    { id: 4, year: '2024', region: '北京', type: '数学', count: 21, hasAnswer: true, format: 'JSON' },
    { id: 5, year: '2024', region: '上海', type: '数学', count: 21, hasAnswer: true, format: 'JSON' },
    { id: 6, year: '2024', region: '天津', type: '数学', count: 20, hasAnswer: true, format: 'JSON' },
    { id: 7, year: '2023', region: '新高考I卷', type: '数学', count: 22, hasAnswer: true, format: 'JSON' },
    { id: 8, year: '2023', region: '全国甲卷', type: '数学', count: 22, hasAnswer: true, format: 'JSON' },
    { id: 9, year: '2022', region: '新高考I卷', type: '数学', count: 22, hasAnswer: true, format: 'JSON' },
    { id: 10, year: '2022', region: '全国乙卷', type: '数学', count: 22, hasAnswer: true, format: 'JSON' },
  ]
  
  const filteredSets = questionSets.filter(s => {
    if (selectedYear !== '全部' && s.year !== selectedYear) return false
    if (selectedRegion !== '全部' && s.region !== selectedRegion) return false
    return true
  })
  
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900">真题资源库</h2>
        <p className="text-sm text-gray-500 mt-1">历年高考真题及答案解析</p>
      </div>
      
      <div className="flex items-center space-x-4">
        <select
          value={selectedYear}
          onChange={(e) => setSelectedYear(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
        >
          <option value="全部">全部年份</option>
          {years.map(y => <option key={y} value={y}>{y}年</option>)}
        </select>
        <select
          value={selectedRegion}
          onChange={(e) => setSelectedRegion(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
        >
          {regions.map(r => <option key={r} value={r}>{r}</option>)}
        </select>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredSets.map((set) => (
          <div key={set.id} className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="flex items-center space-x-2 mb-1">
                  <Calendar className="h-4 w-4 text-gray-400" />
                  <span className="text-sm font-medium text-gray-900">{set.year}年</span>
                </div>
                <div className="flex items-center space-x-2">
                  <MapPin className="h-4 w-4 text-gray-400" />
                  <span className="text-sm text-gray-600">{set.region}</span>
                </div>
              </div>
              <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">{set.type}</span>
            </div>
            <div className="flex items-center justify-between text-sm text-gray-500">
              <span>{set.count} 道题目</span>
              <div className="flex items-center space-x-2">
                {set.hasAnswer && (
                  <span className="inline-flex items-center text-green-600">
                    <CheckCircle className="h-4 w-4 mr-1" />
                    含答案
                  </span>
                )}
                <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded">{set.format}</span>
              </div>
            </div>
            <div className="mt-3 flex space-x-2">
              <button className="flex-1 px-3 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 inline-flex items-center justify-center">
                <Eye className="h-4 w-4 mr-1" />
                查看
              </button>
              <button className="px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50">
                下载
              </button>
            </div>
          </div>
        ))}
      </div>
      
      {filteredSets.length === 0 && (
        <div className="text-center py-12">
          <Database className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">暂无匹配的真题资源</p>
        </div>
      )}
    </div>
  )
}

const AIQuestionBank = () => {
  const [prompt, setPrompt] = useState('')
  const [generating, setGenerating] = useState(false)
  const [generatedQuestions, setGeneratedQuestions] = useState([])
  
  const quickPrompts = [
    '生成5道三角函数选择题，难度中等',
    '生成3道数列求和解答题，含详细解析',
    '生成一道立体几何证明题，难度较高',
    '生成概率统计应用题，结合实际场景',
  ]
  
  const handleGenerate = () => {
    if (!prompt.trim()) return
    setGenerating(true)
    setTimeout(() => {
      setGeneratedQuestions([
        { id: 1, question: '已知函数 f(x) = sin(2x + π/3)，求 f(x) 的最小正周期。', answer: 'T = π', difficulty: 2, type: '填空题' },
        { id: 2, question: '若 sinα = 3/5，α ∈ (π/2, π)，求 cosα 的值。', answer: '-4/5', difficulty: 2, type: '填空题' },
        { id: 3, question: '求函数 y = 2sin(x - π/4) 的单调递增区间。', answer: '[2kπ - π/4, 2kπ + 3π/4], k∈Z', difficulty: 3, type: '解答题' },
      ])
      setGenerating(false)
    }, 3000)
  }
  
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900">AI 智题库</h2>
        <p className="text-sm text-gray-500 mt-1">使用 AI 大模型智能生成题目</p>
      </div>
      
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex items-center space-x-2 mb-4">
          <Sparkles className="h-5 w-5 text-purple-500" />
          <span className="text-sm font-medium text-gray-700">快速生成</span>
        </div>
        <div className="flex flex-wrap gap-2 mb-4">
          {quickPrompts.map((p, idx) => (
            <button
              key={idx}
              onClick={() => setPrompt(p)}
              className="px-3 py-1.5 bg-purple-50 text-purple-700 text-xs rounded-lg hover:bg-purple-100 transition-colors"
            >
              {p}
            </button>
          ))}
        </div>
        <div className="flex space-x-3">
          <input
            type="text"
            placeholder="描述你想要生成的题目类型、知识点、难度等..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
          />
          <button
            onClick={handleGenerate}
            disabled={generating || !prompt.trim()}
            className="px-6 py-2.5 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg text-sm hover:shadow-lg disabled:opacity-50 inline-flex items-center"
          >
            {generating ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                生成中...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4 mr-2" />
                生成题目
              </>
            )}
          </button>
        </div>
      </div>
      
      {generatedQuestions.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="p-5 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">生成结果</h3>
          </div>
          <div className="divide-y divide-gray-200">
            {generatedQuestions.map((q) => (
              <div key={q.id} className="p-5">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-2">
                      <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded">{q.type}</span>
                      <div className="flex items-center space-x-1">
                        {[1,2,3,4,5].map(i => (
                          <Star key={i} className={`h-3 w-3 ${i <= q.difficulty ? 'text-yellow-400 fill-yellow-400' : 'text-gray-200'}`} />
                        ))}
                      </div>
                    </div>
                    <p className="text-sm text-gray-900">{q.question}</p>
                    <div className="mt-3 p-3 bg-green-50 rounded-lg">
                      <span className="text-xs font-medium text-green-700">参考答案：</span>
                      <span className="text-sm text-green-800 ml-2">{q.answer}</span>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2 ml-4">
                    <button className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg">
                      <Eye className="h-4 w-4" />
                    </button>
                    <button className="p-2 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded-lg">
                      <CheckCircle className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

const QuestionBank = () => {
  return (
    <div className="p-6">
      <Routes>
        <Route path="my" element={<MyQuestionBank />} />
        <Route path="real" element={<RealQuestionBank />} />
        <Route path="ai" element={<AIQuestionBank />} />
        <Route path="/" element={<MyQuestionBank />} />
      </Routes>
    </div>
  )
}

export default QuestionBank
