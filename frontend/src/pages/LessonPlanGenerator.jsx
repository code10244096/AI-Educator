import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  FileDown, FileText, Download, History, Trash2, Edit, Save, X, Loader2, Search, RefreshCw,
} from 'lucide-react'
import { lessonPlanAPI, getErrorMessage } from '../utils/api'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import { useTask, estimateProgress } from '../context/TaskContext'
import { useToast } from '../components/Toast'
import ConfirmDialog from '../components/ConfirmDialog'
import PageBackground from '../components/PageBackground'
import { formatServerTime } from '../utils/time'
import 'katex/dist/katex.min.css'
import html2pdf from 'html2pdf.js'

const plainPreview = (text) => (text || '')
  .replace(/\$/g, '')
  .replace(/[#>*`|]+/g, ' ')
  .replace(/\s+/g, ' ')
  .trim()

const splitPlan = (markdown) => {
  const text = markdown || ''
  const chunks = text.split(/\n(?=## )/)
  const sections = []
  chunks.forEach((chunk) => {
    if (!chunk.startsWith('## ')) return
    const nl = chunk.indexOf('\n')
    const heading = (nl === -1 ? chunk : chunk.slice(0, nl)).replace(/^##\s+/, '').trim()
    const body = nl === -1 ? '' : chunk.slice(nl + 1).replace(/\s+$/, '')
    sections.push({ heading, body })
  })
  return sections
}

const joinPlan = (title, sections) => {
  const head = `# ${title || '教案'}`
  const body = sections.map(s => `## ${s.heading}\n${(s.body || '').trim()}`).join('\n\n')
  return `${head}\n\n${body}`.trim() + '\n'
}

const sectionLabel = (heading) => {
  if (heading.includes('目标')) return '目标'
  if (heading.includes('过程')) return '过程'
  return heading.replace(/^\d+(?:\.\d+)*\.?\s*/, '')
}

const STATUS_BADGE = {
  processing: { label: '生成中', cls: 'bg-blue-100 text-blue-700' },
  completed: { label: '已完成', cls: 'bg-green-100 text-green-700' },
  failed: { label: '失败', cls: 'bg-red-100 text-red-700' },
}

const LessonPlanGenerator = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const [formData, setFormData] = useState({
    title: '',
    period: '1 课时',
    studentLevel: '中等',
    requirements: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)
  const [isVisible, setIsVisible] = useState(false)
  const [elapsedTime, setElapsedTime] = useState(0)
  const [error, setError] = useState(null)
  const [currentTaskId, setCurrentTaskId] = useState(null)
  const [exporting, setExporting] = useState(false)
  const [editing, setEditing] = useState(false)
  const [editContent, setEditContent] = useState('')
  const [editTitle, setEditTitle] = useState('')
  const [saving, setSaving] = useState(false)
  const [plans, setPlans] = useState({ items: [], total: 0 })
  const [plansLoading, setPlansLoading] = useState(true)
  const [keyword, setKeyword] = useState('')
  const [appliedKeyword, setAppliedKeyword] = useState('')
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [markdownMode, setMarkdownMode] = useState(false)
  const [sections, setSections] = useState([])

  const previewRef = useRef(null)
  const { tasks, addTask } = useTask()
  const { addToast } = useToast()

  const currentTask = tasks.find(t => t.id === currentTaskId)
  const loading = submitting || currentTask?.status === 'running'

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

  const loadPlans = useCallback((kw = keyword) => {
    const q = typeof kw === 'string' ? kw.trim() : ''
    setAppliedKeyword(q)
    setPlansLoading(true)
    lessonPlanAPI.list({ limit: 50, keyword: q || undefined })
      .then(setPlans)
      .catch(() => {})
      .finally(() => setPlansLoading(false))
  }, [keyword])

  useEffect(() => { loadPlans('') }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const openPlan = useCallback(async (planId) => {
    try {
      const plan = await lessonPlanAPI.getById(planId)
      setResult(plan)
      setEditing(false)
      setError(plan.status === 'failed' ? (plan.error_message || '生成失败') : null)
      setFormData({
        title: plan.title,
        period: plan.period || '1 课时',
        studentLevel: plan.student_level || '中等',
        requirements: plan.requirements || '',
      })
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (err) {
      addToast(getErrorMessage(err, '加载教案失败'), 'error')
    }
  }, [addToast])

  // 支持 /lessonplan?id=xx 直接打开已保存的教案
  const planIdParam = searchParams.get('id')
  useEffect(() => {
    if (planIdParam) openPlan(planIdParam)
  }, [planIdParam, openPlan])

  // 当前生成任务结束 → 拉取教案内容
  useEffect(() => {
    if (!currentTask || currentTask.status === 'running') return
    if (currentTask.planId) {
      openPlan(currentTask.planId)
      loadPlans()
    }
  }, [currentTask?.status]) // eslint-disable-line react-hooks/exhaustive-deps

  // 打开的教案仍在生成中（例如从列表进入）时，定时刷新它
  useEffect(() => {
    if (result?.status !== 'processing') return
    const timer = setTimeout(() => openPlan(result.id), 4000)
    return () => clearTimeout(timer)
  }, [result, openPlan])

  // 列表中有生成中的教案时定时刷新
  useEffect(() => {
    if (!plans.items.some(p => p.status === 'processing')) return
    const timer = setInterval(() => loadPlans(), 5000)
    return () => clearInterval(timer)
  }, [plans, loadPlans])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!formData.title.trim()) {
      setError('请输入课题名称')
      return
    }
    setSubmitting(true)
    setError(null)
    setResult(null)
    setEditing(false)
    try {
      const plan = await lessonPlanAPI.generate(
        formData.title,
        formData.period,
        formData.studentLevel,
        formData.requirements
      )
      const taskId = addTask({
        type: 'lessonplan',
        title: `生成《${formData.title}》教案`,
        period: formData.period,
        studentLevel: formData.studentLevel,
        requirements: formData.requirements,
        status: 'running',
        progress: estimateProgress(plan.progress_stage, plan.status),
        progressLabel: plan.progress_stage || '排队中',
        planId: plan.id,
      })
      setCurrentTaskId(taskId)
      setSearchParams({ id: String(plan.id) }, { replace: true })
      loadPlans()
      addToast('教案生成任务已提交，可离开本页，完成后自动保存', 'success')
    } catch (err) {
      setError(getErrorMessage(err, '生成失败，请重试'))
    } finally {
      setSubmitting(false)
    }
  }

  const handleRegenerate = async () => {
    if (!result) return
    try {
      const plan = await lessonPlanAPI.regenerate(result.id)
      const taskId = addTask({
        type: 'lessonplan',
        title: `重新生成《${plan.title}》教案`,
        status: 'running',
        progress: 5,
        progressLabel: plan.progress_stage || '排队中',
        planId: plan.id,
      })
      setCurrentTaskId(taskId)
      setResult(null)
      setError(null)
      loadPlans()
    } catch (err) {
      addToast(getErrorMessage(err, '重新生成失败'), 'error')
    }
  }

  const startEdit = () => {
    const content = result.content || ''
    setEditContent(content)
    setEditTitle(result.title || '')
    setSections(splitPlan(content))
    setMarkdownMode(false)
    setEditing(true)
  }

  const updateSection = (index, body) => {
    const next = sections.map((s, i) => (i === index ? { ...s, body } : s))
    setSections(next)
    setEditContent(joinPlan(editTitle, next))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const plan = await lessonPlanAPI.update(result.id, { title: editTitle, content: editContent })
      setResult(plan)
      setFormData(prev => ({ ...prev, title: plan.title }))
      setEditing(false)
      loadPlans()
      addToast('教案已保存', 'success')
    } catch (err) {
      addToast(getErrorMessage(err, '保存失败'), 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    try {
      await lessonPlanAPI.remove(deleteTarget.id)
      if (result?.id === deleteTarget.id) {
        setResult(null)
        setSearchParams({}, { replace: true })
      }
      loadPlans()
      addToast('教案已删除', 'success')
    } catch (err) {
      addToast(getErrorMessage(err, '删除失败'), 'error')
    } finally {
      setDeleteTarget(null)
    }
  }

  const handleExportFile = (format) => {
    const a = document.createElement('a')
    a.href = lessonPlanAPI.exportUrl(result.id, format)
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
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

      const tempContainer = document.createElement('div')
      tempContainer.style.position = 'absolute'
      tempContainer.style.left = '-9999px'
      tempContainer.style.top = '0'
      tempContainer.appendChild(clone)
      document.body.appendChild(tempContainer)

      const opt = {
        margin: [0, 0, 0, 0],
        filename: `${result.title}.pdf`,
        image: { type: 'jpeg', quality: 1 },
        html2canvas: {
          scale: 3,
          useCORS: true,
          letterRendering: true,
          logging: false,
          windowWidth: 794,
        },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
        pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
      }

      await html2pdf().set(opt).from(clone).save()
      document.body.removeChild(tempContainer)
    } catch (err) {
      console.error('PDF导出失败:', err)
      addToast('PDF导出失败，请重试', 'error')
    } finally {
      setExporting(false)
    }
  }

  const stageText = currentTask?.progressLabel || '正在生成教案...'

  return (
    <PageBackground gradient="lessonplan">
      <div className={`max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 pb-12 space-y-6 transition-all duration-1000 ${
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
              <p className="text-sm text-gray-600">一键生成，个性化定制，自动保存</p>
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
                <span className="text-gray-600">{submitting ? '正在提交...' : stageText}</span>
                <span className="text-primary-600 font-medium">
                  已耗时 {elapsedTime}秒
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-purple-500 to-pink-500 h-full rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${Math.max(currentTask?.progress || 5, 5)}%` }}
                >
                  <div className="h-full bg-white/30 animate-pulse" style={{ width: '100%' }}></div>
                </div>
              </div>
              <div className="text-xs text-gray-500 text-center">
                AI 生成通常需要 30-90 秒，任务在后台进行，可离开本页，完成后会自动保存到「我的教案」
              </div>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <h3 className="text-sm font-medium text-red-800">生成失败</h3>
              <p className="mt-1 text-sm text-red-700">{error}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !formData.title}
            className={`w-full py-3 px-4 rounded-lg font-medium ${
              result?.id
                ? 'border border-gray-300 bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-50'
                : loading || !formData.title
                  ? 'bg-gray-400 text-white cursor-not-allowed'
                  : 'bg-primary-600 text-white hover:bg-primary-700'
            }`}
          >
            {loading ? '正在生成...' : (result?.id ? '生成新教案' : '生成教案')}
          </button>
          {result?.id && (
            <p className="text-xs text-gray-400">这是已保存的教案。改内容请用预览旁的「保存修改」，不必重新生成。</p>
          )}
        </form>

        {result && result.status === 'processing' && !loading && (
          <div className="flex items-center justify-center py-8 text-gray-500 text-sm">
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            《{result.title}》正在生成中：{result.progress_stage || '处理中'}
          </div>
        )}

        {result && result.status === 'completed' && (
          <div>
            <div className="flex justify-between items-center mb-4 flex-wrap gap-3">
              <h3 className="text-xl font-bold">{editing ? '编辑教案' : '教案预览'}</h3>
              <div className="flex flex-wrap gap-2">
                {editing ? (
                  <>
                    <button
                      onClick={handleSave}
                      disabled={saving}
                      className="flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                    >
                      <Save className="h-4 w-4 mr-2" />
                      {saving ? '保存中...' : '保存修改'}
                    </button>
                    <button
                      type="button"
                      onClick={() => setMarkdownMode(v => !v)}
                      className="flex items-center px-3 py-2 text-sm text-gray-600 hover:text-gray-900"
                    >
                      {markdownMode ? '返回分段' : '查看 Markdown'}
                    </button>
                    <button
                      onClick={() => setEditing(false)}
                      className="flex items-center px-4 py-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200"
                    >
                      <X className="h-4 w-4 mr-2" />
                      取消
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={startEdit}
                      className="flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                    >
                      <Save className="h-4 w-4 mr-2" />
                      保存修改
                    </button>
                    <button
                      onClick={startEdit}
                      className="flex items-center px-3 py-2 bg-purple-50 text-purple-600 rounded-lg hover:bg-purple-100 transition-colors"
                    >
                      <Edit className="h-4 w-4 mr-1.5" />
                      编辑
                    </button>
                    <button
                      onClick={() => handleExportFile('docx')}
                      className="flex items-center px-3 py-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors"
                    >
                      <FileDown className="h-4 w-4 mr-1.5" />
                      Word
                    </button>
                    <button
                      onClick={() => handleExportFile('md')}
                      className="flex items-center px-3 py-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors"
                    >
                      <FileDown className="h-4 w-4 mr-1.5" />
                      Markdown
                    </button>
                    <button
                      onClick={() => handleExportFile('txt')}
                      className="flex items-center px-3 py-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors"
                    >
                      <FileDown className="h-4 w-4 mr-1.5" />
                      TXT
                    </button>
                    <button
                      onClick={handleExportPdf}
                      disabled={exporting}
                      className="flex items-center px-3 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors disabled:opacity-50"
                    >
                      <Download className="h-4 w-4 mr-1.5" />
                      {exporting ? '生成中...' : 'PDF'}
                    </button>
                    <button
                      type="button"
                      onClick={handleRegenerate}
                      className="px-2 py-2 text-sm text-gray-400 hover:text-gray-700"
                    >
                      重新生成
                    </button>
                  </>
                )}
              </div>
            </div>

            {editing ? (
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">课题</label>
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => {
                      const title = e.target.value
                      setEditTitle(title)
                      if (!markdownMode) setEditContent(joinPlan(title, sections))
                    }}
                    className="w-full border border-gray-300 rounded-lg px-4 py-2"
                    placeholder="课题名称"
                  />
                </div>
                {markdownMode ? (
                  <textarea
                    value={editContent}
                    onChange={(e) => {
                      setEditContent(e.target.value)
                      setSections(splitPlan(e.target.value))
                    }}
                    className="w-full border border-gray-300 rounded-lg px-4 py-3 font-mono text-sm"
                    rows={24}
                  />
                ) : sections.length > 0 ? (
                  sections.map((s, i) => (
                    <div key={`${s.heading}-${i}`}>
                      <label className="block text-xs font-medium text-gray-500 mb-1">{sectionLabel(s.heading)}</label>
                      <textarea
                        value={s.body}
                        onChange={(e) => updateSection(i, e.target.value)}
                        className="w-full border border-gray-300 rounded-lg px-4 py-3 text-sm"
                        rows={s.heading.includes('过程') ? 10 : 4}
                      />
                    </div>
                  ))
                ) : (
                  <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-4 py-3 text-sm"
                    rows={16}
                  />
                )}
              </div>
            ) : (
            <div
              ref={previewRef}
              className="border rounded-lg p-6 bg-white lesson-plan-content max-w-full overflow-x-auto"
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
                .lesson-plan-content pre,
                .lesson-plan-content code {
                  max-width: 100%;
                }
                .lesson-plan-content pre {
                  overflow-x: auto;
                  white-space: pre;
                }
              `}</style>
              <ReactMarkdown
                remarkPlugins={[remarkMath]}
                rehypePlugins={[rehypeKatex]}
              >
                {result.content}
              </ReactMarkdown>
            </div>
            )}
          </div>
        )}
        </div>

        <div className="bg-white/90 backdrop-blur-md rounded-2xl shadow-xl border border-white/20">
          <div className="p-5 border-b border-gray-100 flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center space-x-2">
              <History className="h-5 w-5 text-purple-500" />
              <h3 className="text-lg font-semibold text-gray-900">我的教案</h3>
              <span className="text-sm text-gray-400">共 {plans.total} 份</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') loadPlans(keyword) }}
                  placeholder="搜索课题，回车"
                  className="pl-9 pr-3 py-1.5 border border-gray-300 rounded-lg text-sm"
                />
              </div>
              <button onClick={() => loadPlans(keyword)} className="p-2 text-gray-400 hover:text-purple-600 rounded-lg" title="刷新">
                <RefreshCw className={`h-4 w-4 ${plansLoading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
          {plansLoading && plans.items.length === 0 ? (
            <p className="p-8 text-center text-sm text-gray-400" role="status">加载中…</p>
          ) : plans.items.length === 0 ? (
            appliedKeyword ? (
              <div className="p-8 text-center">
                <p className="text-sm text-gray-500">没有找到包含这个词的教案</p>
                <button
                  type="button"
                  onClick={() => { setKeyword(''); loadPlans('') }}
                  className="mt-3 text-sm text-purple-600 hover:underline"
                >
                  清空搜索
                </button>
              </div>
            ) : (
              <p className="p-8 text-center text-sm text-gray-400">还没有保存的教案</p>
            )
          ) : (
            <div className="divide-y divide-gray-100">
              {plans.items.map(plan => {
                const badge = STATUS_BADGE[plan.status] || STATUS_BADGE.completed
                const active = result?.id === plan.id
                return (
                  <div
                    key={plan.id}
                    className={`px-5 py-3 flex items-center justify-between gap-3 cursor-pointer hover:bg-purple-50/50 ${active ? 'bg-purple-50' : ''}`}
                    onClick={() => setSearchParams({ id: String(plan.id) })}
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <button
                          type="button"
                          className="text-sm font-medium text-gray-900 text-left hover:text-purple-700"
                          onClick={(e) => { e.stopPropagation(); setSearchParams({ id: String(plan.id) }) }}
                        >
                          {plan.title}
                        </button>
                        <span className={`px-2 py-0.5 text-xs rounded-full ${badge.cls}`}>{badge.label}</span>
                        {plan.status === 'processing' && <Loader2 className="h-3 w-3 animate-spin text-blue-500" />}
                      </div>
                      <p className="text-xs text-gray-400 mt-0.5 truncate">
                        {formatServerTime(plan.created_at)}
                        {' · '}{plan.period} · {plan.student_level}
                        {plan.status === 'failed' ? ` · ${plan.error_message || ''}` : plan.preview ? ` · ${plainPreview(plan.preview)}` : ''}
                      </p>
                    </div>
                    {plan.status !== 'processing' && (
                      <button
                        onClick={(e) => { e.stopPropagation(); setDeleteTarget(plan) }}
                        className="p-2 text-gray-400 hover:text-red-600 rounded-lg shrink-0"
                        title="删除"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      <ConfirmDialog
        isOpen={!!deleteTarget}
        title="删除教案"
        message={`确定删除《${deleteTarget?.title || ''}》吗？删除后无法恢复。`}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
        confirmText="确认删除"
        cancelText="再想想"
      />
    </PageBackground>
  )
}

export default LessonPlanGenerator
