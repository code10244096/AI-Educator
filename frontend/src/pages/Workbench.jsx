import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ClipboardCheck, Loader2, AlertTriangle, Inbox, Plus, Upload, ChevronRight, Users, FileText,
  UserPlus, ClipboardList, CheckCircle2,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useClass } from '../context/ClassContext'
import { useTask } from '../context/TaskContext'
import { dashboardAPI } from '../utils/api'
import useAsync from '../hooks/useAsync'
import { Loading, ErrorState, Empty } from '../components/PageState'
import { formatRelative } from '../utils/time'

// 工作台（R1-006）：登录后首页，一眼看到今天要做的事——待复核、批改中、需处理、收集中，最近作业与快捷入口

const greeting = () => {
  const h = new Date().getHours()
  if (h < 6) return '晚上好'
  if (h < 11) return '上午好'
  if (h < 13) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
}

const teacherTitle = (user) => {
  const name = (user?.display_name || '').trim()
  if (!name) return '老师'
  if (name.endsWith('老师')) return name
  return name.length <= 3 ? `${name.slice(0, 1)}老师` : `${name}老师`
}

const homeworkPath = (t, filter) => `/class/${t.class_id}/homework/${t.assignment_id}${filter ? `?filter=${filter}` : ''}`

const formatEta = (seconds) => {
  if (!seconds || seconds <= 0) return ''
  if (seconds < 60) return '预计不到 1 分钟'
  return `预计 ${Math.ceil(seconds / 60)} 分钟`
}

const CARD_TONES = {
  blue: { icon: 'bg-blue-50 text-blue-600', num: 'text-blue-700' },
  sky: { icon: 'bg-sky-50 text-sky-600', num: 'text-sky-700' },
  red: { icon: 'bg-red-50 text-red-600', num: 'text-red-600' },
  amber: { icon: 'bg-amber-50 text-amber-600', num: 'text-amber-700' },
}

const StatCard = ({ icon: Icon, label, value, unit, hint, tone, onClick, active, testId }) => {
  const t = CARD_TONES[tone]
  const clickable = value > 0
  return (
    <button
      type="button"
      onClick={clickable ? onClick : undefined}
      disabled={!clickable}
      data-testid={testId}
      aria-expanded={active || undefined}
      className={`flex min-w-0 flex-col rounded-xl border bg-white p-4 text-left transition-colors ${
        active ? 'border-blue-300 ring-1 ring-blue-200' : 'border-gray-200'
      } ${clickable ? 'hover:border-blue-300 hover:bg-blue-50/30' : 'cursor-default'}`}
    >
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500">{label}</span>
        <span className={`flex h-8 w-8 items-center justify-center rounded-lg ${t.icon}`}>
          <Icon className="h-4 w-4" />
        </span>
      </div>
      <div className="mt-2 flex items-baseline gap-1">
        <span className={`text-2xl font-semibold ${value > 0 ? t.num : 'text-gray-300'}`}>{value}</span>
        <span className="text-sm text-gray-500">{unit}</span>
      </div>
      <div className="mt-1 min-h-[1rem] truncate text-xs text-gray-400">{hint}</div>
    </button>
  )
}

// 三步引导：① 新建班级 ② 导入学生名单 ③ 布置第一次作业
const GuideSteps = ({ data, navigate }) => {
  const firstClass = data.classes[0]
  const hasClass = data.classes.length > 0
  const hasMembers = data.classes.some(c => c.member_count > 0)
  const hasAssignment = data.classes.some(c => c.assignment_count > 0)
  const memberClass = data.classes.find(c => c.member_count > 0) || firstClass
  const steps = [
    {
      title: '新建班级',
      desc: '填写班级名称和年级',
      done: hasClass,
      action: '新建班级',
      icon: Plus,
      onClick: () => navigate('/class?create=1'),
    },
    {
      title: '导入学生名单',
      desc: '粘贴或上传“姓名,性别,学号”名单',
      done: hasMembers,
      action: '导入名单',
      icon: UserPlus,
      disabled: !hasClass,
      onClick: () => firstClass && navigate(`/class/${firstClass.class_id}/members?import=1`),
    },
    {
      title: '布置第一次作业',
      desc: '填写作业名称和参考答案，之后就能批量上传批改',
      done: hasAssignment,
      action: '布置作业',
      icon: ClipboardList,
      disabled: !hasClass,
      onClick: () => memberClass && navigate(`/class/${memberClass.class_id}/homework?create=1`),
    },
  ]
  const current = steps.findIndex(s => !s.done)
  return (
    <section className="rounded-xl border border-blue-100 bg-white p-5" data-testid="workbench-guide">
      <h2 className="text-base font-semibold text-gray-900">三步开始使用</h2>
      <p className="mt-1 text-sm text-gray-500">完成下面三步，就可以上传学生作业，让 AI 帮你批改。</p>
      <ol className="mt-4 grid gap-3 md:grid-cols-3">
        {steps.map((s, i) => {
          const Icon = s.icon
          const isCurrent = i === current
          return (
            <li
              key={s.title}
              className={`flex flex-col rounded-lg border p-4 ${isCurrent ? 'border-blue-200 bg-blue-50/50' : 'border-gray-100'}`}
            >
              <div className="flex items-center gap-2">
                {s.done ? (
                  <CheckCircle2 className="h-5 w-5 text-green-500" />
                ) : (
                  <span className={`flex h-5 w-5 items-center justify-center rounded-full text-xs font-medium ${isCurrent ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600'}`}>
                    {i + 1}
                  </span>
                )}
                <span className="text-sm font-medium text-gray-900">{s.title}</span>
              </div>
              <p className="mt-1 flex-1 text-xs text-gray-500">{s.desc}</p>
              {!s.done && (
                <button
                  type="button"
                  onClick={s.onClick}
                  disabled={s.disabled}
                  className={`mt-3 inline-flex w-fit items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium ${
                    isCurrent ? 'bg-blue-600 text-white hover:bg-blue-700' : 'border border-gray-200 text-gray-600 hover:bg-gray-50'
                  } disabled:cursor-not-allowed disabled:opacity-50`}
                >
                  <Icon className="h-4 w-4" />
                  {s.action}
                </button>
              )}
            </li>
          )
        })}
      </ol>
    </section>
  )
}

const assignmentSummary = (a) => {
  const parts = []
  if (a.total_members > 0) parts.push(`已上传 ${a.uploaded}/${a.total_members}`)
  else parts.push(`已上传 ${a.uploaded}`)
  if (a.missing > 0) parts.push(`未交 ${a.missing}`)
  const waitingGrade = Math.max(0, (a.uploaded || 0) - (a.completed || 0) - (a.processing || 0) - (a.failed || 0))
  if (waitingGrade > 0) parts.push(`待批改 ${waitingGrade}`)
  if (a.processing > 0) parts.push(`批改中 ${a.processing}`)
  parts.push(`已批改 ${a.completed || 0}`)
  if (a.avg_score !== null && a.avg_score !== undefined && a.completed > 0) parts.push(`均分 ${a.avg_score}`)
  return parts.join(' · ')
}

// 还没批完 → 去批改 / 查看进度；批完且有待确认 → 去复核；其余给「查看」
const nextStep = (a) => {
  if ((a.processing || 0) > 0) return { label: '查看进度', filter: 'processing' }
  const waitingGrade = Math.max(0, (a.uploaded || 0) - (a.completed || 0) - (a.processing || 0) - (a.failed || 0))
  if (waitingGrade > 0 || ((a.completed || 0) === 0 && (a.uploaded || 0) > 0)) return { label: '去批改', filter: 'pending' }
  if ((a.pending_review || 0) > 0) return { label: '去复核', filter: 'review' }
  return { label: '查看', filter: '' }
}

const AssignmentBadges = ({ a }) => (
  <div className="flex flex-wrap items-center gap-1.5">
    {a.processing > 0 && <span className="rounded-full bg-sky-50 px-2 py-0.5 text-xs text-sky-700">批改中 {a.processing}</span>}
    {a.pending_review > 0 && <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-700">待复核 {a.pending_review}</span>}
    {a.failed > 0 && <span className="rounded-full bg-red-50 px-2 py-0.5 text-xs text-red-600">失败 {a.failed}</span>}
    {a.missing > 0 && <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-700">未交 {a.missing}</span>}
  </div>
)

// “布置作业”：一个班直接进；多个班先选班
const AssignButton = ({ classes, navigate }) => {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  useEffect(() => {
    if (!open) return undefined
    const onClick = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [open])

  const handle = () => {
    if (classes.length === 0) navigate('/class?create=1')
    else if (classes.length === 1) navigate(`/class/${classes[0].id}/homework?create=1`)
    else setOpen(v => !v)
  }
  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={handle}
        className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
      >
        <Plus className="h-4 w-4" />
        布置作业
      </button>
      {open && (
        <div className="absolute right-0 z-20 mt-1 w-48 rounded-lg border border-gray-200 bg-white py-1 shadow-lg" role="menu">
          <div className="px-3 py-1.5 text-xs text-gray-400">选择班级</div>
          {classes.map(c => (
            <button
              key={c.id}
              type="button"
              role="menuitem"
              onClick={() => navigate(`/class/${c.id}/homework?create=1`)}
              className="block w-full truncate px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50"
            >
              {c.name}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

const CARDS = [
  { key: 'review', count: 'pending_review', label: '待复核', unit: '份', icon: ClipboardCheck, tone: 'blue' },
  { key: 'processing', count: 'processing', label: '批改中', unit: '份', icon: Loader2, tone: 'sky' },
  { key: 'failed', count: 'failed', label: '需处理', unit: '份失败', icon: AlertTriangle, tone: 'red' },
  { key: 'missing', count: 'collecting', label: '收集中', unit: '次作业', icon: Inbox, tone: 'amber' },
]

const Workbench = () => {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { classes } = useClass()
  const { runningCount } = useTask()
  const { data, loading, error, reload } = useAsync(() => dashboardAPI.get(), [])
  const [expanded, setExpanded] = useState(null)
  const [showAllTargets, setShowAllTargets] = useState(false)

  // 有批改在进行时静默刷新（数字随进度变化）；后台任务数变化时也刷新一次
  const processing = data?.counts?.processing || 0
  useEffect(() => {
    if (!processing) return undefined
    const timer = setInterval(() => reload({ silent: true }), 5000)
    return () => clearInterval(timer)
  }, [processing, reload])
  const lastRunning = useRef(runningCount)
  useEffect(() => {
    if (lastRunning.current !== runningCount) reload({ silent: true })
    lastRunning.current = runningCount
  }, [runningCount, reload])

  useEffect(() => {
    document.title = '工作台 - AI 教学助手'
    return () => { document.title = 'AI 教学助手' }
  }, [])

  const hints = useMemo(() => {
    if (!data) return {}
    const c = data.counts
    return {
      review: c.pending_review ? '批改完成，等你确认' : '暂时没有',
      processing: c.processing ? (formatEta(data.eta_seconds) || 'AI 正在批改，可以先忙别的') : '暂时没有',
      failed: c.failed ? '照片模糊或识别失败，需重新上传' : '没有失败的批改',
      missing: c.collecting ? `共 ${c.missing_students} 人还没上传` : '暂时没有',
    }
  }, [data])

  const onCard = (card) => {
    const list = data?.targets?.[card.key] || []
    if (list.length === 1) {
      navigate(homeworkPath(list[0], card.key))
    } else if (list.length > 1) {
      setShowAllTargets(false)
      setExpanded(prev => (prev === card.key ? null : card.key))
    }
  }

  const header = (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="min-w-0">
        <h1 className="text-xl font-semibold text-gray-900">{teacherTitle(user)}，{greeting()}</h1>
        <p className="mt-0.5 text-sm text-gray-500">
          {new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' })}
        </p>
      </div>
      <div className="flex items-center gap-2">
        <AssignButton classes={classes} navigate={navigate} />
        <button
          type="button"
          onClick={() => navigate('/grader')}
          className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          <Upload className="h-4 w-4" />
          上传作业
        </button>
      </div>
    </div>
  )

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
        {header}
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-hidden="true">
          {CARDS.map(c => <div key={c.key} className="h-[116px] animate-pulse rounded-xl border border-gray-100 bg-white" />)}
        </div>
        <Loading variant="skeleton" rows={3} text="正在加载工作台" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
        {header}
        <div className="rounded-xl border border-gray-200 bg-white">
          <ErrorState error={error} title="工作台加载失败" onRetry={() => reload()} />
        </div>
      </div>
    )
  }

  const showGuide = data.classes.length === 0 ||
    !data.classes.some(c => c.member_count > 0) ||
    !data.classes.some(c => c.assignment_count > 0)
  const expandedCard = CARDS.find(c => c.key === expanded)
  const expandedAll = expandedCard ? (data.targets?.[expandedCard.key] || []) : []
  const TARGET_PREVIEW = 5
  const expandedList = showAllTargets ? expandedAll : expandedAll.slice(0, TARGET_PREVIEW)
  const hiddenTargets = expandedAll.length - expandedList.length
  const visibleSum = expandedList.reduce((sum, t) => sum + (t.count || 0), 0)
  const cardTotal = expandedCard ? (data.counts[expandedCard.count] || 0) : 0
  const hiddenAmount = expandedCard?.key === 'missing'
    ? (data.counts.missing_students || 0) - visibleSum
    : cardTotal - visibleSum

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6" data-testid="workbench">
      {header}

      {showGuide && <GuideSteps data={data} navigate={navigate} />}

      <section aria-label="今日待办">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {CARDS.map(card => (
            <StatCard
              key={card.key}
              testId={`card-${card.key}`}
              icon={card.icon}
              label={card.label}
              value={data.counts[card.count] || 0}
              unit={card.key === 'failed' && !(data.counts.failed) ? '' : card.unit}
              hint={hints[card.key]}
              tone={card.tone}
              active={expanded === card.key}
              onClick={() => onCard(card)}
            />
          ))}
        </div>
        {expandedCard && expandedList.length > 0 && (
          <div className="mt-3 rounded-xl border border-gray-200 bg-white">
            <div className="border-b border-gray-100 px-4 py-2.5 text-sm text-gray-500">
              {expandedCard.label}的作业（点击进入）
            </div>
            <ul className="divide-y divide-gray-50">
              {expandedList.map(t => (
                <li key={t.assignment_id}>
                  <button
                    type="button"
                    onClick={() => navigate(homeworkPath(t, expandedCard.key))}
                    className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-gray-50"
                  >
                    <span className="min-w-0 truncate text-sm text-gray-800">{t.class_name} · {t.title}</span>
                    <span className="flex flex-shrink-0 items-center gap-1 text-sm text-gray-500">
                      {t.count} {expandedCard.key === 'missing' ? '人' : '份'}
                      <ChevronRight className="h-4 w-4 text-gray-300" />
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            {hiddenTargets > 0 && (
              <div className="flex items-center justify-between gap-3 border-t border-gray-100 px-4 py-3 text-sm text-gray-600">
                <span>
                  还有 {hiddenTargets} 次
                  {hiddenAmount > 0 ? `（${hiddenAmount} ${expandedCard.key === 'missing' ? '人' : '份'}）` : ''}
                </span>
                <button
                  type="button"
                  onClick={() => setShowAllTargets(true)}
                  className="text-blue-600 hover:underline"
                >
                  查看全部
                </button>
              </div>
            )}
          </div>
        )}
      </section>

      <section className="rounded-xl border border-gray-200 bg-white" aria-label="最近作业">
        <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
          <h2 className="text-base font-semibold text-gray-900">最近作业</h2>
          {data.classes.length > 0 && (
            <button type="button" onClick={() => navigate('/class')} className="text-sm text-blue-600 hover:underline">
              全部班级
            </button>
          )}
        </div>
        {data.recent_assignments.length === 0 ? (
          <Empty
            compact
            icon={ClipboardList}
            title="还没有布置作业"
            desc={data.classes.length ? '布置作业并填写参考答案后，就可以上传学生作业让 AI 批改' : '先新建班级，再布置作业'}
            action={data.classes.length
              ? { label: '布置作业', icon: Plus, onClick: () => navigate(`/class/${data.classes[0].class_id}/homework?create=1`) }
              : { label: '新建班级', icon: Plus, onClick: () => navigate('/class?create=1') }}
          />
        ) : (
          <ul className="divide-y divide-gray-50">
            {data.recent_assignments.map(a => {
              const step = nextStep(a)
              return (
              <li key={a.assignment_id} className="flex items-center gap-3 px-4 py-3 hover:bg-gray-50">
                <button
                  type="button"
                  onClick={() => navigate(homeworkPath(a))}
                  className="flex min-w-0 flex-1 items-center gap-3 text-left"
                >
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium text-gray-900">
                      <span className="text-gray-500">{a.class_name} · </span>{a.title}
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
                      <span className="text-xs text-gray-500">{assignmentSummary(a)}</span>
                      <AssignmentBadges a={a} />
                    </div>
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => navigate(homeworkPath(a, step.filter))}
                  className="flex-shrink-0 rounded-lg border border-blue-200 px-3 py-1.5 text-sm text-blue-700 hover:bg-blue-50"
                >
                  {step.label}
                </button>
              </li>
              )
            })}
          </ul>
        )}
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-gray-200 bg-white" aria-label="我的班级">
          <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
            <h2 className="text-base font-semibold text-gray-900">我的班级</h2>
            <button type="button" onClick={() => navigate('/class?create=1')} className="inline-flex items-center text-sm text-blue-600 hover:underline">
              <Plus className="mr-0.5 h-4 w-4" />新建班级
            </button>
          </div>
          {data.classes.length === 0 ? (
            <Empty compact icon={Users} title="还没有班级" desc="新建班级并导入学生名单后，作业和成绩会按班级管理" action={{ label: '新建班级', icon: Plus, onClick: () => navigate('/class?create=1') }} />
          ) : (
            <div className="grid gap-3 p-4 sm:grid-cols-2">
              {data.classes.map(c => (
                <button
                  key={c.class_id}
                  type="button"
                  onClick={() => navigate(`/class/${c.class_id}`)}
                  className="rounded-lg border border-gray-100 p-3 text-left hover:border-blue-200 hover:bg-blue-50/30"
                >
                  <div className="truncate text-sm font-medium text-gray-900">{c.name}</div>
                  <div className="mt-1 text-xs text-gray-500">
                    {c.member_count} 人 · {c.assignment_count} 次作业{c.avg_score !== null && c.avg_score !== undefined ? ` · 均分 ${c.avg_score}` : ''}
                  </div>
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="rounded-xl border border-gray-200 bg-white" aria-label="最近教案">
          <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
            <h2 className="text-base font-semibold text-gray-900">最近教案</h2>
            <button type="button" onClick={() => navigate('/lessonplan')} className="text-sm text-blue-600 hover:underline">
              生成教案
            </button>
          </div>
          {data.recent_lesson_plans.length === 0 ? (
            <Empty compact icon={FileText} title="还没有教案" desc="输入课题，AI 会按新课标生成一份可编辑、可导出的教案" action={{ label: '生成教案', onClick: () => navigate('/lessonplan') }} />
          ) : (
            <ul className="divide-y divide-gray-50">
              {data.recent_lesson_plans.map(p => (
                <li key={p.id}>
                  <button
                    type="button"
                    onClick={() => navigate(`/lessonplan?id=${p.id}`)}
                    className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-gray-50"
                  >
                    <FileText className="h-4 w-4 flex-shrink-0 text-gray-400" />
                    <span className="min-w-0 flex-1 truncate text-sm text-gray-800">{p.title}</span>
                    <span className="flex-shrink-0 text-xs text-gray-400">
                      {p.status === 'processing' ? '生成中' : p.status === 'failed' ? '生成失败' : formatRelative(p.created_at)}
                    </span>
                    <ChevronRight className="h-4 w-4 flex-shrink-0 text-gray-300" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  )
}

export default Workbench
