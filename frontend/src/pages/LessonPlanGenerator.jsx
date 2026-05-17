import React, { useState, useEffect, useRef } from 'react'
import { FileDown, FileText, Download } from 'lucide-react'
import { lessonPlanAPI } from '../utils/api'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import PageBackground from '../components/PageBackground'
import { useTask } from '../context/TaskContext'
import 'katex/dist/katex.min.css'
import html2pdf from 'html2pdf.js'

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
  const [elapsedTime, setElapsedTime] = useState(0)
  const [error, setError] = useState(null)
  const [currentTaskId, setCurrentTaskId] = useState(null)
  const [exporting, setExporting] = useState(false)
  
  const previewRef = useRef(null)
  
  const { addTask, updateTask, tasks } = useTask()
  
  useEffect(() => {
    setIsVisible(true)
  }, [])
  
  useEffect(() => {
    let interval
    if (loading) {
      setElapsedTime(0)
      interval = setInterval(() => {
        setElapsedTime(prev => prev + 1)
      }, 1000)
    }
    return () => clearInterval(interval)
  }, [loading])
  
  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!formData.title) {
      alert('请输入课题名称')
      return
    }
    
    const taskId = Date.now().toString()
    const newTask = {
      id: taskId,
      type: 'lessonplan',
      title: formData.title,
      period: formData.period,
      studentLevel: formData.studentLevel,
      requirements: formData.requirements,
      status: 'running',
      startTime: new Date().toISOString(),
      elapsedTime: 0,
      result: null,
      error: null
    }
    
    addTask(newTask)
    setCurrentTaskId(taskId)
    
    setLoading(true)
    setElapsedTime(0)
    setError(null)
    setResult(null)
    
    try {
      const response = await lessonPlanAPI.generate(
        formData.title,
        formData.period,
        formData.studentLevel,
        formData.requirements
      )
      setResult(response)
      
      updateTask(taskId, {
        status: 'completed',
        result: response,
        elapsedTime: elapsedTime
      })
    } catch (error) {
      console.error('生成失败:', error)
      setError(error.response?.data?.detail || error.message || '生成失败，请重试')
      
      updateTask(taskId, {
        status: 'failed',
        error: error.response?.data?.detail || error.message || '生成失败'
      })
    } finally {
      setLoading(false)
    }
  }
  
  const handleViewTask = (task) => {
    if (task.status === 'completed' && task.result) {
      setResult(task.result)
      setFormData({
        title: task.title,
        period: task.period,
        studentLevel: task.studentLevel,
        requirements: task.requirements || ''
      })
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }
  
  useEffect(() => {
    const handleViewTaskEvent = (e) => {
      handleViewTask(e.detail)
    }
    window.addEventListener('viewTask', handleViewTaskEvent)
    return () => window.removeEventListener('viewTask', handleViewTaskEvent)
  }, [])
  
  const handleExportTxt = () => {
    const content = result.content
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${formData.title}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }
  
  const handleExportPdf = async () => {
    if (!previewRef.current) return
    setExporting(true)
    
    try {
      const element = previewRef.current
      
      // 等待 KaTeX 公式完全渲染
      await new Promise(resolve => setTimeout(resolve, 500))
      
      // 创建克隆元素用于 PDF 导出
      const clone = element.cloneNode(true)
      clone.style.width = '210mm'
      clone.style.padding = '15mm'
      clone.style.background = 'white'
      clone.style.fontFamily = '"Noto Serif SC", "Source Han Serif SC", "SimSun", serif'
      clone.style.lineHeight = '1.8'
      clone.style.color = '#333'
      
      // 添加 KaTeX 样式
      const katexStyle = document.createElement('style')
      katexStyle.textContent = `
        .katex { font-size: 1.1em !important; }
        .katex-display { margin: 1rem 0 !important; overflow-x: auto !important; }
        h1 { font-size: 1.5rem; font-weight: bold; text-align: center; margin-bottom: 1rem; }
        h2 { font-size: 1.25rem; font-weight: bold; margin-top: 1.5rem; margin-bottom: 0.75rem; border-left: 4px solid #6366f1; padding-left: 0.75rem; }
        h3 { font-size: 1.1rem; font-weight: 600; margin-top: 1rem; margin-bottom: 0.5rem; }
        p { margin-bottom: 0.75rem; }
        ul, ol { margin-left: 1.5rem; margin-bottom: 0.75rem; }
        li { margin-bottom: 0.25rem; }
        table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
        th, td { border: 1px solid #d1d5db; padding: 0.5rem 0.75rem; text-align: left; }
        th { background-color: #f3f4f6; font-weight: 600; }
      `
      clone.insertBefore(katexStyle, clone.firstChild)
      
      // 添加到临时容器
      const tempContainer = document.createElement('div')
      tempContainer.style.position = 'absolute'
      tempContainer.style.left = '-9999px'
      tempContainer.style.top = '0'
      tempContainer.appendChild(clone)
      document.body.appendChild(tempContainer)
      
      const opt = {
        margin: [0, 0, 0, 0],
        filename: `${formData.title}.pdf`,
        image: { type: 'jpeg', quality: 1 },
        html2canvas: { 
          scale: 3,
          useCORS: true,
          letterRendering: true,
          logging: false,
          windowWidth: 794, // A4 width in pixels at 96 DPI
        },
        jsPDF: { 
          unit: 'mm', 
          format: 'a4', 
          orientation: 'portrait'
        },
        pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
      }
      
      await html2pdf().set(opt).from(clone).save()
      
      // 清理临时容器
      document.body.removeChild(tempContainer)
    } catch (err) {
      console.error('PDF导出失败:', err)
      alert('PDF导出失败，请重试')
    } finally {
      setExporting(false)
    }
  }
  
  return (
    <PageBackground gradient="lessonplan">
      <div className={`max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 pb-12 transition-all duration-1000 ${
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
          
          {loading && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">正在生成教案...</span>
                <span className="text-primary-600 font-medium">
                  已耗时 {elapsedTime}秒
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-purple-500 to-pink-500 h-full rounded-full transition-all duration-500 ease-out"
                  style={{ width: '100%' }}
                >
                  <div className="h-full bg-white/30 animate-pulse" style={{ width: '100%' }}></div>
                </div>
              </div>
              <div className="text-xs text-gray-500 text-center">
                {elapsedTime < 10 && "AI 正在分析课题，设计教学目标..."}
                {elapsedTime >= 10 && elapsedTime < 20 && "AI 正在规划教学重难点和教学方法..."}
                {elapsedTime >= 20 && elapsedTime < 30 && "AI 正在设计详细的教学过程..."}
                {elapsedTime >= 30 && "AI 正在完善板书设计和教学反思..."}
              </div>
            </div>
          )}
          
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-start">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">生成失败</h3>
                  <p className="mt-1 text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}
          
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
        
        {result && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold">教案预览</h3>
              <div className="flex space-x-3">
                <button
                  onClick={handleExportTxt}
                  className="flex items-center px-4 py-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors"
                >
                  <FileDown className="h-4 w-4 mr-2" />
                  导出TXT
                </button>
                <button
                  onClick={handleExportPdf}
                  disabled={exporting}
                  className="flex items-center px-4 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors disabled:opacity-50"
                >
                  <Download className="h-4 w-4 mr-2" />
                  {exporting ? '生成中...' : '导出PDF'}
                </button>
              </div>
            </div>
            
            <div 
              ref={previewRef}
              className="border rounded-lg p-6 bg-white lesson-plan-content"
              style={{
                fontFamily: '"Noto Serif SC", "Source Han Serif SC", "SimSun", serif',
                lineHeight: '1.8'
              }}
            >
              <style>{`
                .lesson-plan-content h1 {
                  font-size: 1.5rem;
                  font-weight: bold;
                  text-align: center;
                  margin-bottom: 1rem;
                  color: #1a1a1a;
                }
                .lesson-plan-content h2 {
                  font-size: 1.25rem;
                  font-weight: bold;
                  margin-top: 1.5rem;
                  margin-bottom: 0.75rem;
                  color: #333;
                  border-left: 4px solid #6366f1;
                  padding-left: 0.75rem;
                }
                .lesson-plan-content h3 {
                  font-size: 1.1rem;
                  font-weight: 600;
                  margin-top: 1rem;
                  margin-bottom: 0.5rem;
                  color: #444;
                }
                .lesson-plan-content p {
                  margin-bottom: 0.75rem;
                  color: #374151;
                }
                .lesson-plan-content ul, .lesson-plan-content ol {
                  margin-left: 1.5rem;
                  margin-bottom: 0.75rem;
                }
                .lesson-plan-content li {
                  margin-bottom: 0.25rem;
                  color: #374151;
                }
                .lesson-plan-content strong {
                  color: #1f2937;
                }
                .lesson-plan-content table {
                  width: 100%;
                  border-collapse: collapse;
                  margin: 1rem 0;
                }
                .lesson-plan-content th, .lesson-plan-content td {
                  border: 1px solid #d1d5db;
                  padding: 0.5rem 0.75rem;
                  text-align: left;
                }
                .lesson-plan-content th {
                  background-color: #f3f4f6;
                  font-weight: 600;
                }
                .lesson-plan-content .katex {
                  font-size: 1.1em;
                }
                .lesson-plan-content .katex-display {
                  margin: 1rem 0;
                  overflow-x: auto;
                  overflow-y: hidden;
                }
              `}</style>
              <ReactMarkdown
                remarkPlugins={[remarkMath]}
                rehypePlugins={[rehypeKatex]}
              >
                {result.content}
              </ReactMarkdown>
            </div>
          </div>
        )}
        </div>
      </div>
    </PageBackground>
  )
}

export default LessonPlanGenerator
