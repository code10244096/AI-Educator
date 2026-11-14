import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Sparkles, Users, ClipboardList, ScanLine, BookOpen, FileText, Gift, X, ChevronLeft, ChevronRight, ArrowRight,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'

// 新手功能指引：首次登录自动弹出（后端按账号记忆），完成后不再打扰；工作台可随时重新打开
const STEPS = [
  {
    icon: Sparkles,
    color: 'from-blue-500 to-indigo-500',
    title: '欢迎使用 AI 教学助手',
    desc: '拍照批改、班级作业、错题本、教案生成，日常教学提效的活儿都交给 AI。接下来用一分钟，带你看看每个功能怎么用。',
    where: '',
    route: '',
  },
  {
    icon: Users,
    color: 'from-violet-500 to-purple-500',
    title: '第一步 · 创建班级',
    desc: '先建一个你自己的班级，支持用 Excel 名单批量导入学生。有了班级，才能布置作业、追踪每个学生的学情。',
    where: '左侧菜单「班级」→ 新建班级',
    route: '/class',
  },
  {
    icon: ClipboardList,
    color: 'from-cyan-500 to-teal-500',
    title: '第二步 · 布置作业',
    desc: '上传卷面照片或文件，AI 自动识别题目并生成参考答案，确认后一键布置给学生，不用手工抄题。',
    where: '班级页 → 布置作业',
    route: '/class',
  },
  {
    icon: ScanLine,
    color: 'from-orange-500 to-amber-500',
    title: '第三步 · 拍照批改',
    desc: '学生作业拍照上传，AI 逐题批改、打分、写评语，还能自动生成整份作业的讲评要点，批改效率成倍提升。',
    where: '左侧菜单「作业批改」',
    route: '/grader',
  },
  {
    icon: BookOpen,
    color: 'from-green-500 to-emerald-500',
    title: '第四步 · 错题本举一反三',
    desc: '批改中做错的题会自动收录进错题本，按知识板块聚合，一眼看出班级薄弱知识点；每道题还能一键生成变式题巩固练习。',
    where: '左侧菜单「错题本」',
    route: '/notebook',
  },
  {
    icon: FileText,
    color: 'from-rose-500 to-pink-500',
    title: '第五步 · 教案与学情',
    desc: '输入课题、学段，AI 生成完整教案；作业数据按知识点维度做学情分析，备课和复盘都有据可依。',
    where: '左侧菜单「教案生成」「学情分析」',
    route: '/lessonplan',
  },
  {
    icon: Gift,
    color: 'from-amber-500 to-yellow-500',
    title: '小贴士 · 体验额度与反馈',
    desc: '每天都有免费体验额度，正常使用完全够用；提交一条使用反馈还能获得额外奖励额度。有想法随时右下角告诉我们。',
    where: '页面右下角「意见反馈」',
    route: '',
  },
]

const OnboardingGuide = ({ onClose }) => {
  const [step, setStep] = useState(0)
  const [leaving, setLeaving] = useState(false)
  const { markOnboardingSeen } = useAuth()
  const navigate = useNavigate()
  const current = STEPS[step]
  const Icon = current.icon
  const isLast = step === STEPS.length - 1

  const close = () => {
    // 完成或跳过都记为已看：静默提交，失败也不阻塞关闭
    Promise.resolve(markOnboardingSeen?.()).catch(() => {})
    setLeaving(true)
    setTimeout(onClose, 200)
  }

  const go = (route) => {
    Promise.resolve(markOnboardingSeen?.()).catch(() => {})
    setLeaving(true)
    setTimeout(() => {
      onClose()
      if (route) navigate(route)
    }, 200)
  }

  return (
    <div
      className={`fixed inset-0 z-[90] flex items-center justify-center p-4 bg-gray-900/50 backdrop-blur-sm transition-opacity duration-200 ${leaving ? 'opacity-0' : 'opacity-100'}`}
      onClick={close}
    >
      <div
        className={`relative w-full max-w-lg bg-white rounded-2xl shadow-2xl overflow-hidden transition-all duration-200 ${leaving ? 'opacity-0 scale-95' : 'opacity-100 scale-100'}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* 头部色带 + 关闭 */}
        <div className={`h-1.5 bg-gradient-to-r ${current.color}`} />
        <button
          onClick={close}
          className="absolute top-4 right-4 p-1.5 rounded-full text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          aria-label="跳过指引"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="px-7 pt-7 pb-6">
          <div className={`inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br ${current.color} shadow-lg mb-4`}>
            <Icon className="h-7 w-7 text-white" />
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">{current.title}</h2>
          <p className="text-sm text-gray-600 leading-relaxed min-h-[66px]">{current.desc}</p>
          {current.where && (
            <p className="mt-3 text-xs text-gray-400">入口：{current.where}</p>
          )}

          {/* 步骤指示点 */}
          <div className="flex items-center justify-center gap-1.5 mt-5">
            {STEPS.map((s, i) => (
              <button
                key={i}
                onClick={() => setStep(i)}
                aria-label={`第 ${i + 1} 步`}
                className={`h-1.5 rounded-full transition-all duration-300 ${i === step ? 'w-6 bg-gray-800' : 'w-1.5 bg-gray-300 hover:bg-gray-400'}`}
              />
            ))}
          </div>

          {/* 操作区 */}
          <div className="flex items-center justify-between mt-6">
            <button
              onClick={() => setStep((s) => Math.max(0, s - 1))}
              disabled={step === 0}
              className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800 disabled:opacity-0 transition-colors"
            >
              <ChevronLeft className="h-4 w-4" /> 上一步
            </button>
            <div className="flex items-center gap-2">
              {current.route && (
                <button
                  onClick={() => go(current.route)}
                  className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800 transition-colors"
                >
                  带我去试试 <ArrowRight className="h-4 w-4" />
                </button>
              )}
              <button
                onClick={() => (isLast ? close() : setStep((s) => s + 1))}
                className={`inline-flex items-center gap-1 px-5 py-2 rounded-full text-sm font-medium text-white bg-gradient-to-r ${current.color} shadow-md hover:shadow-lg hover:brightness-105 transition-all`}
              >
                {isLast ? '开始使用' : '下一步'} <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default OnboardingGuide
