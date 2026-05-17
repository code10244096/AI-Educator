import React, { useState, useCallback, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, X, FileImage } from 'lucide-react'
import { homeworkAPI } from '../utils/api'
import PageBackground from '../components/PageBackground'

const HomeworkGrader = () => {
  const [files, setFiles] = useState([])
  const [referenceAnswer, setReferenceAnswer] = useState('')
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState(null)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    setIsVisible(true)
  }, [])
  
  const onDrop = useCallback((acceptedFiles) => {
    setFiles(prev => [...prev, ...acceptedFiles])
  }, [])
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.gif'],
    },
  })
  
  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }
  
  const handleGrade = async () => {
    if (files.length === 0) {
      alert('请上传作业图片')
      return
    }
    
    setLoading(true)
    setProgress(0)
    
    try {
      // 模拟进度
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval)
            return 90
          }
          return prev + 10
        })
      }, 300)
      
      const response = await homeworkAPI.upload(files, referenceAnswer)
      
      clearInterval(progressInterval)
      setProgress(100)
      setResult(response)
    } catch (error) {
      console.error('批改失败:', error)
      alert('批改失败，请重试')
    } finally {
      setLoading(false)
    }
  }
  
  return (
      <PageBackground gradient="grader">
        <div className={`max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 pb-12 transition-all duration-1000 ${
          isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-12'
        }`}>
          <div className="bg-white/90 backdrop-blur-md rounded-2xl shadow-xl p-8 border border-white/20">
          <div className="flex items-center space-x-3 mb-6">
            <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-xl flex items-center justify-center shadow-lg">
              <Upload className="h-6 w-6 text-white" />
            </div>
            <div>
              <h2 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent">
                AI 作业批改助手
              </h2>
              <p className="text-sm text-gray-600">拍照上传，智能批改，实时反馈</p>
            </div>
          </div>
          
          {/* 上传区域 */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-3">
            上传作业照片（支持多张）
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
                  支持 PNG、JPG、GIF 格式，可上传多张图片
                </p>
              </>
            )}
          </div>
          
          {/* 文件列表 */}
          {files.length > 0 && (
            <div className="mt-4 grid grid-cols-4 gap-4">
              {files.map((file, index) => (
                <div key={index} className="relative group">
                  <div className="aspect-square bg-gradient-to-br from-blue-50 to-cyan-50 rounded-xl flex items-center justify-center border border-blue-100">
                    <FileImage className="h-10 w-10 text-blue-400" />
                  </div>
                  <button
                    onClick={() => removeFile(index)}
                    className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1.5 hover:bg-red-600 shadow-lg opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <X className="h-3 w-3" />
                  </button>
                  <p className="text-xs text-gray-600 mt-2 truncate text-center">
                    {file.name}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
        
        {/* 参考答案 */}
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
        
        {/* 批改按钮 */}
        <button
          onClick={handleGrade}
          disabled={loading || files.length === 0}
          className={`w-full py-3.5 px-4 rounded-xl text-white font-medium text-lg transition-all duration-300 ${
            loading || files.length === 0
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 shadow-lg hover:shadow-xl hover:scale-[1.01]'
          }`}
        >
          {loading ? '正在批改...' : '开始批改'}
        </button>
        
        {/* 进度条 */}
        {loading && (
          <div className="mt-6">
            <div className="flex justify-between text-sm text-gray-600 mb-2">
              <span className="font-medium">批改进度</span>
              <span className="text-blue-600 font-medium">{progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
              <div
                className="bg-gradient-to-r from-blue-500 to-cyan-500 h-full rounded-full transition-all duration-500 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}
        
        {/* 批改结果 */}
        {result && (
          <div className="mt-8">
            <h3 className="text-xl font-bold mb-6 flex items-center">
              <span className="w-1.5 h-6 bg-blue-500 rounded-full mr-3"></span>
              批改结果
            </h3>
            
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="bg-gradient-to-br from-green-50 to-emerald-50 p-5 rounded-xl border border-green-100 text-center">
                <p className="text-sm text-gray-600 mb-1">总题数</p>
                <p className="text-3xl font-bold text-green-600">
                  {result.grading_result.total_questions || 0}
                </p>
              </div>
              <div className="bg-gradient-to-br from-blue-50 to-cyan-50 p-5 rounded-xl border border-blue-100 text-center">
                <p className="text-sm text-gray-600 mb-1">正确数</p>
                <p className="text-3xl font-bold text-blue-600">
                  {result.grading_result.correct_count || 0}
                </p>
              </div>
              <div className="bg-gradient-to-br from-red-50 to-pink-50 p-5 rounded-xl border border-red-100 text-center">
                <p className="text-sm text-gray-600 mb-1">错误数</p>
                <p className="text-3xl font-bold text-red-600">
                  {result.grading_result.wrong_count || 0}
                </p>
              </div>
            </div>
            
            {result.grading_result.questions && (
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
                      <p className="text-gray-900 leading-relaxed">{q.question_text}</p>
                    </div>
                    <div className="space-y-2">
                      <p className="text-sm">
                        <span className="font-medium text-gray-600">你的答案：</span>
                        <span className={`font-medium ${q.is_correct ? 'text-green-600' : 'text-red-600'}`}>
                          {q.student_answer}
                        </span>
                      </p>
                      {!q.is_correct && (
                        <p className="text-sm">
                          <span className="font-medium text-gray-600">正确答案：</span>
                          <span className="font-medium text-green-600">{q.correct_answer}</span>
                        </p>
                      )}
                      {q.explanation && (
                        <div className="bg-white/60 rounded-xl p-4 mt-3">
                          <p className="text-sm">
                            <span className="font-medium text-gray-600">解析：</span>
                            <span className="text-gray-700">{q.explanation}</span>
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
        </div>
      </div>
    </PageBackground>
  )
}

export default HomeworkGrader
