import React, { useMemo, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft,
  Search,
  Eye,
  Users,
  BarChart3,
  Upload,
  XCircle,
  Loader2,
  BrainCircuit,
  AlertTriangle,
} from 'lucide-react'
import { useHomeworkDetail, useClassInfo } from '../hooks/useClassHomework'
import { classHomeworkAPI, homeworkAPI, getErrorMessage } from '../utils/api'
import { useToast } from '../components/Toast'
import useAsync from '../hooks/useAsync'
import MathText from '../components/MathText'
import { Empty, ErrorState, Loading } from '../components/PageState'

// 名录筛选；工作台卡片跳转时带 ?filter=review|failed|processing|missing
const STATUS_FILTERS = [
  { id: 'all', label: '全部' },
  { id: 'missing', label: '未上传' },
  { id: 'processing', label: '批改中' },
  { id: 'failed', label: '失败' },
  { id: 'pending', label: '待批改' },
  { id: 'graded', label: '已批改' },
  { id: 'review', label: '待复核' },
]

export const isProcessing = (s) => s.status === 'processing' || s.status === 'queued'
export const isGraded = (s) => s.status === 'completed' && s.score !== null && s.score !== undefined
export const needsReview = (s) => isGraded(s) && s.review_status === 'pending_review'
const canStartGrade = (s) => s.uploaded && !isGraded(s) && !isProcessing(s) && s.status !== 'failed'

const matchFilter = (s, filter) => {
  switch (filter) {
    case 'missing': return !s.uploaded && s.in_roster !== false
    case 'pending': return canStartGrade(s)
    case 'processing': return isProcessing(s)
    case 'failed': return s.status === 'failed'
    case 'graded': return isGraded(s)
    case 'review': return needsReview(s)
    default: return true
  }
}

const Badge = ({ className, children }) => (
  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${className}`}>
    {children}
  </span>
)

const GradingBadge = ({ student }) => {
  if (!student.uploaded) return <span className="text-sm text-gray-400">-</span>
  if (student.status === 'queued') return <Badge className="bg-gray-100 text-gray-700">排队中</Badge>
  if (student.status === 'processing') {
    return <Badge className="bg-blue-100 text-blue-800"><Loader2 className="h-3 w-3 mr-1 animate-spin" />批改中</Badge>
  }
  if (student.status === 'failed') return <Badge className="bg-red-100 text-red-700">批改失败</Badge>
  if (isGraded(student)) {
    if (student.review_status === 'pending_review') return <Badge className="bg-blue-100 text-blue-800">待你确认</Badge>
    if (student.review_status === 'reviewed') return <Badge className="bg-green-100 text-green-800">已确认</Badge>
    return <Badge className="bg-green-100 text-green-800">已批改</Badge>
  }
  return <Badge className="bg-orange-100 text-orange-800">待批改</Badge>
}

const StatCard = ({ label, value, className = 'text-gray-900' }) => (
  <div className="bg-white rounded-xl p-4 border border-gray-200">
    <p className="text-xs text-gray-500">{label}</p>
    <p className={`text-xl font-bold mt-1 ${className}`}>{value}</p>
  </div>
)

const HomeworkDetail = () => {
  const { classId, homeworkId } = useParams()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { addToast } = useToast()
  const [searchTerm, setSearchTerm] = useState('')
  const [confirmingId, setConfirmingId] = useState(null)
  const statusFilter = STATUS_FILTERS.some(f => f.id === searchParams.get('filter')) ? searchParams.get('filter') : 'all'

  const { homework, students, loading, error, reload } = useHomeworkDetail(classId, homeworkId)
  const { info } = useClassInfo(classId)
  const gradedTotal = students.filter(isGraded).length
  const analysis = useAsync(() => classHomeworkAPI.getAnalysis(classId, homeworkId), [classId, homeworkId, gradedTotal])

  const stats = useMemo(() => {
    const roster = students.filter(s => s.in_roster !== false)
    const uploaded = students.filter(s => s.uploaded).length
    const missing = roster.filter(s => !s.uploaded).length
    const graded = students.filter(isGraded)
    const processing = students.filter(isProcessing).length
    const failed = students.filter(s => s.status === 'failed').length
    const avgScore = graded.length
      ? Math.round((graded.reduce((a, s) => a + s.score, 0) / graded.length) * 10) / 10
      : null
    const pendingReview = students.filter(needsReview)
    const reviewAvg = pendingReview.length
      ? Math.round((pendingReview.reduce((a, s) => a + s.score, 0) / pendingReview.length) * 10) / 10
      : null
    return {
      uploaded, missing, graded: graded.length, processing, failed, avgScore, total: roster.length,
      pendingReview: pendingReview.length, reviewAvg,
    }
  }, [students])

  const filteredStudents = useMemo(() => {
    const term = searchTerm.trim().toLowerCase()
    return students.filter(s => {
      const text = `${s.display_name || s.name}${s.student_no || ''}`.toLowerCase()
      return (!term || text.includes(term)) && matchFilter(s, statusFilter)
    })
  }, [students, searchTerm, statusFilter])

  const setFilter = (id) => {
    const next = new URLSearchParams(searchParams)
    if (id === 'all') next.delete('filter')
    else next.set('filter', id)
    setSearchParams(next, { replace: true })
  }

  const goUpload = (student) => {
    const params = new URLSearchParams()
    params.set('classId', classId)
    params.set('homeworkId', homeworkId)
    if (homework?.assignment_id) params.set('assignmentId', homework.assignment_id)
    if (student?.member_id) params.set('memberId', student.member_id)
    if (student?.submission_id) params.set('submissionId', student.submission_id)
    if (student?.name) params.set('studentName', student.name)
    navigate(`/grader?${params.toString()}`)
  }

  const viewResult = (student) => {
    const qs = searchParams.toString()
    navigate(`/tasks/sub-${student.submission_id}`, {
      state: { from: `/class/${classId}/homework/${homeworkId}${qs ? `?${qs}` : ''}` },
    })
  }

  const confirmReview = async (student) => {
    if (!student.submission_id) return
    setConfirmingId(student.submission_id)
    try {
      await homeworkAPI.markReviewed(student.submission_id)
      addToast('已确认这份批改', 'success')
      reload()
    } catch (err) {
      addToast(getErrorMessage(err, '确认失败'), 'error')
    } finally {
      setConfirmingId(null)
    }
  }

  const onReviewFilter = statusFilter === 'review'

  if (loading && !homework) {
    return <div className="p-6"><Loading text="正在加载作业…" /></div>
  }

  if (error || !homework) {
    const notFound = error?.response?.status === 404
    return (
      <div className="p-6">
        {notFound ? (
          <Empty
            title="作业不存在或已被删除"
            action={{ label: '返回作业看板', onClick: () => navigate(`/class/${classId}/homework`) }}
          />
        ) : (
          <ErrorState error={error} onRetry={() => reload()} />
        )}
      </div>
    )
  }

  return (
    <div className="p-4 sm:p-6 space-y-6">
      <div className="flex items-start gap-3 flex-wrap">
        <button
          onClick={() => navigate(`/class/${classId}/homework`)}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          aria-label="返回作业看板"
        >
          <ArrowLeft className="h-5 w-5 text-gray-600" />
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-bold text-gray-900">{homework.title}</h1>
          <p className="text-sm text-gray-500 mt-1">
            {info.name}{info.name ? ' · ' : ''}布置 {homework.date} · 截止 {homework.deadline}
          </p>
        </div>
        <button
          onClick={() => goUpload(null)}
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
        >
          <Upload className="h-4 w-4 mr-2" />
          上传作业
        </button>
      </div>

      {!homework.hasReferenceAnswer && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-2 text-sm text-amber-800">
          <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
          <span>这次作业没有参考答案，AI 将自行解题判分，准确率会下降。</span>
        </div>
      )}

      {homework.description && (
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
          <p className="text-sm text-gray-700">{homework.description}</p>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard label="已上传" value={`${stats.uploaded}/${stats.total}`} className="text-green-600" />
        <StatCard label="未上传" value={stats.missing} className="text-gray-700" />
        <StatCard label="批改中" value={stats.processing} className="text-blue-600" />
        <StatCard label="批改失败" value={stats.failed} className={stats.failed ? 'text-red-600' : 'text-gray-700'} />
        {onReviewFilter ? (
          <StatCard label="待你确认" value={stats.pendingReview} className="text-blue-600" />
        ) : (
          <StatCard label="已批改" value={stats.graded} className="text-blue-600" />
        )}
        <StatCard label="平均分" value={(onReviewFilter ? stats.reviewAvg : stats.avgScore) ?? '-'} className="text-purple-600" />
      </div>

      <div className="bg-white rounded-xl border border-gray-200">
        <div className="p-4 sm:p-5 border-b border-gray-200">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center space-x-2">
              <Users className="h-5 w-5 text-gray-500" />
              <h3 className="text-lg font-semibold text-gray-900">学生名录</h3>
              <span className="text-sm text-gray-400">{filteredStudents.length} 人</span>
            </div>
            <div className="flex items-center gap-3 flex-wrap">
              <div className="flex flex-wrap gap-1 bg-gray-100 rounded-lg p-1">
                {STATUS_FILTERS.map(f => (
                  <button
                    key={f.id}
                    onClick={() => setFilter(f.id)}
                    className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                      statusFilter === f.id ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="搜索姓名或学号"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9 pr-3 py-2 w-44 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
          </div>
        </div>
        {students.length === 0 ? (
          <Empty
            compact
            title="班级里还没有学生"
            desc="先导入学生名单，再上传作业"
            action={{ label: '去导入学生', onClick: () => navigate(`/class/${classId}/members`) }}
          />
        ) : (
          <>
          <div className="md:hidden divide-y divide-gray-100">
            {filteredStudents.map((student) => (
              <div key={`card-${student.member_id || 'x'}-${student.submission_id || student.id}`} className="p-4 space-y-2">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-gray-900">{student.display_name || student.name}</div>
                    <div className="mt-1"><GradingBadge student={student} /></div>
                  </div>
                  <div className="text-sm font-medium text-gray-900 shrink-0">
                    {isGraded(student) ? `${student.score} 分` : '-'}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {canStartGrade(student) && (
                    <button
                      onClick={() => goUpload(student)}
                      className="text-blue-600 hover:text-blue-800 text-sm inline-flex items-center"
                    >
                      <Upload className="h-3.5 w-3.5 mr-1" />
                      去批改
                    </button>
                  )}
                  {student.submission_id && (isGraded(student) || student.status === 'failed') && (
                    <button
                      onClick={() => viewResult(student)}
                      className="text-blue-600 hover:text-blue-800 text-sm inline-flex items-center"
                    >
                      <Eye className="h-3.5 w-3.5 mr-1" />
                      查看
                    </button>
                  )}
                  {needsReview(student) && (
                    <button
                      onClick={() => confirmReview(student)}
                      disabled={confirmingId === student.submission_id}
                      className="text-sm text-blue-700 hover:text-blue-900 disabled:opacity-50"
                    >
                      {confirmingId === student.submission_id ? '确认中…' : '确认'}
                    </button>
                  )}
                </div>
              </div>
            ))}
            {filteredStudents.length === 0 && (
              <div className="p-8 text-center text-gray-400 text-sm">没有符合条件的学生</div>
            )}
          </div>
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full min-w-[760px]">
              <thead>
                <tr className="bg-gray-50">
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">学生</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">上传</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">上传时间</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">批改状态</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">得分</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">错题数</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredStudents.map((student) => (
                  <tr key={`${student.member_id || 'x'}-${student.submission_id || student.id}`} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="text-sm font-medium text-gray-900">{student.display_name || student.name}</div>
                      <div className="text-xs text-gray-400">
                        {student.in_roster === false ? '不在当前名单中' : (student.student_no ? `学号 ${student.student_no}` : '')}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {student.uploaded
                        ? <Badge className="bg-green-50 text-green-700">已上传 {student.fileCount} 个文件</Badge>
                        : <Badge className="bg-gray-100 text-gray-500">未上传</Badge>}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">{student.submitTime || '-'}</td>
                    <td className="px-4 py-3">
                      <GradingBadge student={student} />
                      {isProcessing(student) && student.progressStage && (
                        <p className="text-[11px] text-blue-500 mt-1">{student.progressStage}</p>
                      )}
                      {student.status === 'failed' && student.errorMessage && (
                        <p className="text-[11px] text-red-500 mt-1 max-w-[220px]" title={student.errorMessage}>
                          {student.errorMessage}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">
                      {isGraded(student) ? `${student.score} 分` : '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {isGraded(student) ? student.wrongCount : '-'}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center space-x-3 whitespace-nowrap">
                        {canStartGrade(student) && (
                          <button
                            onClick={() => goUpload(student)}
                            className="text-blue-600 hover:text-blue-800 text-sm inline-flex items-center"
                          >
                            <Upload className="h-3.5 w-3.5 mr-1" />
                            去批改
                          </button>
                        )}
                        {student.submission_id && (isGraded(student) || student.status === 'failed') && (
                          <button
                            onClick={() => viewResult(student)}
                            className="text-blue-600 hover:text-blue-800 text-sm inline-flex items-center"
                          >
                            <Eye className="h-3.5 w-3.5 mr-1" />
                            查看
                          </button>
                        )}
                        {needsReview(student) && (
                          <button
                            onClick={() => confirmReview(student)}
                            disabled={confirmingId === student.submission_id}
                            className="text-sm text-blue-700 hover:text-blue-900 disabled:opacity-50"
                          >
                            {confirmingId === student.submission_id ? '确认中…' : '确认'}
                          </button>
                        )}
                        {!isProcessing(student) && student.in_roster !== false && (
                          <button
                            onClick={() => goUpload(student)}
                            className={`text-sm inline-flex items-center ${student.uploaded ? 'text-gray-500 hover:text-gray-800' : 'text-blue-600 hover:text-blue-800'}`}
                          >
                            <Upload className="h-3.5 w-3.5 mr-1" />
                            {student.uploaded ? '重新上传' : '上传'}
                          </button>
                        )}
                        {isProcessing(student) && <span className="text-sm text-gray-400">处理中</span>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filteredStudents.length === 0 && (
              <div className="p-8 text-center text-gray-400 text-sm">没有符合条件的学生</div>
            )}
          </div>
          </>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200">
        <div className="p-4 sm:p-5 border-b border-gray-200 flex items-center space-x-2 flex-wrap">
          <BrainCircuit className="h-5 w-5 text-purple-500" />
          <h3 className="text-lg font-semibold text-gray-900">逐题正确率</h3>
          {analysis.data && analysis.data.analyzed_count > 0 && (
            <span className="text-sm text-gray-400">基于 {analysis.data.analyzed_count} 份已批改作业</span>
          )}
        </div>
        {analysis.loading && !analysis.data ? (
          <Loading variant="skeleton" rows={3} className="p-5" />
        ) : analysis.error ? (
          <ErrorState error={analysis.error} onRetry={() => analysis.reload()} compact />
        ) : analysis.data && analysis.data.questions.length > 0 ? (
          <div className="p-4 sm:p-5 space-y-4">
            {analysis.data.questions.map((q) => (
              <div key={q.question_number} className="space-y-2">
                <div className="flex items-start justify-between gap-3">
                  <div className="text-sm font-medium text-gray-700 min-w-0">
                    <span className="mr-1">第 {q.question_number} 题</span>
                    {q.question_text && <MathText text={q.question_text} className="text-gray-600 font-normal" />}
                  </div>
                  <span className="text-sm text-gray-500 shrink-0">
                    正确率 {q.correct_rate}%（{q.correct}/{q.total}）
                  </span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2.5 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      q.correct_rate >= 70 ? 'bg-green-500' : q.correct_rate >= 50 ? 'bg-orange-500' : 'bg-red-500'
                    }`}
                    style={{ width: `${q.correct_rate}%` }}
                  />
                </div>
                {q.wrong_students.length > 0 && (
                  <p className="text-xs text-gray-500">
                    做错 {q.wrong_students.length} 人：{q.wrong_students.slice(0, 12).join('、')}
                    {q.wrong_students.length > 12 ? ' 等' : ''}
                  </p>
                )}
              </div>
            ))}
          </div>
        ) : (
          <Empty
            compact
            icon={BarChart3}
            title={(analysis.data?.graded_count || stats.graded) > 0 ? '有总分，但没有逐题对错' : '还没有批改完成的作业'}
            desc={(analysis.data?.graded_count || stats.graded) > 0
              ? '这些作业记下了分数，但没有保存每道题的对错，所以这里统计不了正确率'
              : '上传并批改后，这里会统计每道题的正确率和做错名单'}
          />
        )}
      </div>

      {stats.failed > 0 && statusFilter !== 'failed' && (
        <button
          onClick={() => setFilter('failed')}
          className="w-full text-left bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700 flex items-center gap-2"
        >
          <XCircle className="h-4 w-4" />
          有 {stats.failed} 份作业批改失败（不计入成绩），点击查看并重新上传
        </button>
      )}
    </div>
  )
}

export default HomeworkDetail
