import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Activity,
  CheckCircle,
  Coins,
  Timer,
  RefreshCw,
  Loader2,
  AlertTriangle,
  BarChart3,
} from 'lucide-react'
import { usageAPI } from '../utils/api'

const RANGES = [
  { id: 'today', label: '今天' },
  { id: '7d', label: '7天' },
  { id: '30d', label: '30天' },
  { id: 'all', label: '全部' },
]

const FEATURE_LABELS = {
  ocr: 'OCR 识别',
  grade: '作业批改',
  lessonplan: '教案生成',
  variant: '变式题',
  seed_grade: '种子批改',
  other: '其他',
  unknown: '未标注',
}

const SOURCE_LABELS = {
  backend: '后端',
  cli: '脚本',
}

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

const fmtInt = (v) => Number(v || 0).toLocaleString('zh-CN')
const fmtFloat = (v, d = 2) => Number(v || 0).toFixed(d)
const fmtPct = (v) => `${Number(v || 0).toFixed(1)}%`

const fmtTokens = (v) => {
  const n = Number(v || 0)
  if (n >= 1e6) return `${(n / 1e6).toFixed(2)}M`
  if (n >= 1e4) return `${(n / 1e3).toFixed(1)}K`
  return fmtInt(n)
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

const Card = ({ title, hint, children, right }) => (
  <div className="bg-white rounded-xl border border-gray-200">
    <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
      <div>
        <h3 className="text-base font-semibold text-gray-900">{title}</h3>
        {hint && <p className="text-xs text-gray-400 mt-0.5">{hint}</p>}
      </div>
      {right}
    </div>
    <div className="overflow-x-auto">{children}</div>
  </div>
)

const ALIGN = { left: 'text-left', right: 'text-right', center: 'text-center' }

const Th = ({ children, align = 'right' }) => (
  <th className={`px-4 py-2.5 text-xs font-medium text-gray-500 whitespace-nowrap ${ALIGN[align]}`}>{children}</th>
)

const Td = ({ children, align = 'right', className = '' }) => (
  <td className={`px-4 py-2.5 text-sm text-gray-700 whitespace-nowrap ${ALIGN[align]} ${className}`}>{children}</td>
)

const EmptyRow = ({ cols }) => (
  <tr>
    <td colSpan={cols} className="px-4 py-8 text-center text-sm text-gray-400">暂无数据</td>
  </tr>
)

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

const UsageStats = () => {
  const [range, setRange] = useState('7d')
  const [summary, setSummary] = useState(null)
  const [calls, setCalls] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    const since = rangeToSince(range)
    const params = since ? { since } : {}
    try {
      const [s, c] = await Promise.all([
        usageAPI.getSummary(params),
        usageAPI.getCalls({ ...params, limit: 50 }),
      ])
      setSummary(s)
      setCalls(c?.items || [])
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [range])

  useEffect(() => {
    load()
  }, [load])

  const overview = summary?.overview || {}
  const byFeature = summary?.by_feature || []
  const byModel = summary?.by_model || []
  const byDay = useMemo(() => [...(summary?.by_day || [])].reverse(), [summary])
  const maxFeatureTokens = useMemo(
    () => byFeature.reduce((m, x) => Math.max(m, x.total_tokens || 0), 0),
    [byFeature]
  )
  const maxDayTokens = useMemo(
    () => byDay.reduce((m, x) => Math.max(m, x.total_tokens || 0), 0),
    [byDay]
  )

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-xl font-bold text-gray-900">模型用量统计</h2>
          <p className="text-sm text-gray-500 mt-1">
            统计每一次大模型调用的次数、成功率、Token 消耗与耗时
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <div className="flex space-x-1 bg-gray-100 rounded-xl p-1">
            {RANGES.map((r) => (
              <button
                key={r.id}
                onClick={() => setRange(r.id)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  range === r.id ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>
          <button
            onClick={load}
            disabled={loading}
            className="inline-flex items-center space-x-2 px-4 py-2 border border-gray-300 rounded-xl text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            <span>刷新</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center space-x-2 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          <AlertTriangle className="h-4 w-4" />
          <span>统计数据加载失败：{String(error)}</span>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
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
          note={`输入 ${fmtTokens(overview.prompt_tokens)} · 输出 ${fmtTokens(overview.completion_tokens)}`}
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

      <Card title="按功能" hint="各功能模块的调用与 Token 消耗">
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
          </thead>
          <tbody className="divide-y divide-gray-100">
            {byFeature.length === 0 && <EmptyRow cols={6} />}
            {byFeature.map((f) => (
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
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <Th align="left">模型</Th>
                <Th>调用</Th>
                <Th>成功率</Th>
                <Th>总 tokens</Th>
                <Th>平均耗时</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {byModel.length === 0 && <EmptyRow cols={5} />}
              {byModel.map((m) => (
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

        <Card title="按日期" hint="按服务器本地日期汇总">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <Th align="left">日期</Th>
                <Th align="left">Tokens</Th>
                <Th>调用</Th>
                <Th>失败</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {byDay.length === 0 && <EmptyRow cols={4} />}
              {byDay.map((d) => (
                <tr key={d.day} className="hover:bg-gray-50">
                  <Td align="left" className="font-mono">{d.day}</Td>
                  <Td align="left"><TokenBar value={d.total_tokens} max={maxDayTokens} /></Td>
                  <Td>{fmtInt(d.calls)}</Td>
                  <Td className={d.failed > 0 ? 'text-red-600 font-medium' : 'text-gray-400'}>{fmtInt(d.failed)}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>

      <Card
        title="最近调用"
        hint="最近 50 次调用；失败行标红，鼠标悬停查看错误信息"
        right={<BarChart3 className="h-4 w-4 text-gray-300" />}
      >
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <Th align="left">时间</Th>
              <Th align="left">功能</Th>
              <Th align="left">来源</Th>
              <Th align="left">模型</Th>
              <Th align="left">状态</Th>
              <Th>耗时</Th>
              <Th>输入</Th>
              <Th>输出</Th>
              <Th>总 tokens</Th>
              <Th align="left">任务</Th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {calls.length === 0 && <EmptyRow cols={10} />}
            {calls.map((c) => (
              <tr
                key={c.call_id}
                title={c.success ? '' : c.error || '调用失败'}
                className={c.success ? 'hover:bg-gray-50' : 'bg-red-50 hover:bg-red-100 cursor-help'}
              >
                <Td align="left" className="text-gray-500">{fmtTime(c.ts_utc)}</Td>
                <Td align="left">{FEATURE_LABELS[c.feature] || c.feature}</Td>
                <Td align="left" className="text-gray-500">{SOURCE_LABELS[c.source] || c.source}</Td>
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

      {summary && (
        <p className="text-xs text-gray-400">
          统计于 {fmtTime(summary.generated_at)} · 日志目录 <span className="font-mono">{summary.log_root}</span>
        </p>
      )}
    </div>
  )
}

export default UsageStats
