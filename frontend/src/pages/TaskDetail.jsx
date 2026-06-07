import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, FileCheck, Award, Target, AlertCircle, TrendingUp, BookOpen, XCircle, CheckCircle } from 'lucide-react'
import { useTask } from '../context/TaskContext'
import html2pdf from 'html2pdf.js'

const TaskDetail = () => {
  const { taskId } = useParams()
  const navigate = useNavigate()
  const { tasks, removeTask } = useTask()
  const [task, setTask] = useState(null)
  const [exporting, setExporting] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  useEffect(() => {
    const found = tasks.find(t => String(t.id) === String(taskId))
    setTask(found)
  }, [tasks, taskId])

  const handleExportPDF = async () => {
    if (!task?.result) return
    setExporting(true)
    
    const element = document.getElementById('grading-result-detail')
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

  const handleDelete = () => {
    removeTask(taskId)
    navigate('/tasks')
  }

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
      .replace(/\\sqrt\{([^}]+)\}/g, '√($1)')
      .replace(/\\text\{([^}]+)\}/g, '$1')
      .replace(/\\\\/g, '\n')
  }

  const analyzeKnowledgePoints = (questions) => {
    const knowledgePoints = {}
    
    questions.forEach((q, idx) => {
      let category = '其他'
      
      if (q.question_text?.includes('方程') || q.question_text?.includes('函数')) {
        category = '函数与方程'
      } else if (q.question_text?.includes('几何') || q.question_text?.includes('圆') || q.question_text?.includes('三角形')) {
        category = '几何图形'
      } else if (q.question_text?.includes('概率') || q.question_text?.includes('统计')) {
        category = '概率统计'
      } else if (q.question_text?.includes('数列') || q.question_text?.includes('等差') || q.question_text?.includes('等比')) {
        category = '数列'
      } else if (q.question_text?.includes('导数') || q.question_text?.includes('极值')) {
        category = '导数应用'
      } else if (q.question_text?.includes('向量') || q.question_text?.includes('坐标')) {
        category = '向量与坐标'
      } else if (q.question_text?.includes('不等式')) {
        category = '不等式'
      } else if (q.question_text?.includes('三角函数')) {
        category = '三角函数'
      }

      if (!knowledgePoints[category]) {
        knowledgePoints[category] = { total: 0, correct: 0, questions: [] }
      }
      knowledgePoints[category].total++
      if (q.is_correct) knowledgePoints[category].correct++
      knowledgePoints[category].questions.push(idx + 1)
    })

    return knowledgePoints
  }

  const getMasteryLevel = (ratio) => {
    if (ratio >= 0.8) return { level: '优秀', color: 'text-green-600', bg: 'bg-green-100', desc: '掌握良好，继续保持' }
    if (ratio >= 0.6) return { level: '良好', color: 'text-blue-600', bg: 'bg-blue-100', desc: '基本掌握，还需巩固' }
    if (ratio >= 0.4) return { level: '一般', color: 'text-yellow-600', bg: 'bg-yellow-100', desc: '需要加强练习' }
    return { level: '薄弱', color: 'text-red-600', bg: 'bg-red-100', desc: '重点关注，多加练习' }
  }

  if (!task) {
    return (
      <div className="p-6">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
            <AlertCircle className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">未找到任务详情</p>
            <button
              onClick={() => navigate('/tasks')}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              返回任务列表
            </button>
          </div>
        </div>
      </div>
    )
  }

  const result = task.result
  const gradingResult = result?.grading_result
  const knowledgePoints = gradingResult?.questions ? analyzeKnowledgePoints(gradingResult.questions) : {}

  return (
    <div className="p-6">
      <div className="max-w-4xl mx-auto">
        {/* 顶部导航 */}
        <div className="flex items-center space-x-4 mb-6">
          <button
            onClick={() => navigate('/tasks')}
            className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
            <span>返回任务列表</span>
          </button>
          <div className="flex-1" />
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="px-4 py-2 text-red-600 border border-red-200 rounded-xl hover:bg-red-50 transition-colors"
          >
            删除任务
          </button>
          <button
            onClick={handleExportPDF}
            disabled={exporting || !gradingResult}
            className="px-4 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {exporting ? '导出中...' : '导出PDF'}
          </button>
        </div>

        {/* 任务标题 */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-xl flex items-center justify-center">
              <FileCheck className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">{task.title}</h1>
              <p className="text-sm text-gray-500">
                {task.createdAt ? new Date(task.createdAt).toLocaleString('zh-CN') : ''}
                {task.files && ` | ${task.files.length} 个文件`}
              </p>
            </div>
          </div>
        </div>

        {gradingResult && (
          <div id="grading-result-detail">
            {/* 总体评分 */}
            <div className="grid grid-cols-4 gap-4 mb-6">
              <div className="bg-gradient-to-br from-blue-500 to-cyan-500 rounded-xl p-5 text-white text-center">
                <div className="text-sm opacity-80 mb-1">总分</div>
                <div className="text-4xl font-bold">{gradingResult.score}</div>
              </div>
              <div className="bg-gradient-to-br from-green-500 to-emerald-500 rounded-xl p-5 text-white text-center">
                <div className="text-sm opacity-80 mb-1">总题数</div>
                <div className="text-4xl font-bold">{gradingResult.total_questions}</div>
              </div>
              <div className="bg-gradient-to-br from-teal-500 to-cyan-500 rounded-xl p-5 text-white text-center">
                <div className="text-sm opacity-80 mb-1">正确数</div>
                <div className="text-4xl font-bold">{gradingResult.correct_count}</div>
              </div>
              <div className="bg-gradient-to-br from-orange-500 to-red-500 rounded-xl p-5 text-white text-center">
                <div className="text-sm opacity-80 mb-1">错误数</div>
                <div className="text-4xl font-bold">{gradingResult.wrong_count}</div>
              </div>
            </div>

            {/* 知识点掌握评估 */}
            <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
              <div className="flex items-center space-x-2 mb-4">
                <TrendingUp className="h-5 w-5 text-purple-600" />
                <h2 className="text-lg font-bold text-gray-900">知识点掌握评估</h2>
              </div>
              
              <div className="space-y-4">
                {Object.entries(knowledgePoints).map(([category, data]) => {
                  const ratio = data.correct / data.total
                  const mastery = getMasteryLevel(ratio)
                  return (
                    <div key={category} className="flex items-center space-x-4 p-4 bg-gray-50 rounded-xl">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2">
                          <BookOpen className="h-4 w-4 text-gray-400" />
                          <span className="font-medium text-gray-700">{category}</span>
                        </div>
                        <div className="text-sm text-gray-500 mt-1">
                          题目 {data.questions.join(', ')}
                        </div>
                      </div>
                      <div className="w-48">
                        <div className="flex items-center justify-between text-sm mb-1">
                          <span className="text-gray-500">正确率</span>
                          <span className={mastery.color}>{Math.round(ratio * 100)}%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full transition-all ${
                              ratio >= 0.8 ? 'bg-green-500' :
                              ratio >= 0.6 ? 'bg-blue-500' :
                              ratio >= 0.4 ? 'bg-yellow-500' : 'bg-red-500'
                            }`}
                            style={{ width: `${ratio * 100}%` }}
                          />
                        </div>
                      </div>
                      <div className={`px-3 py-1.5 rounded-full text-sm font-medium ${mastery.bg} ${mastery.color}`}>
                        {mastery.level}
                      </div>
                    </div>
                  )
                })}
              </div>

              {/* 总体评价 */}
              <div className="mt-6 p-4 bg-gradient-to-r from-purple-50 to-pink-50 rounded-xl border border-purple-100">
                <div className="flex items-start space-x-3">
                  <Award className="h-5 w-5 text-purple-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-gray-900">学习建议</p>
                    <p className="text-sm text-gray-600 mt-1">
                      {gradingResult.score >= 80 
                        ? '整体表现优秀！继续保持，可尝试更有挑战性的题目提升能力。'
                        : gradingResult.score >= 60
                          ? '表现良好，但仍有提升空间。建议针对错题进行专项练习，巩固薄弱知识点。'
                          : '需要加强学习。建议回顾基础知识，多做练习，重点关注错误题目涉及的知识点。'}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* 详细批改结果 */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center space-x-2 mb-4">
                <Target className="h-5 w-5 text-blue-600" />
                <h2 className="text-lg font-bold text-gray-900">详细批改结果</h2>
              </div>
              
              <div className="space-y-4">
                {gradingResult.questions.map((q, idx) => (
                  <div
                    key={idx}
                    className={`border rounded-xl p-5 transition-all ${
                      q.is_correct 
                        ? 'border-green-200 bg-gradient-to-r from-green-50 to-emerald-50' 
                        : 'border-red-200 bg-gradient-to-r from-red-50 to-pink-50'
                    }`}
                  >
                    <div className="flex justify-between items-start mb-3">
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-gray-900">第{q.question_number}题</span>
                        {q.is_correct ? (
                          <span className="px-3 py-1 bg-green-200 text-green-800 rounded-full text-sm font-medium flex items-center space-x-1">
                            <CheckCircle className="h-3 w-3" />
                            <span>正确</span>
                          </span>
                        ) : (
                          <span className="px-3 py-1 bg-red-200 text-red-800 rounded-full text-sm font-medium flex items-center space-x-1">
                            <XCircle className="h-3 w-3" />
                            <span>错误</span>
                          </span>
                        )}
                      </div>
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
            </div>
          </div>
        )}

        {!gradingResult && (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
            <AlertCircle className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">暂无批改结果</p>
          </div>
        )}

        {/* 删除确认弹窗 */}
        {showDeleteConfirm && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4">
              <h3 className="text-lg font-bold text-gray-900 mb-2">删除任务</h3>
              <p className="text-gray-600 mb-6">确定要删除这个任务吗？删除后无法恢复。</p>
              <div className="flex space-x-3">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-xl text-gray-700 hover:bg-gray-50 transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={handleDelete}
                  className="flex-1 px-4 py-2 bg-red-600 text-white rounded-xl hover:bg-red-700 transition-colors"
                >
                  确认删除
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default TaskDetail
