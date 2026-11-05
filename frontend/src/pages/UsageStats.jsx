import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Activity,
  CheckCircle,
  ChevronDown,
  Coins,
  Timer,
  RefreshCw,
  Loader2,
  AlertTriangle,
  Download,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../components/Toast'
import { feedbackAPI, usageAPI } from '../utils/api'

const RANGES = [
  { id: 'today', label: '今天' },
  { id: '7d', label: '7天' },
  { id: '30d', label: '30天' },
  { id: 'all', label: '全部' },
]

const KIND_LABELS = {
  lessonplan: '教案',
  grade: '批改',
  variant: '变式题',
}

const FEATURE_LABELS = {
  ocr: 'OCR 识别',
  grade: '作业批改',
  lessonplan: '教案生成',
  variant: '变式题',
  questionbank_search: '题库搜索',
  seed_grade: '种子批改',
  probe: '探测',
  other: '其他',
  unknown: '未标注',
}

const MODULES = [
  { id: 'grade', label: '作业批改', always: true },
  { id: 'lessonplan', label: '教案生成', always: true },
  { id: 'questionbank', label: '题库搜索', always: true },
  { id: 'notebook', label: '错题本', always: true },
  { id: 'ocr', label: '识别', always: true },
  { id: 'variant', label: '变式题', always: true },
  { id: 'probe', label: '评测脚本', always: false },
  { id: 'other', label: '其他', always: false },
]

const MODULE_LABELS = Object.fromEntries(MODULES.map((item) => [item.id, item.label]))

const rangeToSince = (rangeId) => {
  const now = new Date()
  if (rangeId === 'today') {
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    return start.toISOString()
  }
  if (rangeId === '7d') return new Date(now.getTime() - 7 * 86400000).toISOString()
  if (rangeId === '30d') return new Date(now.getTime() - 30 * 86400000).toISOString()
  return undefined
}

/** YYYY-MM-DD → 当天本地 00:00:00 的 ISO */
const dayStartISO = (ymd) => {
  const [y, m, d] = String(ymd).split('-').map(Number)
  if (!y || !m || !d) return undefined
  return new Date(y, m - 1, d, 0, 0, 0, 0).toISOString()
}

/** YYYY-MM-DD → 当天本地 23:59:59 的 ISO */
const dayEndISO = (ymd) => {
  const [y, m, d] = String(ymd).split('-').map(Number)
  if (!y || !m || !d) return undefined
  return new Date(y, m - 1, d, 23, 59, 59, 999).toISOString()
}

const localYmd = (date = new Date()) => {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

/** 按当前区间判断 YYYY-MM-DD 是否应出现在「按日期」表（避免文件日把区间外的行掺进来） */
const dayWithinRange = (day, rangeId, customFrom, customTo) => {
  if (!day || day === 'unknown') return rangeId === 'all'
  if (rangeId === 'all') return true
  if (rangeId === 'custom') {
    if (customFrom && day < customFrom) return false
    if (customTo && day > customTo) return false
    return true
  }
  const today = localYmd()
  if (rangeId === 'today') return day === today
  const sinceIso = rangeToSince(rangeId)
  if (!sinceIso) return true
  const sinceDay = localYmd(new Date(sinceIso))
  return day >= sinceDay && day <= today
}

const fmtInt = (v) => Number(v || 0).toLocaleString('zh-CN')
const fmtFloat = (v, d = 2) => Number(v || 0).toFixed(d)
const fmtPct = (v) => `${Number(v || 0).toFixed(1)}%`

const fmtTokens = (v) => {
  const n = Number(v || 0)
  if (n >= 1e6) return `${(n / 1e6).toFixed(2)}M`
  if (n >= 1e4) return `${(n / 1e3).toFixed(1)}K`
  return fmtInt(n)
}

const saveBlob = (blob, filename) => {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

const accountName = (account) => {
  if (['历史日志', '未归属', '未记到老师名下'].includes(account?.display_name)) return '历史日志'
  return account?.display_name || '—'
}

const isHistoryAccount = (account) => !account?.username && ['历史日志', '未归属', '未记到老师名下'].includes(account?.display_name)

const callOwner = (call, accounts) => {
  if (call?.teacher_id == null) return '未记到老师名下'
  const found = (accounts || []).find((account) => account.id === call.teacher_id)
  if (found?.username) return found.display_name || found.username
  if (found?.display_name && found.display_name !== '已删除的账号') return found.display_name
  return '账号已删除'
}

const moduleText = (account, id) => {
  const stat = account?.modules?.[id]
  if (!stat || (!Number(stat.calls) && !Number(stat.total_tokens))) return '—'
  return `${fmtInt(stat.calls)} 次 · ${fmtTokens(stat.total_tokens)}`
}

const fmtTime = (iso) => {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('zh-CN', { hour12: false })
}

const KpiCard = ({ icon: Icon, label, value, note, color }) => (
  <div className="bg-white rounded-xl border border-gray-200 p-5">
    <div className="flex items-center justify-between">
      <span className="text-sm text-gray-500">{label}</span>
      <div className={`p-2 rounded-lg ${color}`}>
        <Icon className="h-4 w-4" />
      </div>
    </div>
    <div className="mt-3 text-2xl font-bold text-gray-900">{value}</div>
    {note && <div className="mt-1 text-xs text-gray-400">{note}</div>}
  </div>
)

const Card = ({ title, hint, children, right, collapsible = true, defaultOpen = false }) => {
  const [open, setOpen] = useState(defaultOpen)
  const showBody = !collapsible || open
  return (
    <div className="bg-white rounded-xl border border-gray-200">
      <div className={`px-5 py-4 flex items-center justify-between gap-3 ${showBody ? 'border-b border-gray-100' : ''}`}>
        <div className="min-w-0">
          <h3 className="text-base font-semibold text-gray-900">{title}</h3>
          {hint && <p className="text-xs text-gray-400 mt-0.5">{hint}</p>}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {right}
          {collapsible && (
            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              aria-expanded={open}
              aria-label={open ? `收起${title}` : `展开${title}`}
              className="p-1.5 rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-700"
            >
              <ChevronDown className={`h-5 w-5 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
            </button>
          )}
        </div>
      </div>
      {showBody && <div className="overflow-x-auto">{children}</div>}
    </div>
  )
}

const ALIGN = { left: 'text-left', right: 'text-right', center: 'text-center' }

const Th = ({ children, align = 'right' }) => (
  <th className={`px-4 py-2.5 text-xs font-medium text-gray-500 whitespace-nowrap ${ALIGN[align]}`}>{children}</th>
)

const Td = ({ children, align = 'right', className = '' }) => (
  <td className={`px-4 py-2.5 text-sm text-gray-700 whitespace-nowrap ${ALIGN[align]} ${className}`}>{children}</td>
)

const EmptyRow = ({ cols, text = '暂无数据' }) => (
  <tr>
    <td colSpan={cols} className="px-4 py-8 text-center text-sm text-gray-400">{text}</td>
  </tr>
)

const numText = (v, extra = '') => {
  const n = Number(v || 0)
  return `${extra} ${fmtInt(n)} ${fmtTokens(n)} ${n}`.trim()
}

const applyFilters = (rows, filters, getters) => {
  const active = Object.entries(filters || {}).filter(([, q]) => String(q).trim())
  if (!active.length) return rows
  return rows.filter((row) => active.every(([key, q]) => {
    const text = String(getters[key]?.(row) ?? '').toLowerCase()
    return text.includes(String(q).trim().toLowerCase())
  }))
}

const hasActiveFilters = (filters) => Object.values(filters || {}).some((v) => String(v).trim())

const FilterRow = ({ columns, filters, onChange }) => (
  <tr className="bg-white">
    {columns.map((col) => (
      <th key={col.key} className={`px-2 py-1.5 ${ALIGN[col.align || 'right']}`}>
        {col.filter === false ? null : (
          <input
            type="text"
            value={filters[col.key] || ''}
            onChange={(e) => onChange(col.key, e.target.value)}
            aria-label={`筛选${col.label || col.key}`}
            className="w-full min-w-[3rem] px-1.5 py-1 text-xs border border-gray-200 rounded bg-white text-gray-600 placeholder:text-gray-300 focus:outline-none focus:ring-1 focus:ring-blue-300"
          />
        )}
      </th>
    ))}
  </tr>
)

const ClearFilters = ({ visible, onClick }) => {
  if (!visible) return null
  return (
    <div className="flex justify-end px-4 pt-2">
      <button type="button" onClick={onClick} className="text-xs text-gray-500 hover:text-blue-600">
        清除筛选
      </button>
    </div>
  )
}

const PIE_COLORS = ['#2563eb', '#06b6d4', '#7c3aed', '#f97316', '#10b981', '#ec4899', '#4f46e5', '#64748b']

const polar = (cx, cy, r, deg) => {
  const rad = ((deg - 90) * Math.PI) / 180
  return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)]
}

const slicePath = (cx, cy, r, start, end) => {
  if (end - start >= 359.999) {
    return `M ${cx} ${cy - r} A ${r} ${r} 0 1 1 ${cx} ${cy + r} A ${r} ${r} 0 1 1 ${cx} ${cy - r} Z`
  }
  const [x1, y1] = polar(cx, cy, r, start)
  const [x2, y2] = polar(cx, cy, r, end)
  const large = end - start > 180 ? 1 : 0
  return `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`
}

const FeaturePie = ({ items }) => {
  const rows = (items || []).filter((x) => Number(x.total_tokens) > 0)
  const total = rows.reduce((s, x) => s + Number(x.total_tokens || 0), 0)
  if (!total) {
    return <p className="px-5 py-4 text-sm text-gray-400">暂无 tokens 数据</p>
  }
  const raw = rows.map((x) => (Number(x.total_tokens) / total) * 100)
  const rounded = raw.map((p) => Math.round(p * 10) / 10)
  const drift = Math.round((100 - rounded.reduce((a, b) => a + b, 0)) * 10) / 10
  if (drift !== 0 && rounded.length) {
    let idx = 0
    for (let i = 1; i < rounded.length; i += 1) {
      if (rounded[i] > rounded[idx]) idx = i
    }
    rounded[idx] = Math.round((rounded[idx] + drift) * 10) / 10
  }
  let cursor = 0
  const slices = rows.map((x, i) => {
    const sweep = (Number(x.total_tokens) / total) * 360
    const start = cursor
    cursor += sweep
    return {
      key: x.feature,
      label: FEATURE_LABELS[x.feature] || x.feature,
      tokens: Number(x.total_tokens),
      pct: rounded[i],
      start,
      end: cursor,
      color: PIE_COLORS[i % PIE_COLORS.length],
    }
  })
  const cx = 80
  const cy = 80
  const r = 72
  return (
    <div className="flex flex-wrap items-center gap-6 px-5 py-4">
      <svg viewBox="0 0 160 160" className="h-40 w-40 shrink-0" role="img" aria-label="按功能 tokens 占比">
        {slices.map((s) => (
          <path key={s.key} d={slicePath(cx, cy, r, s.start, s.end)} fill={s.color}>
            <title>{`${s.label}：${fmtInt(s.tokens)} tokens`}</title>
          </path>
        ))}
      </svg>
      <ul className="space-y-1.5 text-sm">
        {slices.map((s) => (
          <li key={s.key} className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-sm shrink-0" style={{ background: s.color }} />
            <span className="text-gray-700">{s.label}</span>
            <span className="text-gray-400">{Number(s.pct).toFixed(1)}%</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

const TokenBar = ({ value, max }) => {
  const pct = max > 0 ? Math.max(1, Math.min(100, (value / max) * 100)) : 0
  return (
    <div className="flex items-center space-x-2 min-w-[160px]">
      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className="h-full bg-gradient-to-r from-cyan-500 to-blue-600 rounded-full" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-500 w-16 text-right">{fmtTokens(value)}</span>
    </div>
  )
}

const RecordView = ({ data }) => {
  const body = data?.body
  if (typeof body === 'string') {
    const text = body.length > 20000 ? `${body.slice(0, 20000)}\n\n……正文较长，完整内容已保存在该账号文件夹里` : body
    return <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap rounded-lg bg-white p-3 text-sm text-gray-800">{text}</pre>
  }
  const grading = body?.grading_result
  if (grading && Array.isArray(grading.questions)) {
    return (
      <div className="mt-3 space-y-2 rounded-lg bg-white p-3 text-sm">
        <p className="text-gray-700">
          {body.student_name || '学生'} · {body.subject || ''} · 得分 {body.score ?? '—'} · 错 {body.wrong_count ?? '—'} 题
        </p>
        {grading.questions.map((q, i) => (
          <div key={i} className="border-t border-gray-100 pt-2">
            <p className="font-medium text-gray-900">
              {q.is_correct ? '正确' : '错误'} · 第 {q.question_number || i + 1} 题
            </p>
            {q.question_text && <p className="mt-1 whitespace-pre-wrap text-gray-700">{q.question_text}</p>}
            {q.student_answer && <p className="mt-1 text-gray-500">学生答案：{q.student_answer}</p>}
            {q.correct_answer && <p className="text-gray-500">参考答案：{q.correct_answer}</p>}
          </div>
        ))}
        {body.ocr_result && (
          <details className="border-t border-gray-100 pt-2">
            <summary className="cursor-pointer text-gray-500">识别原文</summary>
            <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap text-gray-600">{String(body.ocr_result).slice(0, 8000)}</pre>
          </details>
        )}
      </div>
    )
  }
  const text = JSON.stringify(body ?? data, null, 2)
  return <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap rounded-lg bg-white p-3 text-sm text-gray-800">{text.slice(0, 20000)}</pre>
}

const UsageStats = () => {
  const { isAdmin } = useAuth()
  const { addToast } = useToast()
  const [range, setRange] = useState('all')
  const [customFrom, setCustomFrom] = useState('')
  const [customTo, setCustomTo] = useState('')
  /** 已生效的自定义区间（点「查询」后写入）；与输入框草稿分离，避免改日期就立刻请求 */
  const [appliedCustom, setAppliedCustom] = useState(null)
  const [summary, setSummary] = useState(null)
  const [allTime, setAllTime] = useState(null)
  const [calls, setCalls] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [accounts, setAccounts] = useState([])
  const [dailyQuota, setDailyQuota] = useState(null)
  const [recordAccounts, setRecordAccounts] = useState([])
  const [openAccount, setOpenAccount] = useState('')
  const [recordItems, setRecordItems] = useState([])
  const [recordDetail, setRecordDetail] = useState(null)
  const [recordError, setRecordError] = useState('')
  const [feedbacks, setFeedbacks] = useState([])
  const [feedbackLoading, setFeedbackLoading] = useState(false)
  const [feedbackError, setFeedbackError] = useState('')
  const [dayFiles, setDayFiles] = useState({})
  const [selectedDays, setSelectedDays] = useState(() => new Set())
  const [downloadingDays, setDownloadingDays] = useState(false)
  const [downloadError, setDownloadError] = useState('')
  const [tableFilters, setTableFilters] = useState({})

  const setColFilter = (table, col, value) => {
    setTableFilters((prev) => ({
      ...prev,
      [table]: { ...(prev[table] || {}), [col]: value },
    }))
  }
  const clearColFilters = (table) => {
    setTableFilters((prev) => ({ ...prev, [table]: {} }))
  }

  const rangeParams = useCallback(() => {
    if (range === 'custom' && appliedCustom) {
      const since = dayStartISO(appliedCustom.from)
      const until = dayEndISO(appliedCustom.to)
      if (!since || !until) return {}
      return { since, until }
    }
    const since = rangeToSince(range)
    return since ? { since } : {}
  }, [range, appliedCustom])

  const selectFixedRange = (id) => {
    setCustomFrom('')
    setCustomTo('')
    setAppliedCustom(null)
    setRange(id)
  }

  const applyCustomRange = () => {
    if (!customFrom || !customTo) {
      addToast('请选择开始日期和结束日期', 'error')
      return
    }
    if (customFrom > customTo) {
      addToast('开始日期不能晚于结束日期', 'error')
      return
    }
    setAppliedCustom({ from: customFrom, to: customTo })
    setRange('custom')
  }

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    const params = rangeParams()
    const filtered = Boolean(params.since || params.until)
    try {
      const requests = [
        usageAPI.getSummary(params),
        usageAPI.getCalls({ limit: 500, ...params }),
        usageAPI.getAccounts(params),
      ]
      if (filtered) requests.push(usageAPI.getSummary())
      const [s, c, a, full] = await Promise.all(requests)
      setSummary(s)
      setAllTime(filtered ? full : s)
      setCalls(c?.items || [])
      setAccounts(a?.items || [])
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [rangeParams])

  const loadFeedback = useCallback(async () => {
    if (!isAdmin) return
    setFeedbackLoading(true)
    setFeedbackError('')
    try {
      const data = await feedbackAPI.list()
      setFeedbacks(data?.items || [])
    } catch (e) {
      setFeedbackError(e?.response?.data?.detail || e?.message || '加载失败')
    } finally {
      setFeedbackLoading(false)
    }
  }, [isAdmin])

  const loadDaily = useCallback(async () => {
    try {
      setDailyQuota(await usageAPI.dailyQuota())
    } catch {
      setDailyQuota(null)
    }
  }, [])

  const loadRecordAccounts = useCallback(async () => {
    try {
      const data = await usageAPI.listRecords()
      setRecordAccounts(data?.items || [])
    } catch {
      setRecordAccounts([])
    }
  }, [])

  const loadDayFiles = useCallback(async () => {
    try {
      const data = await usageAPI.recordDays()
      const map = {}
      ;(data?.items || []).forEach((item) => { map[item.day] = item })
      setDayFiles(map)
    } catch {
      setDayFiles({})
    }
  }, [])

  const toggleDay = (day) => {
    setSelectedDays((prev) => {
      const next = new Set(prev)
      if (next.has(day)) next.delete(day)
      else next.add(day)
      return next
    })
  }

  const downloadSelectedDays = async (days) => {
    const picked = [...days]
    if (!picked.length) return
    setDownloadingDays(true)
    setDownloadError('')
    try {
      const blob = await usageAPI.downloadDays(picked)
      const name = picked.length === 1
        ? `用户记录-${picked[0]}.zip`
        : `用户记录-${picked[0]}_${picked[picked.length - 1]}.zip`
      saveBlob(blob, name)
    } catch (e) {
      let message = e?.message || '下载失败'
      const data = e?.response?.data
      if (data instanceof Blob) {
        try {
          const parsed = JSON.parse(await data.text())
          if (parsed?.detail) message = parsed.detail
        } catch {
          // 保留上面的提示
        }
      } else if (e?.response?.data?.detail) {
        message = e.response.data.detail
      }
      setDownloadError(message)
    } finally {
      setDownloadingDays(false)
    }
  }

  const openRecords = async (username) => {
    setOpenAccount(username)
    setRecordDetail(null)
    setRecordError('')
    try {
      const data = await usageAPI.listAccountRecords(username)
      setRecordItems(data?.items || [])
    } catch (e) {
      setRecordItems([])
      setRecordError(e?.response?.data?.detail || e?.message || '加载记录失败')
    }
  }

  const downloadAccount = async (username) => {
    setRecordError('')
    try {
      const blob = await usageAPI.downloadAccount(username)
      saveBlob(blob, `${username}.zip`)
    } catch (e) {
      setRecordError(e?.response?.data?.detail || e?.message || '下载失败')
    }
  }

  const downloadRecord = async (item) => {
    setRecordError('')
    try {
      const blob = await usageAPI.downloadRecord(openAccount, item.kind, item.name)
      saveBlob(blob, item.name)
    } catch (e) {
      setRecordError(e?.response?.data?.detail || e?.message || '下载失败')
    }
  }

  const downloadReadable = async (item) => {
    setRecordError('')
    try {
      const blob = await usageAPI.downloadRecord(openAccount, item.kind, item.name, 'md')
      const stem = item.name.endsWith('.json') ? item.name.slice(0, -5) : item.name
      saveBlob(blob, `${stem}.md`)
    } catch (e) {
      setRecordError(e?.response?.data?.detail || e?.message || '下载失败')
    }
  }

  const openRecord = async (item) => {
    setRecordError('')
    try {
      const data = await usageAPI.getRecord(openAccount, item.kind, item.name)
      setRecordDetail(data)
    } catch (e) {
      setRecordDetail(null)
      setRecordError(e?.response?.data?.detail || e?.message || '打开记录失败')
    }
  }

  useEffect(() => {
    load()
    loadDaily()
    loadRecordAccounts()
    loadDayFiles()
  }, [load, loadDaily, loadRecordAccounts, loadDayFiles])

  useEffect(() => {
    loadFeedback()
  }, [loadFeedback])

  const overview = summary?.overview || {}
  const allOverview = allTime?.overview || {}
  const rangeFiltered = range !== 'all'
  const historyHint = rangeFiltered && !Number(overview.calls) && Number(allOverview.calls)
    ? `所选时间内没有调用；全部历史共 ${fmtInt(allOverview.total_tokens)} tokens（${String(allOverview.first_ts || '').slice(0, 10)} 至 ${String(allOverview.last_ts || '').slice(0, 10)}），点「全部」查看`
    : ''
  const moduleRangeHint = overview.first_ts
    ? `${rangeFiltered ? '所选区间' : '全部历史'} ${String(overview.first_ts).slice(0, 10)} 至 ${String(overview.last_ts).slice(0, 10)}。作业里的图片识别记在「识别」，错题本里的识别和变式题记在「错题本」。`
    : (rangeFiltered && historyHint ? historyHint : '还没有调用记录')
  const byFeature = summary?.by_feature || []
  const byModule = useMemo(() => {
    const rows = summary?.by_module?.length
      ? summary.by_module
      : (summary?.by_feature || []).map((row) => ({ ...row, module: row.feature === 'unknown' ? 'other' : row.feature }))
    const map = new Map(rows.map((row) => [row.module, row]))
    return MODULES.map((item) => ({
      ...item,
      calls: 0,
      failed: 0,
      success: 0,
      success_rate: 0,
      prompt_tokens: 0,
      completion_tokens: 0,
      total_tokens: 0,
      avg_total_tokens_per_call: 0,
      ...(map.get(item.id) || {}),
    })).filter((row) => row.always || Number(row.calls) > 0)
  }, [summary])
  const historyAccount = accounts.find(isHistoryAccount)
  const maxAccountTokens = useMemo(
    () => accounts.reduce((m, x) => Math.max(m, x.total_tokens || 0), 0),
    [accounts]
  )
  const byModel = summary?.by_model || []
  const activeCustomFrom = appliedCustom?.from || ''
  const activeCustomTo = appliedCustom?.to || ''
  const byDay = useMemo(() => {
    const rows = new Map((summary?.by_day || []).map((d) => [d.day, { ...d }]))
    Object.keys(dayFiles).forEach((day) => {
      if (!dayWithinRange(day, range, activeCustomFrom, activeCustomTo)) return
      if (!rows.has(day)) rows.set(day, { day, total_tokens: 0, calls: 0, failed: 0 })
    })
    return [...rows.values()]
      .filter((d) => dayWithinRange(d.day, range, activeCustomFrom, activeCustomTo))
      .sort((a, b) => String(b.day).localeCompare(String(a.day)))
  }, [summary, dayFiles, range, activeCustomFrom, activeCustomTo])
  const downloadableDays = useMemo(
    () => byDay.map((d) => d.day).filter((day) => (dayFiles[day]?.files || 0) > 0),
    [byDay, dayFiles],
  )
  const allDownloadableSelected = downloadableDays.length > 0 && downloadableDays.every((day) => selectedDays.has(day))
  const maxFeatureTokens = useMemo(
    () => byFeature.reduce((m, x) => Math.max(m, x.total_tokens || 0), 0),
    [byFeature]
  )
  const maxDayTokens = useMemo(
    () => byDay.reduce((m, x) => Math.max(m, x.total_tokens || 0), 0),
    [byDay]
  )

  const callFilters = tableFilters.calls || {}
  const filteredCalls = applyFilters(calls, callFilters, {
    time: (c) => fmtTime(c.ts_utc),
    feature: (c) => MODULE_LABELS[c.module] || FEATURE_LABELS[c.feature] || c.feature,
    owner: (c) => callOwner(c, accounts),
    model: (c) => c.model,
    status: (c) => (c.success ? '成功' : `失败 ${c.error || ''}`),
    elapsed: (c) => numText(c.elapsed_seconds, `${fmtFloat(c.elapsed_seconds)}s`),
    prompt: (c) => numText(c.usage?.prompt_tokens),
    completion: (c) => numText(c.usage?.completion_tokens),
    tokens: (c) => numText(c.usage?.total_tokens),
    task: (c) => c.task_id || '-',
  })

  const moduleFilters = tableFilters.modules || {}
  const filteredModules = applyFilters(byModule, moduleFilters, {
    label: (row) => row.label,
    tokens: (row) => numText(row.total_tokens),
    share: (row) => {
      const share = Number(overview.total_tokens) > 0
        ? (Number(row.total_tokens) / Number(overview.total_tokens)) * 100
        : 0
      return `${fmtPct(share)} ${share}`
    },
    calls: (row) => numText(row.calls),
    failed: (row) => numText(row.failed),
    prompt: (row) => numText(row.prompt_tokens),
    completion: (row) => numText(row.completion_tokens),
    avg: (row) => numText(Math.round(row.avg_total_tokens_per_call || 0)),
  })

  const quotaFilters = tableFilters.quota || {}
  const filteredQuota = applyFilters(dailyQuota?.items || [], quotaFilters, {
    username: (row) => row.username || '—',
    name: (row) => row.display_name || '—',
    tokens: (row) => numText(row.tokens),
    grade: (row) => numText(row.grade),
    lessonplan: (row) => numText(row.lessonplan),
    variant: (row) => numText(row.variant),
    feedback: (row) => (row.feedback ? '已提交' : '未提交'),
    tier: (row) => (row.tier === 'extended' ? '后续额度' : '基础额度'),
  })

  const accountFilters = tableFilters.accounts || {}
  const filteredAccounts = applyFilters(accounts, accountFilters, {
    username: (a) => a.username || '—',
    name: (a) => accountName(a),
    role: (a) => (a.role === 'admin' ? '管理员' : a.auth_method === 'phone_code' ? '手机号' : a.role === 'teacher' ? '教师' : isHistoryAccount(a) ? '历史日志' : '—'),
    grade: (a) => moduleText(a, 'grade'),
    lessonplan: (a) => moduleText(a, 'lessonplan'),
    notebook: (a) => moduleText(a, 'notebook'),
    ocr: (a) => moduleText(a, 'ocr'),
    variant: (a) => moduleText(a, 'variant'),
    probe: (a) => moduleText(a, 'probe'),
    total: (a) => numText(a.total_tokens),
    calls: (a) => numText(a.calls),
    records: (a) => (a.username && Number(a.calls) > 0 ? '记录' : ''),
  })

  const featureFilters = tableFilters.features || {}
  const filteredFeatures = applyFilters(byFeature, featureFilters, {
    feature: (f) => `${FEATURE_LABELS[f.feature] || f.feature} ${f.feature}`,
    tokens: (f) => numText(f.total_tokens),
    calls: (f) => numText(f.calls),
    success: (f) => `${fmtPct(f.success_rate)} ${f.success_rate}`,
    avg: (f) => numText(Math.round(f.avg_total_tokens_per_call)),
    elapsed: (f) => numText(f.avg_elapsed_seconds, `${fmtFloat(f.avg_elapsed_seconds)}s`),
  })

  const modelFilters = tableFilters.models || {}
  const filteredModels = applyFilters(byModel, modelFilters, {
    model: (m) => m.model,
    calls: (m) => numText(m.calls),
    success: (m) => `${fmtPct(m.success_rate)} ${m.success_rate}`,
    tokens: (m) => numText(m.total_tokens),
    elapsed: (m) => numText(m.avg_elapsed_seconds, `${fmtFloat(m.avg_elapsed_seconds)}s`),
  })

  const dayFilters = tableFilters.days || {}
  const filteredDays = applyFilters(byDay, dayFilters, {
    day: (d) => d.day,
    tokens: (d) => numText(d.total_tokens),
    calls: (d) => numText(d.calls),
    failed: (d) => numText(d.failed),
    files: (d) => numText(dayFiles[d.day]?.files || 0),
  })

  const feedbackFilters = tableFilters.feedbacks || {}
  const filteredFeedbacks = applyFilters(feedbacks, feedbackFilters, {
    time: (f) => fmtTime(f.created_at),
    user: (f) => `${f.user_id != null ? `用户 #${f.user_id}` : '未知用户'} ${f.is_guest ? '体验账号' : '正式账号'}`,
    topics: (f) => (f.topics || []).map((t) => {
      const name = typeof t === 'string' ? t : (t?.name || '')
      const detail = typeof t === 'object' && t?.detail ? String(t.detail) : ''
      return `${name} ${detail}`
    }).join(' '),
    content: (f) => f.content || '',
    contact: (f) => f.contact || '',
  })

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-xl font-bold text-gray-900">模型用量统计</h2>
          <p className="text-sm text-gray-500 mt-1">
            全部历史调用都在这里，包含早期没有记到账号上的用量。各模块的次数和 token 可以直接用来统计。
          </p>
        </div>
        <div className="flex flex-col items-stretch sm:items-end gap-2">
          <div className="flex items-center flex-wrap gap-3 justify-end">
            <div className="flex space-x-1 bg-gray-100 rounded-xl p-1">
              {RANGES.map((r) => (
                <button
                  key={r.id}
                  type="button"
                  onClick={() => selectFixedRange(r.id)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    range === r.id ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>
            <button
              type="button"
              onClick={() => { load(); loadDaily(); if (isAdmin) loadFeedback() }}
              disabled={loading || feedbackLoading}
              className="inline-flex items-center space-x-2 px-4 py-2 border border-gray-300 rounded-xl text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50"
            >
              {loading || feedbackLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              <span>刷新</span>
            </button>
          </div>
          <div className="flex flex-wrap items-center gap-2 justify-end">
            <span className={`text-sm ${range === 'custom' ? 'text-gray-900 font-medium' : 'text-gray-500'}`}>自定义</span>
            <input
              type="date"
              value={customFrom}
              onChange={(e) => setCustomFrom(e.target.value)}
              aria-label="开始日期"
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm text-gray-700 bg-white"
            />
            <span className="text-sm text-gray-400">至</span>
            <input
              type="date"
              value={customTo}
              onChange={(e) => setCustomTo(e.target.value)}
              aria-label="结束日期"
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm text-gray-700 bg-white"
            />
            <button
              type="button"
              onClick={applyCustomRange}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium border transition-all ${
                range === 'custom'
                  ? 'bg-white border-gray-300 text-gray-900 shadow-sm'
                  : 'bg-gray-100 border-transparent text-gray-600 hover:bg-gray-200'
              }`}
            >
              查询
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="flex items-center space-x-2 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          <AlertTriangle className="h-4 w-4" />
          <span>统计数据加载失败：{String(error)}</span>
        </div>
      )}

      <div className={`grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 transition-opacity ${loading ? 'opacity-60' : ''}`}>
        <KpiCard
          icon={Activity}
          label="总调用"
          value={fmtInt(overview.calls)}
          note={`成功 ${fmtInt(overview.success)} · 失败 ${fmtInt(overview.failed)}`}
          color="bg-blue-50 text-blue-600"
        />
        <KpiCard
          icon={CheckCircle}
          label="成功率"
          value={fmtPct(overview.success_rate)}
          note={`涉及任务 ${fmtInt(overview.task_count)} 个`}
          color="bg-green-50 text-green-600"
        />
        <KpiCard
          icon={Coins}
          label="总 tokens"
          value={fmtTokens(overview.total_tokens)}
          note={historyHint || `输入 ${fmtTokens(overview.prompt_tokens)} · 输出 ${fmtTokens(overview.completion_tokens)}`}
          color="bg-purple-50 text-purple-600"
        />
        <KpiCard
          icon={Timer}
          label="平均耗时"
          value={`${fmtFloat(overview.avg_elapsed_seconds)}s`}
          note={`中位数 ${fmtFloat(overview.median_elapsed_seconds)}s`}
          color="bg-orange-50 text-orange-600"
        />
      </div>

      <Card
        title="全部历史调用"
        hint="每一次模型调用都在这里，不随上面的「今天 / 7天」变化。没有教师编号的显示为「未记到老师名下」。"
      >
        <ClearFilters visible={hasActiveFilters(callFilters)} onClick={() => clearColFilters('calls')} />
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <Th align="left">时间</Th>
              <Th align="left">功能</Th>
              <Th align="left">归属</Th>
              <Th align="left">模型</Th>
              <Th align="left">状态</Th>
              <Th>耗时</Th>
              <Th>输入</Th>
              <Th>输出</Th>
              <Th>总 tokens</Th>
              <Th align="left">任务</Th>
            </tr>
            <FilterRow
              filters={callFilters}
              onChange={(col, value) => setColFilter('calls', col, value)}
              columns={[
                { key: 'time', label: '时间', align: 'left' },
                { key: 'feature', label: '功能', align: 'left' },
                { key: 'owner', label: '归属', align: 'left' },
                { key: 'model', label: '模型', align: 'left' },
                { key: 'status', label: '状态', align: 'left' },
                { key: 'elapsed', label: '耗时' },
                { key: 'prompt', label: '输入' },
                { key: 'completion', label: '输出' },
                { key: 'tokens', label: '总 tokens' },
                { key: 'task', label: '任务', align: 'left' },
              ]}
            />
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filteredCalls.length === 0 && <EmptyRow cols={10} text={hasActiveFilters(callFilters) ? '无匹配项' : '暂无数据'} />}
            {filteredCalls.map((c) => (
              <tr
                key={c.call_id}
                title={c.success ? '' : c.error || '调用失败'}
                className={c.success ? 'hover:bg-gray-50' : 'bg-red-50 hover:bg-red-100 cursor-help'}
              >
                <Td align="left" className="text-gray-500">{fmtTime(c.ts_utc)}</Td>
                <Td align="left">{MODULE_LABELS[c.module] || FEATURE_LABELS[c.feature] || c.feature}</Td>
                <Td align="left">{callOwner(c, accounts)}</Td>
                <Td align="left" className="font-mono">{c.model}</Td>
                <Td align="left">
                  {c.success ? (
                    <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full">成功</span>
                  ) : (
                    <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs rounded-full">失败</span>
                  )}
                </Td>
                <Td>{fmtFloat(c.elapsed_seconds)}s</Td>
                <Td>{fmtInt(c.usage?.prompt_tokens)}</Td>
                <Td>{fmtInt(c.usage?.completion_tokens)}</Td>
                <Td className="font-medium text-gray-900">{fmtInt(c.usage?.total_tokens)}</Td>
                <Td align="left" className="font-mono text-xs text-gray-400">{c.task_id || '-'}</Td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card title="各模块用量" hint={moduleRangeHint}>
        {historyAccount && (
          <p className="px-5 pt-3 text-sm text-gray-600">
            其中 {fmtInt(historyAccount.calls)} 次、{fmtTokens(historyAccount.total_tokens)} tokens 当时没有教师编号。调用都在上方「全部历史调用」里，不会出现在 admin 这一行的「记录」中。
          </p>
        )}
        <ClearFilters visible={hasActiveFilters(moduleFilters)} onClick={() => clearColFilters('modules')} />
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <Th align="left">模块</Th>
              <Th align="left">Tokens</Th>
              <Th>占比</Th>
              <Th>调用</Th>
              <Th>失败</Th>
              <Th>输入</Th>
              <Th>输出</Th>
              <Th>平均每次</Th>
            </tr>
            <FilterRow
              filters={moduleFilters}
              onChange={(col, value) => setColFilter('modules', col, value)}
              columns={[
                { key: 'label', label: '模块', align: 'left' },
                { key: 'tokens', label: 'Tokens', align: 'left' },
                { key: 'share', label: '占比' },
                { key: 'calls', label: '调用' },
                { key: 'failed', label: '失败' },
                { key: 'prompt', label: '输入' },
                { key: 'completion', label: '输出' },
                { key: 'avg', label: '平均每次' },
              ]}
            />
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filteredModules.length === 0 && <EmptyRow cols={8} text={hasActiveFilters(moduleFilters) ? '无匹配项' : '暂无数据'} />}
            {filteredModules.map((row) => {
              const share = Number(overview.total_tokens) > 0
                ? (Number(row.total_tokens) / Number(overview.total_tokens)) * 100
                : 0
              return (
                <tr key={row.id} className="hover:bg-gray-50">
                  <Td align="left" className="font-medium text-gray-900">{row.label}</Td>
                  <Td align="left"><TokenBar value={row.total_tokens} max={Number(overview.total_tokens) || 0} /></Td>
                  <Td>{fmtPct(share)}</Td>
                  <Td>{fmtInt(row.calls)}</Td>
                  <Td className={row.failed > 0 ? 'text-red-600' : ''}>{fmtInt(row.failed)}</Td>
                  <Td>{fmtInt(row.prompt_tokens)}</Td>
                  <Td>{fmtInt(row.completion_tokens)}</Td>
                  <Td>{fmtInt(Math.round(row.avg_total_tokens_per_call || 0))}</Td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </Card>

      <Card title="今日额度" hint="按北京时间当天统计。提交过意见的账号会升到后续额度。这里的数字只在管理后台显示">
        <div className="overflow-x-auto">
          <ClearFilters visible={hasActiveFilters(quotaFilters)} onClick={() => clearColFilters('quota')} />
          <table className="w-full min-w-[720px]">
            <thead className="bg-gray-50">
              <tr>
                <Th align="left">账号</Th>
                <Th align="left">姓名</Th>
                <Th align="left">Tokens</Th>
                <Th>批改</Th>
                <Th>教案</Th>
                <Th>变式题</Th>
                <Th align="left">今日意见</Th>
                <Th align="left">档位</Th>
              </tr>
              <FilterRow
                filters={quotaFilters}
                onChange={(col, value) => setColFilter('quota', col, value)}
                columns={[
                  { key: 'username', label: '账号', align: 'left' },
                  { key: 'name', label: '姓名', align: 'left' },
                  { key: 'tokens', label: 'Tokens', align: 'left' },
                  { key: 'grade', label: '批改' },
                  { key: 'lessonplan', label: '教案' },
                  { key: 'variant', label: '变式题' },
                  { key: 'feedback', label: '今日意见', align: 'left' },
                  { key: 'tier', label: '档位', align: 'left' },
                ]}
              />
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredQuota.length === 0 && <EmptyRow cols={8} text={hasActiveFilters(quotaFilters) ? '无匹配项' : '暂无数据'} />}
              {filteredQuota.map((row) => (
                <tr key={row.user_id} className="hover:bg-gray-50">
                  <Td align="left" className="font-mono text-gray-900">{row.username || '—'}</Td>
                  <Td align="left">{row.display_name || '—'}</Td>
                  <Td align="left">{fmtInt(row.tokens)}</Td>
                  <Td>{fmtInt(row.grade)}</Td>
                  <Td>{fmtInt(row.lessonplan)}</Td>
                  <Td>{fmtInt(row.variant)}</Td>
                  <Td align="left" className={row.feedback ? 'text-green-700' : 'text-gray-400'}>{row.feedback ? '已提交' : '未提交'}</Td>
                  <Td align="left">{row.tier === 'extended' ? '后续额度' : '基础额度'}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title="按账号" hint="每格是「调用次数 · tokens」。历史日志是早期没有教师编号的调用，已计入上方各模块合计，不是某个老师的账单">
        <ClearFilters visible={hasActiveFilters(accountFilters)} onClick={() => clearColFilters('accounts')} />
        <table className="w-full min-w-[1100px]">
          <thead className="bg-gray-50">
            <tr>
              <Th align="left">账号</Th>
              <Th align="left">姓名</Th>
              <Th align="left">身份</Th>
              <Th align="left">批改</Th>
              <Th align="left">教案</Th>
              <Th align="left">错题本</Th>
              <Th align="left">识别</Th>
              <Th align="left">变式题</Th>
              <Th align="left">评测</Th>
              <Th align="left">合计</Th>
              <Th>调用</Th>
              <Th>内容</Th>
            </tr>
            <FilterRow
              filters={accountFilters}
              onChange={(col, value) => setColFilter('accounts', col, value)}
              columns={[
                { key: 'username', label: '账号', align: 'left' },
                { key: 'name', label: '姓名', align: 'left' },
                { key: 'role', label: '身份', align: 'left' },
                { key: 'grade', label: '批改', align: 'left' },
                { key: 'lessonplan', label: '教案', align: 'left' },
                { key: 'notebook', label: '错题本', align: 'left' },
                { key: 'ocr', label: '识别', align: 'left' },
                { key: 'variant', label: '变式题', align: 'left' },
                { key: 'probe', label: '评测', align: 'left' },
                { key: 'total', label: '合计', align: 'left' },
                { key: 'calls', label: '调用' },
                { key: 'records', label: '内容' },
              ]}
            />
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filteredAccounts.length === 0 && <EmptyRow cols={12} text={hasActiveFilters(accountFilters) ? '无匹配项' : '暂无数据'} />}
            {filteredAccounts.map((a) => (
              <tr key={`${a.id ?? 'none'}-${a.username}`} className="hover:bg-gray-50">
                <Td align="left" className="font-mono text-gray-900">{a.username || '—'}</Td>
                <Td align="left">{accountName(a)}</Td>
                <Td align="left" className="text-gray-500">
                  {a.role === 'admin' ? '管理员' : a.auth_method === 'phone_code' ? '手机号' : a.role === 'teacher' ? '教师' : isHistoryAccount(a) ? '历史日志' : '—'}
                </Td>
                <Td align="left">{moduleText(a, 'grade')}</Td>
                <Td align="left">{moduleText(a, 'lessonplan')}</Td>
                <Td align="left">{moduleText(a, 'notebook')}</Td>
                <Td align="left">{moduleText(a, 'ocr')}</Td>
                <Td align="left">{moduleText(a, 'variant')}</Td>
                <Td align="left">{moduleText(a, 'probe')}</Td>
                <Td align="left"><TokenBar value={a.total_tokens} max={maxAccountTokens} /></Td>
                <Td>{fmtInt(a.calls)}</Td>
                <Td>
                  {a.username && Number(a.calls) > 0 && (
                    <button type="button" className="text-blue-600 hover:underline" onClick={() => openRecords(a.username)}>
                      记录
                    </button>
                  )}
                </Td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card title="使用记录" hint="按登录账号分文件夹保存的教案、批改和变式题。老师在自己的页面里删除后，这里仍然保留。下载的压缩包里有留存 JSON，教案正文在 body 字段，同时附有可直接打开的 md">
        {recordAccounts.length === 0 && (
          <p className="px-5 py-8 text-sm text-gray-400">还没有留存的生成内容。老师生成教案或批改完成后会出现在这里。</p>
        )}
        <div className="divide-y divide-gray-100">
          {recordAccounts.map((folder) => (
            <div key={folder.username}>
              <div className="flex items-center justify-between gap-3 px-5 py-3 hover:bg-gray-50">
                <button
                  type="button"
                  className="min-w-0 flex-1 text-left"
                  onClick={() => openAccount === folder.username ? setOpenAccount('') : openRecords(folder.username)}
                >
                  <span className="font-mono text-sm text-gray-900">{folder.username}</span>
                </button>
                <span className="shrink-0 text-xs text-gray-500">
                  教案 {folder.counts?.lessonplan || 0} · 批改 {folder.counts?.grade || 0} · 变式题 {folder.counts?.variant || 0}
                </span>
                <button
                  type="button"
                  className="shrink-0 text-sm text-blue-600 hover:underline"
                  onClick={() => downloadAccount(folder.username)}
                >
                  下载
                </button>
              </div>
              {openAccount === folder.username && (
                <div className="bg-gray-50 px-5 py-3">
                  {recordError && <p className="mb-2 text-sm text-red-600">{recordError}</p>}
                  {recordItems.length === 0 && <p className="text-sm text-gray-400">这个账号还没有记录</p>}
                  <ul className="space-y-1">
                    {recordItems.map((item) => (
                      <li key={item.name} className="flex items-center justify-between gap-3">
                        <button type="button" className="min-w-0 text-left text-sm text-blue-700 hover:underline" onClick={() => openRecord(item)}>
                          <span className="mr-2 text-gray-400">{KIND_LABELS[item.kind] || item.kind}</span>
                          {item.title || item.name}
                          <span className="ml-2 text-xs text-gray-400">{fmtTime(item.saved_at)}</span>
                        </button>
                        <span className="flex shrink-0 items-center gap-2">
                          <button type="button" className="text-xs text-blue-600 hover:underline" onClick={() => downloadReadable(item)}>
                            下载正文
                          </button>
                          <button type="button" className="text-xs text-gray-500 hover:underline" onClick={() => downloadRecord(item)}>
                            原始 JSON
                          </button>
                        </span>
                      </li>
                    ))}
                  </ul>
                  {recordDetail && <RecordView data={recordDetail} />}
                </div>
              )}
            </div>
          ))}
        </div>
      </Card>

      <Card title="按功能" hint="各功能模块的调用与 Token 消耗">
        <FeaturePie items={byFeature} />
        <ClearFilters visible={hasActiveFilters(featureFilters)} onClick={() => clearColFilters('features')} />
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <Th align="left">功能</Th>
              <Th align="left">Tokens</Th>
              <Th>调用</Th>
              <Th>成功率</Th>
              <Th>平均 tokens</Th>
              <Th>平均耗时</Th>
            </tr>
            <FilterRow
              filters={featureFilters}
              onChange={(col, value) => setColFilter('features', col, value)}
              columns={[
                { key: 'feature', label: '功能', align: 'left' },
                { key: 'tokens', label: 'Tokens', align: 'left' },
                { key: 'calls', label: '调用' },
                { key: 'success', label: '成功率' },
                { key: 'avg', label: '平均 tokens' },
                { key: 'elapsed', label: '平均耗时' },
              ]}
            />
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filteredFeatures.length === 0 && <EmptyRow cols={6} text={hasActiveFilters(featureFilters) ? '无匹配项' : '暂无数据'} />}
            {filteredFeatures.map((f) => (
              <tr key={f.feature} className="hover:bg-gray-50">
                <Td align="left">
                  <span className="font-medium text-gray-900">{FEATURE_LABELS[f.feature] || f.feature}</span>
                  <span className="ml-2 text-xs text-gray-400 font-mono">{f.feature}</span>
                </Td>
                <Td align="left"><TokenBar value={f.total_tokens} max={maxFeatureTokens} /></Td>
                <Td>{fmtInt(f.calls)}</Td>
                <Td className={f.failed > 0 ? 'text-red-600' : ''}>{fmtPct(f.success_rate)}</Td>
                <Td>{fmtInt(Math.round(f.avg_total_tokens_per_call))}</Td>
                <Td>{fmtFloat(f.avg_elapsed_seconds)}s</Td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card title="按模型">
          <ClearFilters visible={hasActiveFilters(modelFilters)} onClick={() => clearColFilters('models')} />
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <Th align="left">模型</Th>
                <Th>调用</Th>
                <Th>成功率</Th>
                <Th>总 tokens</Th>
                <Th>平均耗时</Th>
              </tr>
              <FilterRow
                filters={modelFilters}
                onChange={(col, value) => setColFilter('models', col, value)}
                columns={[
                  { key: 'model', label: '模型', align: 'left' },
                  { key: 'calls', label: '调用' },
                  { key: 'success', label: '成功率' },
                  { key: 'tokens', label: '总 tokens' },
                  { key: 'elapsed', label: '平均耗时' },
                ]}
              />
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredModels.length === 0 && <EmptyRow cols={5} text={hasActiveFilters(modelFilters) ? '无匹配项' : '暂无数据'} />}
              {filteredModels.map((m) => (
                <tr key={m.model} className="hover:bg-gray-50">
                  <Td align="left" className="font-mono text-gray-900">{m.model}</Td>
                  <Td>{fmtInt(m.calls)}</Td>
                  <Td className={m.failed > 0 ? 'text-red-600' : ''}>{fmtPct(m.success_rate)}</Td>
                  <Td>{fmtInt(m.total_tokens)}</Td>
                  <Td>{fmtFloat(m.avg_elapsed_seconds)}s</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <Card
          title="按日期"
          hint="勾选日期后打包下载。压缩包里是留存 JSON（教案正文在 body 字段），并附有可直接打开的 md。"
          right={(
            <button
              type="button"
              disabled={downloadingDays || selectedDays.size === 0}
              onClick={() => downloadSelectedDays([...selectedDays].sort())}
              className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {downloadingDays ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
              下载选中
            </button>
          )}
        >
          {downloadError && <p className="px-5 py-2 text-sm text-red-600">{downloadError}</p>}
          <ClearFilters visible={hasActiveFilters(dayFilters)} onClick={() => clearColFilters('days')} />
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <Th align="left">
                  <input
                    type="checkbox"
                    aria-label="全选有文件的日期"
                    checked={allDownloadableSelected}
                    disabled={downloadableDays.length === 0}
                    onChange={() => {
                      setSelectedDays(allDownloadableSelected ? new Set() : new Set(downloadableDays))
                    }}
                  />
                </Th>
                <Th align="left">日期</Th>
                <Th align="left">Tokens</Th>
                <Th>调用</Th>
                <Th>失败</Th>
                <Th>文件</Th>
              </tr>
              <FilterRow
                filters={dayFilters}
                onChange={(col, value) => setColFilter('days', col, value)}
                columns={[
                  { key: 'check', label: '选择', align: 'left', filter: false },
                  { key: 'day', label: '日期', align: 'left' },
                  { key: 'tokens', label: 'Tokens', align: 'left' },
                  { key: 'calls', label: '调用' },
                  { key: 'failed', label: '失败' },
                  { key: 'files', label: '文件' },
                ]}
              />
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredDays.length === 0 && <EmptyRow cols={6} text={hasActiveFilters(dayFilters) ? '无匹配项' : '暂无数据'} />}
              {filteredDays.map((d) => {
                const files = dayFiles[d.day]?.files || 0
                return (
                  <tr key={d.day} className="hover:bg-gray-50">
                    <Td align="left">
                      <input
                        type="checkbox"
                        aria-label={`选择 ${d.day}`}
                        checked={selectedDays.has(d.day)}
                        disabled={files === 0}
                        onChange={() => toggleDay(d.day)}
                      />
                    </Td>
                    <Td align="left" className="font-mono">{d.day}</Td>
                    <Td align="left"><TokenBar value={d.total_tokens} max={maxDayTokens} /></Td>
                    <Td>{fmtInt(d.calls)}</Td>
                    <Td className={d.failed > 0 ? 'text-red-600 font-medium' : 'text-gray-400'}>{fmtInt(d.failed)}</Td>
                    <Td>
                      {files > 0 ? (
                        <button
                          type="button"
                          className="text-blue-600 hover:underline"
                          onClick={() => downloadSelectedDays([d.day])}
                        >
                          {fmtInt(files)} 份
                        </button>
                      ) : (
                        <span className="text-gray-400">0</span>
                      )}
                    </Td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </Card>
      </div>

      {summary && (
        <p className="text-xs text-gray-400">
          统计于 {fmtTime(summary.generated_at)}
        </p>
      )}

      {isAdmin && (
        <Card title="用户反馈" hint="最近 200 条，按时间倒序">
          {feedbackError && (
            <div className="flex items-center space-x-2 px-4 py-3 text-sm text-red-700">
              <AlertTriangle className="h-4 w-4" />
              <span>反馈加载失败：{String(feedbackError)}</span>
            </div>
          )}
          <ClearFilters visible={hasActiveFilters(feedbackFilters)} onClick={() => clearColFilters('feedbacks')} />
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <Th align="left">时间</Th>
                <Th align="left">提交人</Th>
                <Th align="left">问题标签</Th>
                <Th align="left">意见内容</Th>
                <Th align="left">联系方式</Th>
              </tr>
              <FilterRow
                filters={feedbackFilters}
                onChange={(col, value) => setColFilter('feedbacks', col, value)}
                columns={[
                  { key: 'time', label: '时间', align: 'left' },
                  { key: 'user', label: '提交人', align: 'left' },
                  { key: 'topics', label: '问题标签', align: 'left' },
                  { key: 'content', label: '意见内容', align: 'left' },
                  { key: 'contact', label: '联系方式', align: 'left' },
                ]}
              />
            </thead>
            <tbody className="divide-y divide-gray-100">
              {!feedbackError && filteredFeedbacks.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-sm text-gray-400">
                    {feedbackLoading ? '加载中…' : hasActiveFilters(feedbackFilters) ? '无匹配项' : '暂无反馈'}
                  </td>
                </tr>
              )}
              {filteredFeedbacks.map((f) => (
                <tr key={f.id} className="hover:bg-gray-50">
                  <Td align="left" className="text-gray-500">{fmtTime(f.created_at)}</Td>
                  <Td align="left">
                    <span className="text-gray-900">
                      {f.user_id != null ? `用户 #${f.user_id}` : '未知用户'}
                    </span>
                    {f.is_guest ? (
                      <span className="ml-2 px-2 py-0.5 bg-amber-50 text-amber-700 text-xs rounded-full">体验账号</span>
                    ) : (
                      <span className="ml-2 px-2 py-0.5 bg-gray-100 text-gray-500 text-xs rounded-full">正式账号</span>
                    )}
                  </Td>
                  <Td align="left" className="!whitespace-normal">
                    {(f.topics || []).length === 0 ? (
                      <span className="text-gray-400">—</span>
                    ) : (
                      <div className="flex flex-col gap-1.5 max-w-xs">
                        {f.topics.map((t, i) => {
                          const name = typeof t === 'string' ? t : (t?.name || '')
                          const detail = typeof t === 'object' && t?.detail ? String(t.detail) : ''
                          if (!name) return null
                          return (
                            <div key={`${name}-${i}`}>
                              <span className="inline-block px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded-full">
                                {name}
                              </span>
                              {detail ? (
                                <div className="mt-0.5 text-xs text-gray-500 whitespace-pre-wrap break-words pl-0.5">
                                  {detail}
                                </div>
                              ) : null}
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </Td>
                  <Td align="left" className="!whitespace-normal max-w-md">
                    {f.content ? (
                      <span className="text-gray-700 whitespace-pre-wrap break-words">{f.content}</span>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </Td>
                  <Td align="left">
                    {f.contact ? (
                      <span className="text-gray-700">{f.contact}</span>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  )
}

export default UsageStats
