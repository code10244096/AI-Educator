import React, { useState, useCallback, useEffect, useRef } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, X, FileText, FileSpreadsheet, File, AlertCircle, CheckCircle, Loader2, Download } from 'lucide-react'
import { homeworkAPI } from '../utils/api'
import { useTask } from '../context/TaskContext'
import PageBackground from '../components/PageBackground'
import html2pdf from 'html2pdf.js'

const FILE_TYPE_ICONS = {
  image: FileText,
  pdf: FileText,
  word: FileText,
  excel: FileSpreadsheet,
  text: File,
}

const getFileType = (file) => {
  const ext = file.name.split('.').pop().toLowerCase()
  if (['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'].includes(ext)) return 'image'
  if (ext === 'pdf') return 'pdf'
  if (['doc', 'docx'].includes(ext)) return 'word'
  if (['xls', 'xlsx'].includes(ext)) return 'excel'
  if (['md', 'txt'].includes(ext)) return 'text'
  return 'unknown'
}

const HomeworkGrader = () => {
  const { addTask, updateTask } = useTask()
  const [files, setFiles] = useState([])
  const [referenceAnswer, setReferenceAnswer] = useState('')
  const [processing, setProcessing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [progressLabel, setProgressLabel] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [isVisible, setIsVisible] = useState(false)
  const [taskId, setTaskId] = useState(null)
  const [exporting, setExporting] = useState(false)
  const resultRef = useRef(null)

  useEffect(() => {
    setIsVisible(true)
  }, [])
  
  const cleanLatex = (text) => {
    if (!text) return ''
    return text
      .replace(/\\\(/g, '')
      .replace(/\\\)/g, '')
      .replace(/\\\[/g, '')
      .replace(/\\\]/g, '')
      .replace(/\\frac\{([^}]+)\}\{([^}]+)\}/g, '($1)/($2)')
      .replace(/\\mathbb\{([^}]+)\}/g, '$1')
      .replace(/\\triangle/g, '△')
      .replace(/\\circ/g, '°')
      .replace(/\\cdot/g, '·')
      .replace(/\\times/g, '×')
      .replace(/\\div/g, '÷')
      .replace(/\\pm/g, '±')
      .replace(/\\leq/g, '≤')
      .replace(/\\geq/g, '≥')
      .replace(/\\neq/g, '≠')
      .replace(/\\approx/g, '≈')
      .replace(/\\infty/g, '∞')
      .replace(/\\pi/g, 'π')
      .replace(/\\alpha/g, 'α')
      .replace(/\\beta/g, 'β')
      .replace(/\\gamma/g, 'γ')
      .replace(/\\Delta/g, 'Δ')
      .replace(/\\Sigma/g, 'Σ')
      .replace(/\\sum/g, 'Σ')
      .replace(/\\int/g, '∫')
      .replace(/\\sqrt\{([^}]+)\}/g, '√($1)')
      .replace(/\\\^/g, '^')
      .replace(/\\_/g, '_')
      .replace(/\\,/g, ' ')
      .replace(/\\;/g, ' ')
      .replace(/\\!/g, '')
      .replace(/\\quad/g, '  ')
      .replace(/\\qquad/g, '    ')
      .replace(/\\text\{([^}]+)\}/g, '$1')
      .replace(/\\left/g, '')
      .replace(/\\right/g, '')
      .replace(/\\begin\{[^}]+\}/g, '')
      .replace(/\\end\{[^}]+\}/g, '')
      .replace(/\\\\/g, '\n')
  }
  
  const handleExportPDF = async () => {
    if (!resultRef.current) return
    setExporting(true)
    
    const element = resultRef.current
    const opt = {
      margin: [10, 10, 10, 10],
      filename: `作业批改结果_${new Date().toLocaleDateString()}.pdf`,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true },
      jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
    }
    
    try {
      await html2pdf().set(opt).from(element).save()
    } catch (err) {
      console.error('PDF导出失败:', err)
    } finally {
      setExporting(false)
    }
  }
  
  const onDrop = useCallback((acceptedFiles) => {
    setFiles(prev => [...prev, ...acceptedFiles])
    setError(null)
  }, [])
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'],
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'text/markdown': ['.md'],
      'text/plain': ['.txt'],
    },
  })
  
  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }
  
  const handleGrade = async () => {
    if (files.length === 0) {
      setError('请先上传作业文件')
      return
    }
    
    setError(null)
    setResult(null)
    setProcessing(true)
    setProgress(0)
    setProgressLabel('准备上传...')
    
    const newTaskId = addTask({
      type: 'grader',
      title: `作业批改 - ${files.length}个文件`,
      status: 'running',
      progress: 0,
      progressLabel: '准备上传...',
      files: files.map(f => f.name)
    })
    setTaskId(newTaskId)
    
    try {
      const response = await homeworkAPI.upload(
        files, 
        referenceAnswer, 
        '数学',
        (progress) => {
          setProgress(progress)
          setProgressLabel(`上传中... ${progress}%`)
          updateTask(newTaskId, {
            progress: Math.round(progress * 0.5),
            progressLabel: `上传中... ${progress}%`
          })
        }
      )
      
      setProgress(50)
      setProgressLabel('上传完成，正在智能批改...')
      updateTask(newTaskId, {
        progress: 50,
        progressLabel: '上传完成，正在智能批改...'
      })
      
      const gradingInterval = setInterval(() => {
        setProgress(prev => {
          const next = Math.min(prev + 5, 95)
          setProgressLabel(`智能批改中... ${next}%`)
          updateTask(newTaskId, {
            progress: next,
            progressLabel: `智能批改中... ${next}%`
          })
          return next
        })
      }, 800)
      
      setResult(response)
      clearInterval(gradingInterval)
      setProgress(100)
      setProgressLabel('批改完成')
      
      updateTask(newTaskId, {
        progress: 100,
        progressLabel: '批改完成',
        status: 'completed',
        result: response
      })
    } catch (error) {
      console.error('批改失败:', error)
      const errorMsg = error.response?.data?.detail || error.message || '批改失败，请重试'
      setError(errorMsg)
      updateTask(newTaskId, {
        status: 'failed',
        error: errorMsg
      })
    } finally {
      setProcessing(false)
    }
  }
  
  return (
    <div className="p-6">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center space-x-3 mb-6">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-lg flex items-center justify-center">
              <Upload className="h-5 w-5 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">
                AI 作业批改助手
              </h2>
              <p className="text-sm text-gray-500">拍照上传，智能批改，实时反馈</p>
            </div>
          </div>
          
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-3">
              上传作业文件（支持多张）
            </label>
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all duration-300 ${
                isDragActive
                  ? 'border-blue-500 bg-blue-50 scale-[1.02]'
                  : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
              }`}
            >
              <input {...getInputProps()} />
              <div className="w-16 h-16 bg-gradient-to-br from-blue-100 to-cyan-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Upload className="h-8 w-8 text-blue-500" />
              </div>
              {isDragActive ? (
                <p className="text-blue-600 font-medium">拖拽文件到此处...</p>
              ) : (
                <>
                  <p className="text-gray-700 font-medium">拖拽或点击上传</p>
                  <p className="text-sm text-gray-500 mt-2">
                    支持 PNG、JPG、GIF、PDF、Word、Excel、TXT、MD 格式，可上传多张文件
                  </p>
                </>
              )}
            </div>
            
            {files.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-2">
                {files.map((file, index) => {
                  const fileType = getFileType(file)
                  const IconComponent = FILE_TYPE_ICONS[fileType] || FileText
                  return (
                    <div key={index} className="relative group flex items-center bg-gradient-to-r from-blue-50 to-cyan-50 rounded-lg px-3 py-2 border border-blue-100">
                      <IconComponent className="h-4 w-4 text-blue-400 mr-2" />
                      <span className="text-xs text-gray-600 max-w-[120px] truncate">
                        {file.name}
                      </span>
                      <button
                        onClick={() => removeFile(index)}
                        className="ml-2 text-gray-400 hover:text-red-500 transition-colors"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
          
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-3">
              设置参考答案（可选）
            </label>
            <textarea
              value={referenceAnswer}
              onChange={(e) => setReferenceAnswer(e.target.value)}
              className="w-full border border-gray-300 rounded-xl px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              rows="3"
              placeholder="输入参考答案，有助于更准确的批改"
            />
          </div>
          
          <button
            onClick={handleGrade}
            disabled={processing || files.length === 0}
            className={`w-full py-3.5 px-4 rounded-xl text-white font-medium text-lg transition-all duration-300 ${
              processing || files.length === 0
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 shadow-lg hover:shadow-xl hover:scale-[1.01]'
            }`}
          >
            {processing ? (
              <span className="flex items-center justify-center">
                <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                {progress < 50 ? '上传中...' : '正在批改...'}
              </span>
            ) : '开始批改'}
          </button>
          
          {error && (
            <div className="mt-6 p-4 bg-gradient-to-r from-red-50 to-pink-50 rounded-xl border border-red-200">
              <div className="flex items-center">
                <AlertCircle className="h-5 w-5 text-red-500 mr-2" />
                <p className="text-red-700 font-medium">{error}</p>
              </div>
            </div>
          )}
          
          {result && (
            <div className="mt-8">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-bold flex items-center">
                  <span className="w-1.5 h-6 bg-blue-500 rounded-full mr-3"></span>
                  批改结果
                </h3>
                <button
                  onClick={handleExportPDF}
                  disabled={exporting}
                  className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 text-white rounded-xl hover:from-blue-700 hover:to-cyan-700 transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {exporting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>导出中...</span>
                    </>
                  ) : (
                    <>
                      <Download className="h-4 w-4" />
                      <span>导出PDF</span>
                    </>
                  )}
                </button>
              </div>
              
              <div ref={resultRef}>
                <div className="grid grid-cols-3 gap-4 mb-6">
                  <div className="bg-gradient-to-br from-green-50 to-emerald-50 p-5 rounded-xl border border-green-100 text-center">
                    <p className="text-sm text-gray-600 mb-1">总题数</p>
                    <p className="text-3xl font-bold text-green-600">
                      {result.grading_result?.total_questions || 0}
                    </p>
                  </div>
                  <div className="bg-gradient-to-br from-blue-50 to-cyan-50 p-5 rounded-xl border border-blue-100 text-center">
                    <p className="text-sm text-gray-600 mb-1">正确数</p>
                    <p className="text-3xl font-bold text-blue-600">
                      {result.grading_result?.correct_count || 0}
                    </p>
                  </div>
                  <div className="bg-gradient-to-br from-red-50 to-pink-50 p-5 rounded-xl border border-red-100 text-center">
                    <p className="text-sm text-gray-600 mb-1">错误数</p>
                    <p className="text-3xl font-bold text-red-600">
                      {result.grading_result?.wrong_count || 0}
                    </p>
                  </div>
                </div>
                
                {result.grading_result?.questions && (
                  <div className="space-y-4">
                    {result.grading_result.questions.map((q, idx) => (
                      <div
                        key={idx}
                        className={`border rounded-xl p-5 transition-all duration-300 hover:shadow-md ${
                          q.is_correct ? 'border-green-200 bg-gradient-to-r from-green-50 to-emerald-50' : 'border-red-200 bg-gradient-to-r from-red-50 to-pink-50'
                        }`}
                      >
                        <div className="flex justify-between items-start mb-3">
                          <p className="font-bold text-gray-900 text-lg">
                            第{q.question_number}题
                          </p>
                          <span
                            className={`px-4 py-1.5 rounded-full text-sm font-medium ${
                              q.is_correct
                                ? 'bg-green-200 text-green-800'
                                : 'bg-red-200 text-red-800'
                            }`}
                          >
                            {q.is_correct ? '✓ 正确' : '✗ 错误'}
                          </span>
                        </div>
                        <div className="bg-white/60 rounded-xl p-4 mb-3">
                          <p className="text-gray-900 leading-relaxed">{cleanLatex(q.question_text)}</p>
                        </div>
                        <div className="space-y-2">
                          <p className="text-sm">
                            <span className="font-medium text-gray-600">你的答案：</span>
                            <span className={`font-medium ${q.is_correct ? 'text-green-600' : 'text-red-600'}`}>
                              {cleanLatex(q.student_answer)}
                            </span>
                          </p>
                          {!q.is_correct && (
                            <p className="text-sm">
                              <span className="font-medium text-gray-600">正确答案：</span>
                              <span className="font-medium text-green-600">{cleanLatex(q.correct_answer)}</span>
                            </p>
                          )}
                          {q.explanation && (
                            <div className="bg-white/60 rounded-xl p-4 mt-3">
                              <p className="text-sm">
                                <span className="font-medium text-gray-600">解析：</span>
                                <span className="text-gray-700">{cleanLatex(q.explanation)}</span>
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default HomeworkGrader
