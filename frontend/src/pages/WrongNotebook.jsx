import React, { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Calendar, CheckCircle, ExternalLink, BookOpen, FileText, FileSpreadsheet, File, AlertCircle, Trash2, Loader2, RotateCcw } from 'lucide-react'
import { notebookAPI, getErrorMessage } from '../utils/api'
import { useAuth } from '../context/AuthContext'
import { subjectsFor } from '../utils/stageSubjects'
import ReactMarkdown from 'react-markdown'
import MathText from '../components/MathText'
import { isBlankText, orDash } from '../utils/mathText'
import PageBackground from '../components/PageBackground'

const SUPPORTED_FORMATS = {
  'image/*': ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'],
  'application/pdf': ['pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['docx'],
  'application/msword': ['doc'],
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['xlsx'],
  'application/vnd.ms-excel': ['xls'],
  'text/markdown': ['md'],
  'text/plain': ['txt'],
}

const FILE_TYPE_ICONS = {
  image: FileText,
  pdf: FileText,
  word: FileText,
  excel: FileSpreadsheet,
  text: File,
}

const FILE_TYPE_LABELS = {
  image: '图片',
  pdf: 'PDF',
  word: 'Word',
  excel: 'Excel',
  text: '文本',
}

const ERROR_MESSAGES = {
  empty: '哎呀，这个文件好像有点"害羞"，什么都没解析出来呢~ 换个文件试试看？',
  invalid_format: '这个文件格式我不太认识呢，试试图片、PDF、Word、Excel 或 TXT 文件吧~',
  parse_failed: '解析遇到了一点小麻烦，可能是文件内容不太清晰，重新上传试试？',
  no_questions: '翻遍了整个文件，也没找到错题的踪迹~ 确认一下文件里有没有题目内容哦',
  general: '出了点小状况，稍后再试一次吧~',
}

const PAGE_SIZE = 20

// 跨页面恢复「生成变式题」进行中状态：生成中的错题 id + 起始时间存 sessionStorage，
// 切走页面再回来时恢复「生成中」并轮询结果；超过 10 分钟未出结果自动放弃，避免空转。
const VARIANT_PENDING_KEY = 'wrongnotebook_variant_pending'
const VARIANT_PENDING_TTL = 10 * 60 * 1000

function readPendingVariants() {
  try {
    const arr = JSON.parse(sessionStorage.getItem(VARIANT_PENDING_KEY) || '[]')
    if (!Array.isArray(arr)) return []
    const now = Date.now()
    return arr.filter(item => item && item.id && now - (item.ts || 0) < VARIANT_PENDING_TTL)
  } catch {
    return []
  }
}

function writePendingVariants(list) {
  try {
    sessionStorage.setItem(VARIANT_PENDING_KEY, JSON.stringify(list))
  } catch {
    /* 存储不可用时静默降级：仅本页内有效 */
  }
}

const WrongNotebook = () => {
  const { user } = useAuth()
  const [questions, setQuestions] = useState([])
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState({ knowledgePoint: '', subject: '', mastered: '' })
  const [isVisible, setIsVisible] = useState(false)
  const [parseError, setParseError] = useState(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadedFileName, setUploadedFileName] = useState('')
  const [listLoading, setListLoading] = useState(true)
  const [hasMore, setHasMore] = useState(false)
  const [stats, setStats] = useState(null)
  const [statsLoading, setStatsLoading] = useState(true)
  const [newKnowledgePoint, setNewKnowledgePoint] = useState('')
  const [variantLoadingIds, setVariantLoadingIds] = useState(() => {
    // 从 sessionStorage 恢复上次页面仍在生成的题目（切页再回来后继续显示"生成中"）
    const restored = {}
    readPendingVariants().forEach(item => { restored[item.id] = true })
    return restored
  }) // 错题 id -> 生成中，支持多题并行
  const [actionError, setActionError] = useState(null)

  useEffect(() => {
    setIsVisible(true)
  }, [])

  useEffect(() => {
    if (!user?.subject) return
    setFilter((prev) => (prev.subject ? prev : { ...prev, subject: user.subject }))
  }, [user?.subject])

  const buildParams = useCallback((offset) => {
    const params = { limit: PAGE_SIZE, offset }
    if (filter.knowledgePoint) params.knowledge_point = filter.knowledgePoint
    if (filter.subject) params.subject = filter.subject
    if (filter.mastered !== '') params.is_mastered = filter.mastered === 'true'
    return params
  }, [filter])

  const loadList = useCallback(async (append = false, offset = 0) => {
    setListLoading(true)
    try {
      const items = await notebookAPI.getList(buildParams(offset))
      setQuestions(prev => (append ? [...prev, ...items] : items))
      setHasMore(items.length === PAGE_SIZE)
    } catch (err) {
      setActionError(getErrorMessage(err, '错题加载失败'))
    } finally {
      setListLoading(false)
    }
  }, [buildParams])

  const loadStats = useCallback(() => {
    setStatsLoading(true)
    notebookAPI.getStats({ subject: filter.subject || undefined })
      .then(setStats)
      .catch(() => {})
      .finally(() => setStatsLoading(false))
  }, [filter.subject])

  // 高频错题：按知识板块归类（三角函数、数列、圆锥曲线……），板块题次越高越是薄弱点
  const [clusters, setClusters] = useState(null)
  const [clustersLoading, setClustersLoading] = useState(true)
  const [expandedQuestions, setExpandedQuestions] = useState({}) // 'catIdx-qIdx' -> 展开全文
  const loadClusters = useCallback(() => {
    setClustersLoading(true)
    notebookAPI.getKnowledgeClusters({ subject: filter.subject || undefined })
      .then(setClusters)
      .catch(() => setClusters(null))
      .finally(() => setClustersLoading(false))
  }, [filter.subject])

  useEffect(() => { loadList(false, 0) }, [loadList])
  useEffect(() => { loadStats() }, [loadStats])
  useEffect(() => { loadClusters() }, [loadClusters])

  const getFileType = (file) => {
    const ext = file.name.split('.').pop().toLowerCase()
    if (['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'].includes(ext)) return 'image'
    if (ext === 'pdf') return 'pdf'
    if (['doc', 'docx'].includes(ext)) return 'word'
    if (['xls', 'xlsx'].includes(ext)) return 'excel'
    if (['md', 'txt'].includes(ext)) return 'text'
    return 'unknown'
  }

  const handleUpload = async (event) => {
    const file = event.target.files[0]
    if (!file) return

    const fileType = getFileType(file)

    if (fileType === 'unknown') {
      setParseError({ type: 'invalid_format', message: ERROR_MESSAGES.invalid_format })
      return
    }

    setLoading(true)
    setParseError(null)
    setUploadProgress(0)
    setUploadedFileName(file.name)

    const progressInterval = setInterval(() => {
      setUploadProgress(prev => {
        if (prev >= 90) {
          clearInterval(progressInterval)
          return 90
        }
        return prev + 10
      })
    }, 200)

    try {
      const response = await notebookAPI.upload(
        file,
        newKnowledgePoint.trim() || filter.knowledgePoint || '未分类',
        filter.subject || user?.subject || ''
      )

      clearInterval(progressInterval)
      setUploadProgress(100)

      if (response && response.questions && response.questions.length > 0) {
        setQuestions(prev => [...response.questions, ...prev])
        setUploadedFileName('')
        loadStats()
        loadClusters()
      } else if (response && response.error) {
        setParseError({ type: response.error_type || 'general', message: response.error || ERROR_MESSAGES.general })
      } else {
        setParseError({ type: 'no_questions', message: ERROR_MESSAGES.no_questions })
      }
    } catch (error) {
      console.error('录入失败:', error)
      clearInterval(progressInterval)
      const detail = error?.response?.data?.detail
      setParseError({ type: 'parse_failed', message: typeof detail === 'string' ? detail : ERROR_MESSAGES.parse_failed })
    } finally {
      setLoading(false)
      event.target.value = ''
    }
  }

  const handleToggleMastered = async (q) => {
    try {
      if (q.is_mastered) await notebookAPI.markUnmastered(q.id)
      else await notebookAPI.markMastered(q.id)
      setQuestions(prev => prev.map(item => (item.id === q.id ? { ...item, is_mastered: !q.is_mastered } : item)))
      loadStats()
      loadClusters()
    } catch (err) {
      setActionError(getErrorMessage(err, '操作失败'))
    }
  }

  const handleDelete = async (q) => {
    if (!window.confirm('确定删除这道错题吗？')) return
    try {
      await notebookAPI.remove(q.id)
      setQuestions(prev => prev.filter(item => item.id !== q.id))
      loadStats()
      loadClusters()
    } catch (err) {
      setActionError(getErrorMessage(err, '删除失败'))
    }
  }

  const handleGenerateVariants = async (q) => {
    setVariantLoadingIds(prev => ({ ...prev, [q.id]: true }))
    setActionError(null)
    writePendingVariants([...readPendingVariants().filter(item => item.id !== q.id), { id: q.id, ts: Date.now() }])
    try {
      const res = await notebookAPI.generateVariants(q.id, 3)
      setQuestions(prev => prev.map(item => (item.id === q.id ? { ...item, variant_questions: res.variant_questions } : item)))
    } catch (err) {
      setActionError(getErrorMessage(err, '变式题生成失败'))
    } finally {
      writePendingVariants(readPendingVariants().filter(item => item.id !== q.id))
      setVariantLoadingIds(prev => {
        const next = { ...prev }
        delete next[q.id]
        return next
      })
    }
  }

  // 切页再回来后：对仍在生成中的错题轮询，变式题一落库就自动显示，无需手动刷新
  useEffect(() => {
    const pendingIds = Object.keys(variantLoadingIds).map(Number)
    if (pendingIds.length === 0) return undefined
    const clearLoading = (id) => {
      setVariantLoadingIds(prev => {
        const next = { ...prev }
        delete next[id]
        return next
      })
    }
    const timer = setInterval(async () => {
      for (const id of pendingIds) {
        if (!readPendingVariants().some(item => item.id === id)) {
          clearLoading(id) // 已过期或被清理：停止本轮轮询标记
          continue
        }
        try {
          const item = await notebookAPI.getOne(id)
          if (item && item.variant_questions && item.variant_questions.length > 0) {
            setQuestions(prev => prev.map(q => (q.id === id ? { ...q, variant_questions: item.variant_questions } : q)))
            writePendingVariants(readPendingVariants().filter(p => p.id !== id))
            clearLoading(id)
          }
        } catch {
          // 题目被删除或登录失效：不再轮询该题
          writePendingVariants(readPendingVariants().filter(p => p.id !== id))
          clearLoading(id)
        }
      }
    }, 4000)
    return () => clearInterval(timer)
  }, [variantLoadingIds])

  return (
    <PageBackground gradient="notebook">
      <div className={`max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 pb-12 transition-all duration-1000 ${
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-12'
      }`}>
        <div className="bg-white/90 backdrop-blur-md rounded-2xl shadow-xl p-8 border border-white/20">
          <div className="flex items-center space-x-3 mb-6">
            <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-emerald-500 rounded-xl flex items-center justify-center shadow-lg">
              <BookOpen className="h-6 w-6 text-white" />
            </div>
            <div>
              <h2 className="text-3xl font-bold bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
                AI 错题本管家
              </h2>
              <p className="text-sm text-gray-600">智能整理，变式练习，举一反三</p>
            </div>
          </div>

          <div className="flex flex-wrap gap-3 mb-6 items-end">
            <label className="flex items-center space-x-2 bg-gradient-to-r from-green-500 to-emerald-500 text-white px-5 py-2.5 rounded-xl cursor-pointer hover:from-green-600 hover:to-emerald-600 shadow-md hover:shadow-lg transition-all duration-300 max-w-full">
              <Plus className="h-5 w-5 shrink-0" />
              <span className="font-medium whitespace-normal text-left">上传错题文件（图片、PDF、Word、TXT、MD）</span>
              <input
                type="file"
                accept="image/*,.pdf,.docx,.md,.txt"
                onChange={handleUpload}
                className="hidden"
                id="upload-wrong"
              />
            </label>

            <label className="flex flex-col gap-1 text-xs text-gray-500 w-full sm:w-auto sm:min-w-[16rem]">
              上传时填写的知识点
              <input
                type="text"
                value={newKnowledgePoint}
                onChange={(e) => setNewKnowledgePoint(e.target.value)}
                placeholder="例如：本课知识点"
                aria-label="上传时填写的知识点"
                className="w-full border border-gray-300 rounded-xl px-4 py-2.5 bg-white text-sm text-gray-900 focus:ring-2 focus:ring-green-500 focus:border-transparent"
              />
            </label>

            <label className="flex flex-col gap-1 text-xs text-gray-500">
              筛选知识点
              <select
                value={filter.knowledgePoint}
                onChange={(e) => setFilter(prev => ({ ...prev, knowledgePoint: e.target.value }))}
                aria-label="筛选知识点"
                className="border border-gray-300 rounded-xl px-4 py-2.5 bg-white hover:border-green-400 focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all cursor-pointer"
              >
                <option value="">全部知识点</option>
                {(stats?.knowledge_points || []).map(kp => (
                  <option key={kp.name} value={kp.name}>{kp.name}（{kp.count}）</option>
                ))}
              </select>
            </label>

            <select
              value={filter.subject}
              onChange={(e) => setFilter(prev => ({ ...prev, subject: e.target.value }))}
              className="border border-gray-300 rounded-xl px-4 py-2.5 bg-white hover:border-green-400 focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all cursor-pointer"
            >
              <option value="">全部学科</option>
              {(filter.subject && !subjectsFor(user?.education_stage).includes(filter.subject)
                ? [filter.subject, ...subjectsFor(user?.education_stage)]
                : subjectsFor(user?.education_stage)
              ).map((item) => <option key={item} value={item}>{item}</option>)}
            </select>

            <select
              value={filter.mastered}
              onChange={(e) => setFilter(prev => ({ ...prev, mastered: e.target.value }))}
              className="border border-gray-300 rounded-xl px-4 py-2.5 bg-white hover:border-green-400 focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all cursor-pointer"
            >
              <option value="">全部状态</option>
              <option value="false">未掌握</option>
              <option value="true">已掌握</option>
            </select>
          </div>

          {(statsLoading || (listLoading && questions.length === 0)) ? (
            <p className="text-sm text-gray-500 mb-4">正在统计</p>
          ) : stats && stats.total > 0 ? (
            <p className="text-sm text-gray-500 mb-4">
              共 {stats.total} 道错题 · 已掌握 {stats.mastered} · 待巩固 {stats.unmastered}
            </p>
          ) : (
            <p className="text-sm text-gray-600 mb-4">
              这里还没有错题。班级作业里的错题请先到对应作业查看。
              <Link to="/class" className="ml-1 text-green-700 underline">我的班级</Link>
            </p>
          )}

          {actionError && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">{actionError}</div>
          )}

          <div className="mb-6 bg-gradient-to-br from-amber-50 to-orange-50 border border-amber-100 rounded-xl p-4 sm:p-5" data-tour="notebook-clusters">
            <div className="flex items-center gap-2 mb-3">
              <FileSpreadsheet className="h-5 w-5 text-amber-600" />
              <h3 className="text-base font-semibold text-gray-900">高频错题</h3>
              <span className="text-xs text-gray-500">按知识板块归类，题次越多的板块越是薄弱点</span>
            </div>
            {clustersLoading ? (
              <p className="text-sm text-gray-500 flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin" />正在统计…</p>
            ) : clusters && clusters.categories.length > 0 ? (
              <>
                {clusters.categories[0] && (
                  <div className="mb-3 flex flex-wrap items-center gap-2">
                    <span className="text-xs text-gray-500">薄弱知识点：</span>
                    {clusters.categories.slice(0, 3).map((c) => (
                      <span key={c.category} className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                        c.errors >= 4 ? 'bg-red-100 text-red-700' : c.count >= 2 ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-600'
                      }`}>
                        {c.category} · {c.errors} 题次
                      </span>
                    ))}
                  </div>
                )}
                <div className="space-y-3">
                  {clusters.categories.map((cat, ci) => (
                    <div key={cat.category} className="bg-white/80 rounded-lg border border-amber-100/60 overflow-hidden">
                      <div className="flex items-center justify-between gap-3 px-3 py-2 bg-amber-50/60">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-500 text-white text-xs font-bold shrink-0">{ci + 1}</span>
                          <span className="font-semibold text-sm text-gray-900 truncate">{cat.category}</span>
                          {cat.errors >= 4 ? (
                            <span className="shrink-0 text-xs font-medium px-2 py-0.5 rounded-full bg-red-100 text-red-700">重点薄弱</span>
                          ) : cat.count >= 2 ? (
                            <span className="shrink-0 text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">薄弱</span>
                          ) : null}
                        </div>
                        <span className="shrink-0 text-xs text-gray-500">
                          {cat.count} 道错题 · 错 {cat.errors} 次
                          {cat.mastered_count > 0 ? ` · 已掌握 ${cat.mastered_count}` : ''}
                        </span>
                      </div>
                      <ol className="divide-y divide-amber-50">
                        {cat.questions.map((item, qi) => {
                          const expKey = `${ci}-${qi}`
                          const expanded = !!expandedQuestions[expKey]
                          return (
                            <li
                              key={expKey}
                              className="px-3 py-2 cursor-pointer hover:bg-amber-50/40"
                              onClick={() => setExpandedQuestions(prev => ({ ...prev, [expKey]: !prev[expKey] }))}
                            >
                              <div className="flex items-start justify-between gap-3">
                                <div className={`text-sm text-gray-800 min-w-0 ${expanded ? '' : 'line-clamp-2'}`}>
                                  <span className="font-medium text-amber-600 mr-1">{qi + 1}.</span>
                                  {isBlankText(item.question_text) ? <span className="text-gray-400">（无题目内容）</span> : <MathText text={item.question_text} className="inline" />}
                                </div>
                                <span className={`shrink-0 text-xs font-medium px-2 py-0.5 rounded-full mt-0.5 ${item.times >= 3 ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>
                                  错 {item.times} 次
                                </span>
                              </div>
                              <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500 pl-5">
                                {item.knowledge_point && <span>知识点:{item.knowledge_point}</span>}
                                {item.error_date && <span>最近:{String(item.error_date).slice(0, 10)}</span>}
                                {item.is_mastered && <span className="text-green-600">已掌握</span>}
                                <span className="text-amber-400">{expanded ? '收起' : '展开全文'}</span>
                              </div>
                            </li>
                          )
                        })}
                      </ol>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <p className="text-sm text-gray-500">还没有足够的数据。班级作业批改或错题录入后，这里会按知识板块自动归类，帮你定位薄弱环节。</p>
            )}
          </div>

        {loading && (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <BookOpen className="h-8 w-8 text-green-500 animate-pulse" />
            </div>
            <p className="text-gray-600 font-medium">正在录入错题...</p>
            {uploadedFileName && (
              <p className="text-sm text-gray-500 mt-2">正在解析：{uploadedFileName}</p>
            )}
            <div className="mt-4 max-w-xs mx-auto">
              <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-green-500 to-emerald-500 h-full rounded-full transition-all duration-300 ease-out"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          </div>
        )}

        {parseError && !loading && (
          <div className="mb-6 p-6 bg-gradient-to-r from-amber-50 to-orange-50 rounded-xl border border-amber-200 text-center">
            <div className="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <AlertCircle className="h-8 w-8 text-amber-500" />
            </div>
            <p className="text-amber-800 font-medium text-lg">{parseError.message}</p>
            <p className="text-amber-600 text-sm mt-2">支持格式：图片、PDF、Word(.docx)、Markdown、TXT，单个文件不超过 10MB</p>
          </div>
        )}

        <div className="space-y-4">
          {questions.map((q) => (
            <div
              key={q.id}
              className={`border rounded-xl p-5 transition-all duration-300 hover:shadow-md ${
                q.is_mastered ? 'border-green-200 bg-gradient-to-r from-green-50 to-emerald-50' : 'border-gray-200 bg-white hover:border-green-300'
              }`}
            >
              <div className="flex justify-between items-start flex-wrap gap-2 mb-4">
                <div className="flex items-center space-x-2">
                  <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center shrink-0">
                    <Calendar className="h-4 w-4 text-green-600" />
                  </div>
                  <span className="text-sm text-gray-600 whitespace-nowrap">
                    {new Date(q.error_date).toLocaleDateString('zh-CN')}
                  </span>
                </div>
                <div className="flex flex-wrap items-center justify-end gap-2">
                  <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-medium whitespace-nowrap">
                    {q.knowledge_point}
                  </span>
                  <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-xs font-medium whitespace-nowrap">
                    {q.subject}
                  </span>
                  {q.source === 'grading' && (
                    <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-xs font-medium whitespace-nowrap">批改同步</span>
                  )}
                </div>
              </div>

              <div className="mb-4 bg-gray-50 rounded-xl p-4">
                <p className="text-sm font-medium text-gray-600 mb-2 flex items-center">
                  <span className="w-1.5 h-1.5 bg-green-500 rounded-full mr-2"></span>
                  原题
                </p>
                <MathText text={orDash(q.question_text)} block className="text-gray-900 leading-relaxed" />
              </div>

              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="bg-red-50 rounded-xl p-4 border border-red-100">
                  <p className="text-sm font-medium text-red-600 mb-1 flex items-center">
                    <span className="w-1.5 h-1.5 bg-red-500 rounded-full mr-2"></span>
                    我的答案
                  </p>
                  <div className="text-red-700">
                    {isBlankText(q.user_answer) ? '—' : <MathText text={q.user_answer} block />}
                  </div>
                </div>
                <div className="bg-green-50 rounded-xl p-4 border border-green-100">
                  <p className="text-sm font-medium text-green-600 mb-1 flex items-center">
                    <span className="w-1.5 h-1.5 bg-green-500 rounded-full mr-2"></span>
                    正确答案
                  </p>
                  <div className="text-green-700">
                    {isBlankText(q.correct_answer) ? '—' : <MathText text={q.correct_answer} block />}
                  </div>
                </div>
              </div>

              {q.variant_questions && q.variant_questions.length > 0 && (
                <div className="mb-4">
                  <p className="text-sm font-medium text-gray-700 mb-3 flex items-center">
                    <span className="w-1.5 h-1.5 bg-blue-500 rounded-full mr-2"></span>
                    变式练习
                  </p>
                  <div className="space-y-3">
                    {q.variant_questions.map((v, idx) => (
                      <div key={idx} className="bg-gradient-to-r from-blue-50 to-cyan-50 p-4 rounded-xl border border-blue-100">
                        <div className="text-sm text-gray-800">
                          <span className="font-medium text-blue-600">变式{idx + 1}:</span>{' '}
                          <MathText text={orDash(v.question_text)} />
                        </div>
                        <div className="text-sm text-gray-600 mt-2 bg-white/60 rounded-lg px-3 py-2">
                          <span className="font-medium">答案:</span>{' '}
                          <MathText text={orDash(v.answer)} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex space-x-3 pt-2 border-t border-gray-100">
                <button
                  onClick={() => handleGenerateVariants(q)}
                  disabled={!!variantLoadingIds[q.id]}
                  className="flex items-center text-blue-600 hover:text-blue-700 text-sm font-medium hover:bg-blue-50 px-3 py-1.5 rounded-lg transition-all disabled:opacity-50"
                >
                  {variantLoadingIds[q.id] ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <ExternalLink className="h-4 w-4 mr-1" />}
                  {variantLoadingIds[q.id] ? 'AI 生成中（约 30 秒）...' : (q.variant_questions?.length ? '换一批变式题' : '生成变式题')}
                </button>
                {!q.is_mastered ? (
                  <button
                    onClick={() => handleToggleMastered(q)}
                    className="flex items-center text-green-600 hover:text-green-700 text-sm font-medium hover:bg-green-50 px-3 py-1.5 rounded-lg transition-all"
                  >
                    <CheckCircle className="h-4 w-4 mr-1" />
                    标记已掌握
                  </button>
                ) : (
                  <button
                    onClick={() => handleToggleMastered(q)}
                    className="text-green-600 text-sm flex items-center font-medium bg-green-100 px-3 py-1.5 rounded-lg"
                    title="点击取消掌握标记"
                  >
                    <CheckCircle className="h-4 w-4 mr-1" />
                    已掌握
                    <RotateCcw className="h-3 w-3 ml-1 opacity-60" />
                  </button>
                )}
                <button
                  onClick={() => handleDelete(q)}
                  className="ml-auto flex items-center text-gray-400 hover:text-red-600 text-sm px-3 py-1.5 rounded-lg transition-all"
                >
                  <Trash2 className="h-4 w-4 mr-1" />
                  删除
                </button>
              </div>
            </div>
          ))}
        </div>

        {questions.length === 0 && !loading && listLoading && (
          <div className="flex items-center justify-center py-16 text-gray-500">
            <Loader2 className="h-5 w-5 mr-2 animate-spin" />
            正在统计错题...
          </div>
        )}

        {questions.length === 0 && !loading && !listLoading && (
          <div className="text-center py-16">
            <div className="w-24 h-24 bg-gradient-to-br from-green-100 to-emerald-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <BookOpen className="h-12 w-12 text-green-500" />
            </div>
            <p className="text-gray-500 text-lg font-medium">暂无错题记录</p>
            <p className="text-sm text-gray-400 mt-2">点击上方「上传错题文件」添加</p>
          </div>
        )}

        {questions.length > 0 && hasMore && (
          <div className="mt-6 text-center">
            <button
              onClick={() => loadList(true, questions.length)}
              disabled={listLoading}
              className="text-primary-600 hover:text-primary-700 disabled:opacity-50"
            >
              {listLoading ? '加载中...' : '加载更多'}
            </button>
          </div>
        )}
        </div>
      </div>
    </PageBackground>
  )
}

export default WrongNotebook
