import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, X, FileText, Loader2, AlertCircle } from 'lucide-react'
import { homeworkAPI, getErrorMessage } from '../utils/api'
import { useAuth } from '../context/AuthContext'
import { useTask, estimateProgress } from '../context/TaskContext'
import { useToast } from './Toast'

/*
 * 上传并批改弹窗（需求：班级作业详情页内直接批改，不跳转 /grader）
 *
 * 复用批改作业页的同一条上传管线（homeworkAPI.uploadWithContext）：
 *   - 传入 assignmentId/memberId/submissionId 时，批改结果直接计入班级作业与该学生
 *   - 提交后进度在全局任务抽屉跟踪；完成/失败时通过 onDone 回调刷新列表
 *
 * <GradeUploadModal
 *   classId={classId} homeworkId={homeworkId} assignmentId={...}
 *   memberId={...} submissionId={...} studentName={...}   // 均可选，定位到某学生
 *   homeworkTitle={homework.title}
 *   onClose={() => setUploadCtx(null)}
 *   onDone={() => reload()}                                // 提交成功或批改结束时刷新
 * />
 */

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

const FILE_TYPE_ICON = { image: '🖼️', pdf: '📕', word: '📘', text: '📄', unknown: '📎' }

const GradeUploadModal = ({
  classId,
  homeworkId,
  assignmentId,
  memberId,
  submissionId,
  studentName,
  homeworkTitle,
  onClose,
  onDone,
}) => {
  const { addTask, tasks } = useTask()
  const { addToast } = useToast()
  const { user } = useAuth()
  const [files, setFiles] = useState([])
  const [referenceAnswer, setReferenceAnswer] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [error, setError] = useState(null)
  const [taskId, setTaskId] = useState(null)
  const [doneNotified, setDoneNotified] = useState(false)

  const contextLabel = [homeworkTitle, studentName].filter(Boolean).join(' · ')

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

  const removeFile = (index) => setFiles(prev => prev.filter((_, i) => i !== index))

  const handleGrade = async () => {
    if (files.length === 0) {
      setError('请先上传作业文件')
      return
    }
    setError(null)
    setSubmitting(true)
    setUploadProgress(0)
    try {
      const resp = await homeworkAPI.uploadWithContext(files, {
        referenceAnswer,
        subject: user?.subject || '',
        assignmentId: assignmentId || undefined,
        submissionId: submissionId || undefined,
        studentName: studentName || undefined,
        memberId: memberId || undefined,
        onProgress: setUploadProgress,
      })
      const who = studentName ? `${studentName} - ` : ''
      const newTaskId = addTask({
        type: 'grader',
        title: `作业批改 - ${who}${files.length}个文件`,
        status: 'running',
        progress: estimateProgress(resp.progress_stage, resp.status),
        progressLabel: resp.progress_stage || '排队中',
        files: files.map(f => f.name),
        submissionId: resp.submission_id,
        classId,
        homeworkId,
      })
      setTaskId(newTaskId)
      setFiles([])
      addToast('已提交批改，进度可在右上角任务里查看', 'success')
      if (onDone) onDone()
    } catch (err) {
      setError(getErrorMessage(err, '提交失败，请重试'))
    } finally {
      setSubmitting(false)
    }
  }

  // 任务结束（完成或失败）时通知外层刷新一次
  const currentTask = useMemo(() => tasks.find(t => t.id === taskId), [tasks, taskId])
  useEffect(() => {
    if (!currentTask || currentTask.status === 'running' || doneNotified) return
    setDoneNotified(true)
    if (onDone) onDone()
  }, [currentTask, doneNotified, onDone])

  const processing = submitting || currentTask?.status === 'running'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40" onClick={processing ? undefined : onClose} />
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div>
            <h3 className="text-base font-semibold text-gray-900">上传并批改</h3>
            {contextLabel && <p className="text-xs text-gray-500 mt-0.5">{contextLabel}</p>}
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={processing}
            className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-lg disabled:opacity-40"
            aria-label="关闭"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="px-5 py-4 space-y-4">
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
              isDragActive ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-blue-300 hover:bg-gray-50'
            }`}
          >
            <input {...getInputProps()} />
            <Upload className="h-8 w-8 mx-auto text-gray-400" />
            <p className="mt-2 text-sm text-gray-600">拖拽作业文件到这里，或点击选择</p>
            <p className="mt-1 text-xs text-gray-400">支持图片 / PDF / Word / txt / md，单个文件不超过 10MB</p>
          </div>

          {files.length > 0 && (
            <ul className="space-y-2">
              {files.map((f, i) => (
                <li key={`${f.name}-${i}`} className="flex items-center justify-between px-3 py-2 bg-gray-50 rounded-lg text-sm">
                  <span className="flex items-center gap-2 text-gray-700 min-w-0">
                    <span>{FILE_TYPE_ICON[getFileType(f)]}</span>
                    <FileText className="h-4 w-4 text-gray-400 shrink-0" />
                    <span className="truncate">{f.name}</span>
                    <span className="text-xs text-gray-400 shrink-0">{(f.size / 1024).toFixed(0)}KB</span>
                  </span>
                  <button type="button" onClick={() => removeFile(i)} className="p-1 text-gray-400 hover:text-red-500" aria-label="移除">
                    <X className="h-4 w-4" />
                  </button>
                </li>
              ))}
            </ul>
          )}

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">设置参考答案（可选）</label>
            <textarea
              value={referenceAnswer}
              onChange={e => setReferenceAnswer(e.target.value)}
              rows={3}
              placeholder="输入参考答案，有助于更准确的批改；留空则使用本次作业已设置的参考答案"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {error && (
            <p className="flex items-start gap-1.5 text-sm text-red-600">
              <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
              {error}
            </p>
          )}

          {processing && (
            <p className="flex items-center gap-2 text-sm text-blue-600">
              <Loader2 className="h-4 w-4 animate-spin" />
              {submitting ? `上传中... ${uploadProgress}%` : `批改中：${currentTask?.progressLabel || '处理中'}`}
            </p>
          )}
        </div>

        <div className="flex items-center justify-end gap-3 px-5 py-4 border-t border-gray-100">
          <button
            type="button"
            onClick={onClose}
            disabled={processing}
            className="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50"
          >
            关闭
          </button>
          <button
            type="button"
            onClick={handleGrade}
            disabled={processing || files.length === 0}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50 inline-flex items-center"
          >
            {processing ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Upload className="h-4 w-4 mr-1.5" />}
            {submitting ? '上传中...' : '开始批改'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default GradeUploadModal
