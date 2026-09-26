import React, { useState, useCallback, useEffect, useMemo } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import {
  Upload, X, FileText, File, AlertCircle, Loader2, CheckCircle, History,
  RotateCcw, Trash2, Eye, Beaker, RefreshCw,
} from 'lucide-react'
import { homeworkAPI, getErrorMessage } from '../utils/api'
import { useTask, estimateProgress } from '../context/TaskContext'
import { clearHomeworkCache } from '../services/homeworkService'
import { useToast } from '../components/Toast'
import ConfirmDialog from '../components/ConfirmDialog'

const MAX_FILE_SIZE = 10 * 1024 * 1024
const ALLOWED_EXTS = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'pdf', 'docx', 'txt', 'md']

const getFileType = (file) => {
  const ext = file.name.split('.').pop().toLowerCase()
  if (['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'].includes(ext)) return 'image'
  if (ext === 'pdf') return 'pdf'
  if (ext === 'docx') return 'word'
  if (['md', 'txt'].includes(ext)) return 'text'
  return 'unknown'
}

const STATUS_BADGE = {
  processing: { label: '批改中', cls: 'bg-blue-100 text-blue-700' },
  completed: { label: '已完成', cls: 'bg-green-100 text-green-700' },
  failed: { label: '失败', cls: 'bg-red-100 text-red-700' },
  pending: { label: '待批改', cls: 'bg-orange-100 text-orange-700' },
}

const HomeworkGrader = () => {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { tasks, addTask } = useTask()
  const { addToast } = useToast()
  const [files, setFiles] = useState([])
  const [referenceAnswer, setReferenceAnswer] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [error, setError] = useState(null)
  const [taskId, setTaskId] = useState(null)
  const [finishedResult, setFinishedResult] = useState(null)
  const [history, setHistory] = useState({ items: [], total: 0 })
  const [historyLoading, setHistoryLoading] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)

  const gradeContext = useMemo(() => ({
    classId: searchParams.get('classId'),
    homeworkId: searchParams.get('homeworkId'),
    submissionId: searchParams.get('submissionId'),
    studentName: searchParams.get('studentName'),
    assignmentId: searchParams.get('assignmentId'),
    datasetId: searchParams.get('dataset'),
  }), [searchParams])

  const currentTask = tasks.find(t => t.id === taskId)
  const processing = submitting || currentTask?.status === 'running'

  const loadHistory = useCallback(() => {
    setHistoryLoading(true)
    homeworkAPI.listSubmissions({ limit: 10 })
      .then(setHistory)
      .catch(() => {})
      .finally(() => setHistoryLoading(false))
  }, [])

  useEffect(() => { loadHistory() }, [loadHistory])

  // 当前任务结束后拉取结果并刷新记录
  useEffect(() => {
    if (!currentTask || currentTask.status === 'running') return
    loadHistory()
    if (currentTask.status === 'completed' && currentTask.submissionId && finishedResult?.id !== currentTask.submissionId) {
      homeworkAPI.getResult(currentTask.submissionId).then(setFinishedResult).catch(() => {})
      if (gradeContext.classId && gradeContext.homeworkId) {
        clearHomeworkCache(gradeContext.classId, gradeContext.homeworkId)
      }
    }
    if (currentTask.status === 'failed') {
      setError(currentTask.error || '批改失败，请重试')
    }
  }, [currentTask?.status]) // eslint-disable-line react-hooks/exhaustive-deps

  // 有进行中的记录时，定时刷新列表
  useEffect(() => {
    if (!history.items.some(i => i.status === 'processing')) return
    const timer = setInterval(loadHistory, 4000)
    return () => clearInterval(timer)
  }, [history, loadHistory])

  const onDrop = useCallback((acceptedFiles, rejections) => {
    const valid = []
    const problems = []
    acceptedFiles.forEach(f => {
      const ext = f.name.split('.').pop().toLowerCase()
      if (!ALLOWED_EXTS.includes(ext)) problems.push(`${f.name}：不支持的格式`)
      else if (f.size > MAX_FILE_SIZE) problems.push(`${f.name}：超过 10MB`)
      else valid.push(f)
    })
    rejections?.forEach(r => problems.push(`${r.file.name}：不支持的格式`))
    setFiles(prev => [...prev, ...valid])
    setError(problems.length ? problems.join('；') : null)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'],
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/markdown': ['.md'],
      'text/plain': ['.txt', '.md'],
    },
  })

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const startTask = (resp, title, fileNames) => {
    const newTaskId = addTask({
      type: 'grader',
      title,
      status: 'running',
      progress: estimateProgress(resp.progress_stage, resp.status),
      progressLabel: resp.progress_stage || '排队中',
      files: fileNames,
      submissionId: resp.submission_id,
      classId: gradeContext.classId,
      homeworkId: gradeContext.homeworkId,
    })
    setTaskId(newTaskId)
    addToast('已提交批改任务，可离开本页，完成后在「我的任务」查看', 'success')
    loadHistory()
  }

  const handleGrade = async () => {
    if (files.length === 0) {
      setError('请先上传作业文件')
      return
    }
    setError(null)
    setFinishedResult(null)
    setSubmitting(true)
    setUploadProgress(0)
    try {
      const resp = await homeworkAPI.uploadWithContext(files, {
        referenceAnswer,
        subject: '数学',
        assignmentId: gradeContext.assignmentId,
        submissionId: gradeContext.submissionId,
        studentName: gradeContext.studentName,
        onProgress: setUploadProgress,
      })
      const who = gradeContext.studentName ? `${gradeContext.studentName} - ` : ''
      startTask(resp, `作业批改 - ${who}${files.length}个文件`, files.map(f => f.name))
      setFiles([])
    } catch (err) {
      setError(getErrorMessage(err, '提交失败，请重试'))
    } finally {
      setSubmitting(false)
    }
  }

  const handleGradeDataset = async () => {
    setError(null)
    setFinishedResult(null)
    setSubmitting(true)
    try {
      const resp = await homeworkAPI.gradeDataset(gradeContext.datasetId, {
        assignmentId: gradeContext.assignmentId,
        submissionId: gradeContext.submissionId,
        studentName: gradeContext.studentName,
        classId: gradeContext.classId,
        homeworkId: gradeContext.homeworkId,
      })
      startTask(resp, `测试集批改 - ${resp.dataset_title || gradeContext.datasetId}`, [resp.dataset_filename].filter(Boolean))
    } catch (err) {
      setError(getErrorMessage(err, '提交失败，请重试'))
    } finally {
      setSubmitting(false)
    }
  }

  const handleRetry = async (item) => {
    try {
      const resp = await homeworkAPI.retry(item.id)
      const newTaskId = addTask({
        type: 'grader',
        title: `重新批改 - ${item.student_name || `#${item.id}`}`,
        status: 'running',
        progress: 5,
        progressLabel: resp.progress_stage || '排队中',
        files: item.file_names,
        submissionId: item.id,
      })
      setTaskId(newTaskId)
      setFinishedResult(null)
      setError(null)
      loadHistory()
    } catch (err) {
      addToast(getErrorMessage(err, '重新批改失败'), 'error')
    }
  }

  const handleDelete = async () => {
    try {
      await homeworkAPI.deleteSubmission(deleteTarget.id)
      addToast('批改记录已删除', 'success')
      loadHistory()
    } catch (err) {
      addToast(getErrorMessage(err, '删除失败'), 'error')
    } finally {
      setDeleteTarget(null)
    }
  }

  const contextBanner = gradeContext.studentName && (
    <div className="mb-4 p-3 bg-blue-50 border border-blue-100 rounded-xl text-sm text-blue-800">
      正在为 <strong>{gradeContext.studentName}</strong> 批改作业
      {gradeContext.classId && `（${gradeContext.classId} / 作业 #${gradeContext.homeworkId}）`}
      <span className="ml-1 text-blue-600">，将使用该作业的参考答案（如有）</span>
    </div>
  )

  const progressValue = submitting
    ? Math.round(uploadProgress * 0.05)
    : currentTask?.progress ?? 0
  const progressLabel = submitting
    ? `上传中... ${uploadProgress}%`
    : currentTask?.progressLabel || '处理中'

  return (
    <div className="p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center space-x-3 mb-6">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-lg flex items-center justify-center">
              <Upload className="h-5 w-5 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">AI 作业批改助手</h2>
              <p className="text-sm text-gray-500">拍照上传，智能批改，结果自动保存</p>
            </div>
          </div>

          {contextBanner}

          {gradeContext.datasetId && (
            <div className="mb-6 p-4 bg-purple-50 border border-purple-100 rounded-xl flex items-center justify-between gap-3">
              <p className="text-sm text-purple-800 flex items-center">
                <Beaker className="h-4 w-4 mr-2" />
                该学生有 dataset 测试集作业（#{gradeContext.datasetId}），可直接用测试数据批改
              </p>
              <button
                onClick={handleGradeDataset}
                disabled={processing}
                className="shrink-0 px-4 py-2 bg-purple-600 text-white rounded-lg text-sm hover:bg-purple-700 disabled:opacity-50"
              >
                使用测试数据批改
              </button>
            </div>
          )}

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
                    支持 PNG、JPG、GIF、WEBP、PDF、Word(.docx)、TXT、MD 格式，单个文件不超过 10MB
                  </p>
                </>
              )}
            </div>

            {files.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-2">
                {files.map((file, index) => {
                  const IconComponent = getFileType(file) === 'text' ? File : FileText
                  return (
                    <div key={index} className="relative group flex items-center bg-gradient-to-r from-blue-50 to-cyan-50 rounded-lg px-3 py-2 border border-blue-100">
                      <IconComponent className="h-4 w-4 text-blue-400 mr-2" />
                      <span className="text-xs text-gray-600 max-w-[160px] truncate">{file.name}</span>
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
              placeholder={gradeContext.assignmentId ? '留空则使用该作业布置时填写的参考答案' : '输入参考答案，有助于更准确的批改'}
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
                {submitting ? '上传中...' : '正在批改...'}
              </span>
            ) : '开始批改'}
          </button>

          {processing && (
            <div className="mt-4">
              <div className="flex justify-between text-sm text-gray-600 mb-1">
                <span>{progressLabel}</span>
                <span>{progressValue}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full transition-all duration-500"
                  style={{ width: `${Math.max(progressValue, 3)}%` }}
                />
              </div>
              <p className="text-xs text-gray-400 mt-2">
                AI 识别与批改每步约需 20-60 秒，多张图片可能需要几分钟。任务在后台运行，可以离开本页。
              </p>
            </div>
          )}

          {error && (
            <div className="mt-6 p-4 bg-gradient-to-r from-red-50 to-pink-50 rounded-xl border border-red-200">
              <div className="flex items-center">
                <AlertCircle className="h-5 w-5 text-red-500 mr-2 shrink-0" />
                <p className="text-red-700 font-medium">{error}</p>
              </div>
            </div>
          )}

          {finishedResult && currentTask?.status === 'completed' && (
            <div className="mt-8 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl p-8 text-white text-center">
              <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="h-8 w-8" />
              </div>
              <h3 className="text-xl font-bold mb-2">批改完成</h3>
              <p className="text-white/90 mb-1">
                得分 <span className="text-2xl font-bold">{finishedResult.score ?? '-'}</span>
                {' '}· 共 {finishedResult.grading_result?.total_questions ?? '-'} 题 · 错 {finishedResult.wrong_count ?? 0} 题
              </p>
              <p className="text-white/70 text-sm mb-6">结果已保存，错题已同步到错题本</p>
              <div className="flex justify-center gap-3">
                <button
                  onClick={() => navigate(`/tasks/sub-${finishedResult.id}`)}
                  className="px-6 py-3 bg-white text-blue-600 rounded-xl font-medium hover:bg-blue-50 transition-colors"
                >
                  查看详细结果
                </button>
                {finishedResult.class_slug && finishedResult.homework_id && (
                  <button
                    onClick={() => navigate(`/class/${finishedResult.class_slug}/homework/${finishedResult.homework_id}`)}
                    className="px-6 py-3 bg-white/20 text-white rounded-xl font-medium hover:bg-white/30 transition-colors"
                  >
                    返回班级作业
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl border border-gray-200">
          <div className="p-5 border-b border-gray-200 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <History className="h-5 w-5 text-gray-500" />
              <h3 className="text-lg font-semibold text-gray-900">最近批改记录</h3>
              <span className="text-sm text-gray-400">共 {history.total} 条</span>
            </div>
            <button onClick={loadHistory} className="p-2 text-gray-400 hover:text-blue-600 rounded-lg" title="刷新">
              <RefreshCw className={`h-4 w-4 ${historyLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
          {history.items.length === 0 ? (
            <p className="p-8 text-center text-sm text-gray-400">还没有批改记录</p>
          ) : (
            <div className="divide-y divide-gray-100">
              {history.items.map(item => {
                const badge = STATUS_BADGE[item.status] || STATUS_BADGE.pending
                return (
                  <div key={item.id} className="px-5 py-3 flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium text-gray-900">
                          {item.student_name || `批改 #${item.id}`}
                        </span>
                        {item.assignment_title && (
                          <span className="text-xs text-gray-500">《{item.assignment_title}》</span>
                        )}
                        <span className={`px-2 py-0.5 text-xs rounded-full ${badge.cls}`}>{badge.label}</span>
                        {item.status === 'completed' && (
                          <span className="text-sm font-bold text-blue-600">{item.score} 分</span>
                        )}
                      </div>
                      <p className="text-xs text-gray-400 mt-0.5 truncate">
                        {item.submit_time || ''} · {(item.file_names || []).join('、') || `${item.file_count} 个文件`}
                        {item.status === 'processing' && ` · ${item.progress_stage || '处理中'}`}
                        {item.status === 'failed' && <span className="text-red-500"> · {item.error_message}</span>}
                      </p>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      {item.status === 'completed' && (
                        <button onClick={() => navigate(`/tasks/sub-${item.id}`)} className="p-2 text-gray-400 hover:text-blue-600 rounded-lg" title="查看结果">
                          <Eye className="h-4 w-4" />
                        </button>
                      )}
                      {item.status !== 'processing' && (
                        <button onClick={() => handleRetry(item)} className="p-2 text-gray-400 hover:text-blue-600 rounded-lg" title="重新批改">
                          <RotateCcw className="h-4 w-4" />
                        </button>
                      )}
                      {item.status !== 'processing' && (
                        <button onClick={() => setDeleteTarget(item)} className="p-2 text-gray-400 hover:text-red-600 rounded-lg" title="删除">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      <ConfirmDialog
        isOpen={!!deleteTarget}
        title="删除批改记录"
        message="删除后该批改结果以及同步到错题本的错题都将被移除，确定删除吗？"
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
        confirmText="确认删除"
        cancelText="再想想"
      />
    </div>
  )
}

export default HomeworkGrader
