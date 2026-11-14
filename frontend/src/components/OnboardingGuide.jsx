import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { ChevronLeft, ChevronRight, MousePointerClick, X } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

// 交互式新手向导：聚光灯高亮真实界面元素，引导用户亲手依次点开各功能。
// - action: 'click' 表示需要用户点击高亮元素才继续；'next' 表示展示说明后点「下一步」继续。
// - route 非空时向导会自动导航到该页面再定位元素。
const STEPS = [
  {
    sel: '[data-tour="nav-classes"]', route: null, action: 'click',
    title: '第一步 · 打开「我的班级」',
    desc: '班级是布置作业、批改、学情分析的基础。从这里开始。',
    tip: '请点击左侧高亮的「我的班级」',
  },
  {
    sel: '[data-tour="class-create"]', route: '/class', action: 'click',
    title: '第二步 · 新建班级',
    desc: '点「新建班级」，填好名称、年级、学科即可创建。',
    tip: '请点击「新建班级」按钮',
  },
  {
    sel: '[data-tour="class-create-panel"]', route: '/class', action: 'next',
    title: '创建你的第一个班级',
    desc: '填好班级名称点「确认创建」。建好后进入班级，还能用 Excel 名单批量导入学生、给班级布置作业。',
    tip: '',
  },
  {
    sel: '[data-tour="nav-grader"]', route: null, action: 'click',
    title: '第三步 · 作业批改',
    desc: '学生作业拍照或传文件，AI 逐题批改、打分、写评语，自动生成讲评要点。',
    tip: '请点击「作业批改」',
  },
  {
    sel: '[data-tour="grader-upload"]', route: '/grader', action: 'next',
    title: '上传作业试试',
    desc: '拖拽或点击上传作业照片（支持多张和常见文档格式）。上传后 AI 自动识别题目开始批改，你可以先去忙别的。',
    tip: '',
  },
  {
    sel: '[data-tour="nav-notebook"]', route: null, action: 'click',
    title: '第四步 · 错题本',
    desc: '批改中做错的题会自动收录到这里，不用手抄。',
    tip: '请点击「错题本」',
  },
  {
    sel: '[data-tour="notebook-clusters"]', route: '/notebook', action: 'next',
    title: '按知识板块找薄弱点',
    desc: '错题自动按知识板块归类，题次越多越是薄弱点；每道题还能一键生成变式题，帮助学生举一反三。',
    tip: '',
  },
  {
    sel: '[data-tour="nav-lessonplan"]', route: null, action: 'click',
    title: '第五步 · 教案',
    desc: '输入课题、课时等信息，一键生成完整教案并自动保存。',
    tip: '请点击「教案」',
  },
  {
    sel: '[data-tour="lessonplan-submit"]', route: '/lessonplan', action: 'next',
    title: '生成教案',
    desc: '填好信息后点「生成教案」，AI 给出完整教案；不满意可以调整要求重新生成。',
    tip: '',
  },
  {
    sel: '[data-tour="feedback-fab"]', route: null, action: 'click',
    title: '最后 · 有想法随时告诉我们',
    desc: '右下角「反馈」按钮随时提意见，提交反馈还能获得额外体验额度。指引结束，开始使用吧！',
    tip: '点一下「反馈」试试，或直接点「完成」',
  },
]

const TOOLTIP_W = 340
const MAX_LOCATE_ATTEMPTS = 40 // 元素未出现最多等约 6 秒，之后先展示无聚光灯的提示

const OnboardingGuide = () => {
  const { user, markOnboardingSeen } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [active, setActive] = useState(false)
  const [stepIdx, setStepIdx] = useState(0)
  const [rect, setRect] = useState(null)
  const [place, setPlace] = useState('bottom')
  const clickHandlerRef = useRef(null)

  const step = STEPS[stepIdx]
  const isLast = stepIdx === STEPS.length - 1

  const finish = useCallback(() => {
    setActive(false)
    // 完成或跳过都记为已看：静默提交，失败不阻塞
    Promise.resolve(markOnboardingSeen?.()).catch(() => {})
  }, [markOnboardingSeen])

  const next = useCallback(() => {
    if (stepIdx >= STEPS.length - 1) finish()
    else setStepIdx((i) => i + 1)
  }, [stepIdx, finish])

  // 新用户首次登录自动开始
  useEffect(() => {
    if (!user || user.onboarding_seen || user.needs_profile || user.must_change_password) return undefined
    const t = setTimeout(() => {
      setStepIdx(0)
      setActive(true)
    }, 900)
    return () => clearTimeout(t)
  }, [user])

  // 「新手指引」按钮等处可手动重新开始（工作台 dispatchEvent('tour:start')）
  useEffect(() => {
    const start = () => {
      setStepIdx(0)
      setActive(true)
    }
    window.addEventListener('tour:start', start)
    return () => window.removeEventListener('tour:start', start)
  }, [])

  // 定位当前步骤的目标元素：必要时先导航，再轮询等待元素出现
  useEffect(() => {
    if (!active) return undefined
    let cancelled = false
    let attempts = 0
    let poll = null

    if (clickHandlerRef.current) {
      clickHandlerRef.current()
      clickHandlerRef.current = null
    }

    if (step.route && location.pathname !== step.route) {
      navigate(step.route)
      return undefined // pathname 变化后本 effect 重跑
    }

    const measure = (el) => {
      el.scrollIntoView({ block: 'center', behavior: 'smooth' })
      setTimeout(() => {
        if (cancelled) return
        const r = el.getBoundingClientRect()
        setRect({ top: r.top, left: r.left, width: r.width, height: r.height })
        setPlace(r.bottom + 260 < window.innerHeight ? 'bottom' : 'top')
      }, 380)
      if (step.action === 'click') {
        const handler = () => next()
        el.addEventListener('click', handler)
        clickHandlerRef.current = () => el.removeEventListener('click', handler)
      }
    }

    const locate = () => {
      if (cancelled) return
      const el = document.querySelector(step.sel)
      if (el) {
        setRect(null)
        measure(el)
        return
      }
      attempts += 1
      if (attempts >= MAX_LOCATE_ATTEMPTS) {
        setRect(null) // 找不到也先展示提示，可手动下一步
        return
      }
      poll = setTimeout(locate, 150)
    }
    locate()
    return () => {
      cancelled = true
      if (poll) clearTimeout(poll)
      if (clickHandlerRef.current) {
        clickHandlerRef.current()
        clickHandlerRef.current = null
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, stepIdx, location.pathname])

  // 滚动 / 窗口变化时跟随重测高亮位置
  useEffect(() => {
    if (!active || !rect) return undefined
    let raf = null
    const update = () => {
      if (raf) return
      raf = requestAnimationFrame(() => {
        raf = null
        const el = document.querySelector(step.sel)
        if (!el) return
        const r = el.getBoundingClientRect()
        setRect({ top: r.top, left: r.left, width: r.width, height: r.height })
      })
    }
    window.addEventListener('resize', update)
    window.addEventListener('scroll', update, true)
    return () => {
      window.removeEventListener('resize', update)
      window.removeEventListener('scroll', update, true)
      if (raf) cancelAnimationFrame(raf)
    }
  }, [active, rect, step.sel])

  if (!active) return null

  const prev = () => setStepIdx((i) => Math.max(0, i - 1))

  const tipLeft = rect ? Math.min(Math.max(rect.left, 12), Math.max(12, window.innerWidth - TOOLTIP_W - 12)) : (window.innerWidth - TOOLTIP_W) / 2
  const tipStyle = rect
    ? (place === 'bottom'
        ? { top: rect.top + rect.height + 14, left: tipLeft }
        : { bottom: window.innerHeight - rect.top + 14, left: tipLeft })
    : { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }

  return (
    <div className="fixed inset-0 z-[95]" style={{ pointerEvents: 'none' }}>
      {/* 聚光灯：透明区域可点击穿透到真实元素 */}
      {rect && (
        <div
          className="absolute rounded-xl transition-all duration-300 ease-out"
          style={{
            top: rect.top - 5,
            left: rect.left - 5,
            width: rect.width + 10,
            height: rect.height + 10,
            boxShadow: '0 0 0 9999px rgba(15, 23, 42, 0.55)',
            outline: '2px solid rgba(96, 165, 250, 0.95)',
            outlineOffset: 3,
          }}
        />
      )}

      {/* 提示气泡 */}
      <div className="absolute w-[340px] max-w-[calc(100vw-24px)] bg-white rounded-2xl shadow-2xl transition-all duration-300" style={{ ...tipStyle, pointerEvents: 'auto' }}>
        <div className="h-1 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-t-2xl" />
        <div className="p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-blue-600 bg-blue-50 rounded-full px-2 py-0.5">
              {stepIdx + 1} / {STEPS.length}
            </span>
            <button onClick={finish} className="p-1 rounded-full text-gray-300 hover:text-gray-500 hover:bg-gray-100 transition-colors" aria-label="跳过指引">
              <X className="h-4 w-4" />
            </button>
          </div>
          <h3 className="text-base font-bold text-gray-900 mb-1.5">{step.title}</h3>
          <p className="text-sm text-gray-600 leading-relaxed">{step.desc}</p>
          {step.tip && (
            <p className="mt-3 flex items-center gap-1.5 text-xs font-medium text-blue-600 bg-blue-50 rounded-lg px-3 py-2">
              <MousePointerClick className="h-4 w-4 shrink-0 animate-pulse" />
              {step.tip}
            </p>
          )}
          <div className="flex items-center justify-between mt-4">
            <button
              onClick={prev}
              disabled={stepIdx === 0}
              className="inline-flex items-center gap-0.5 text-sm text-gray-400 hover:text-gray-700 disabled:opacity-0 transition-colors"
            >
              <ChevronLeft className="h-4 w-4" /> 上一步
            </button>
            <div className="flex items-center gap-2">
              {step.action === 'click' && !isLast && (
                <button onClick={next} className="text-sm text-gray-400 hover:text-gray-600 transition-colors">
                  直接下一步
                </button>
              )}
              <button
                onClick={next}
                className="inline-flex items-center gap-0.5 px-4 py-1.5 rounded-full text-sm font-medium text-white bg-gradient-to-r from-blue-500 to-indigo-500 shadow hover:brightness-105 transition-all"
              >
                {isLast ? '完成' : '下一步'} <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default OnboardingGuide
