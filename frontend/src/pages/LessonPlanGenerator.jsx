import React, { useState, useEffect } from 'react'
import { FileDown, Edit, FileText } from 'lucide-react'
import { lessonPlanAPI } from '../utils/api'
import ReactMarkdown from 'react-markdown'
import PageBackground from '../components/PageBackground'

const LessonPlanGenerator = () => {
  const [formData, setFormData] = useState({
    title: '',
    period: '1 课时',
    studentLevel: '中等',
    requirements: '',
  })
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [isVisible, setIsVisible] = useState(false)
  
  useEffect(() => {
    setIsVisible(true)
  }, [])
  
  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!formData.title) {
      alert('请输入课题名称')
      return
    }
    
    setLoading(true)
    try {
      const response = await lessonPlanAPI.generate(
        formData.title,
        formData.period,
        formData.studentLevel,
        formData.requirements
      )
      setResult(response)
    } catch (error) {
      console.error('生成失败:', error)
      alert('生成失败，请重试')
    } finally {
      setLoading(false)
    }
  }
  
  const handleExport = (format) => {
    // 导出功能实现
    const content = result.content
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${formData.title}.${format === 'word' ? 'docx' : 'pdf'}`
    a.click()
    URL.revokeObjectURL(url)
  }
  
  return (
    <PageBackground gradient="lessonplan">
      <div className={`max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 transition-all duration-1000 ${
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-12'
      }`}>
        <div className="bg-white/90 backdrop-blur-md rounded-2xl shadow-xl p-8 border border-white/20">
          <div className="flex items-center space-x-3 mb-8">
            <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl flex items-center justify-center shadow-lg">
              <FileText className="h-6 w-6 text-white" />
            </div>
            <div>
              <h2 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
                AI 教案生成
              </h2>
              <p className="text-sm text-gray-600">一键生成，个性化定制，省时省力</p>
            </div>
          </div>
        
        {/* 表单 */}
        <form onSubmit={handleSubmit} className="space-y-4 mb-8">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              课题名称
            </label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              placeholder="例如：导数的几何意义"
            />
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                课时数
              </label>
              <select
                value={formData.period}
                onChange={(e) => setFormData(prev => ({ ...prev, period: e.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-4 py-2"
              >
                <option value="1 课时">1 课时</option>
                <option value="2 课时">2 课时</option>
                <option value="3 课时">3 课时</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                学生基础
              </label>
              <select
                value={formData.studentLevel}
                onChange={(e) => setFormData(prev => ({ ...prev, studentLevel: e.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-4 py-2"
              >
                <option value="基础薄弱">基础薄弱</option>
                <option value="中等">中等</option>
                <option value="培优">培优</option>
              </select>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              额外要求
            </label>
            <input
              type="text"
              value={formData.requirements}
              onChange={(e) => setFormData(prev => ({ ...prev, requirements: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              placeholder="例如：多举例生活场景，包含真题"
            />
          </div>
          
          <button
            type="submit"
            disabled={loading || !formData.title}
            className={`w-full py-3 px-4 rounded-lg text-white font-medium ${
              loading || !formData.title
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-primary-600 hover:bg-primary-700'
            }`}
          >
            {loading ? '正在生成...' : '生成教案'}
          </button>
        </form>
        
        {/* 教案预览 */}
        {result && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold">教案预览</h3>
              <div className="flex space-x-3">
                <button
                  onClick={() => handleExport('word')}
                  className="flex items-center text-primary-600 hover:text-primary-700"
                >
                  <FileDown className="h-4 w-4 mr-2" />
                  导出 Word
                </button>
                <button
                  onClick={() => handleExport('pdf')}
                  className="flex items-center text-primary-600 hover:text-primary-700"
                >
                  <FileDown className="h-4 w-4 mr-2" />
                  导出 PDF
                </button>
              </div>
            </div>
            
            <div className="border rounded-lg p-6 bg-gray-50">
              <div className="prose max-w-none">
                <ReactMarkdown>{result.content}</ReactMarkdown>
              </div>
            </div>
          </div>
        )}
        </div>
      </div>
    </PageBackground>
  )
}

export default LessonPlanGenerator
