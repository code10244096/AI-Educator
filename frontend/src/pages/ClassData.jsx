import React, { useState, useEffect, useCallback } from 'react'
import { Routes, Route, useNavigate, useLocation, useParams, useSearchParams } from 'react-router-dom'
import {
  ClipboardList,
  Archive,
  Users,
  TrendingUp,
  TrendingDown,
  AlertCircle,
  Clock,
  BarChart3,
  Search,
  Plus,
  Edit,
  Eye,
  GraduationCap,
  Upload,
  XCircle,
  FileCheck,
  ChevronRight,
  ListTodo,
  X,
  FileText,
  Trash2,
  Loader2,
} from 'lucide-react'
import HomeworkDetail from './HomeworkDetail'
import { useHomeworkBoard, useClassInfo } from '../hooks/useClassHomework'
import ClassStats from '../components/ClassStats'
import ClassManager from '../components/ClassManager'
import { Loading } from '../components/PageState'
import ConfirmDialog from '../components/ConfirmDialog'
import { useToast } from '../components/Toast'
import { useClass } from '../context/ClassContext'
import { classAPI, classHomeworkAPI, getErrorMessage } from '../utils/api'

const inputCls = 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500'

const Modal = ({ title, onClose, children, footer, wide = false }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
    <div className="absolute inset-0 bg-black/40" onClick={onClose} />
    <div className={`relative w-full ${wide ? 'max-w-2xl' : 'max-w-lg'} bg-white rounded-xl shadow-xl max-h-[90vh] flex flex-col`}>
      <div className="p-5 border-b border-gray-200 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
        <button onClick={onClose} className="p-1.5 hover:bg-gray-100 rounded-lg">
          <X className="h-5 w-5 text-gray-500" />
        </button>
      </div>
      <div className="p-5 overflow-y-auto space-y-4">{children}</div>
      {footer && <div className="p-4 border-t border-gray-200 flex justify-end space-x-3">{footer}</div>}
    </div>
  </div>
)

const HomeworkFormModal = ({ classId, homework, onClose, onSaved }) => {
  const { addToast } = useToast()
  const today = new Date().toISOString().slice(0, 10)
  const [form, setForm] = useState({
    title: homework?.title || '',
    description: homework?.description || '',
    reference_answer: homework?.referenceAnswer || '',
    assign_date: homework?.date || today,
    deadline: homework?.deadline || today,
  })
  const [saving, setSaving] = useState(false)

  const submit = async () => {
    if (!form.title.trim()) {
      addToast('请输入作业标题', 'error')
      return
    }
    setSaving(true)
    try {
      if (homework) {
        await classHomeworkAPI.updateHomework(classId, homework.id, form)
        addToast('作业已更新', 'success')
      } else {
        await classHomeworkAPI.createHomework(classId, form)
        addToast('作业已布置', 'success')
      }
      onSaved()
    } catch (err) {
      addToast(getErrorMessage(err, '保存失败'), 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      title={homework ? '编辑作业' : '布置作业'}
      onClose={onClose}
      wide
      footer={(
        <>
          <button onClick={onClose} className="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50">取消</button>
          <button onClick={submit} disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
            {saving ? '保存中...' : '保存'}
          </button>
        </>
      )}
    >
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">作业标题 *</label>
        <input autoFocus={!homework} className={inputCls} value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} placeholder="例如：导数综合练习" />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">布置日期</label>
          <input type="text" inputMode="numeric" placeholder="2026-09-27" className={inputCls} value={form.assign_date} onChange={e => setForm(f => ({ ...f, assign_date: e.target.value }))} />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">截止日期</label>
          <input type="text" inputMode="numeric" placeholder="2026-09-27" className={inputCls} value={form.deadline} onChange={e => setForm(f => ({ ...f, deadline: e.target.value }))} />
        </div>
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">作业说明</label>
        <textarea className={inputCls} rows={2} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">参考答案（批改时自动使用）</label>
        <textarea
          className={`${inputCls} font-mono`}
          rows={6}
          value={form.reference_answer}
          onChange={e => setForm(f => ({ ...f, reference_answer: e.target.value }))}
          placeholder={'1. A\n2. 3\n3. x=2'}
        />
      </div>
    </Modal>
  )
}

const HomeworkBoard = ({ classId, info }) => {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { addToast } = useToast()
  const { reloadClasses } = useClass()
  const { stats: homeworkStats, homeworkList: recentHomework, gradingTasks, alertStudents, loading, error, reload } = useHomeworkBoard(classId)
  const [classStats, setClassStats] = React.useState(null)
  const [editingHomework, setEditingHomework] = useState(undefined)
  const [deleteTarget, setDeleteTarget] = useState(null)

  useEffect(() => {
    if (searchParams.get('create') === '1') setEditingHomework(null)
  }, [searchParams])

  const closeHomeworkForm = () => {
    setEditingHomework(undefined)
    if (searchParams.get('create')) {
      const next = new URLSearchParams(searchParams)
      next.delete('create')
      setSearchParams(next, { replace: true })
    }
  }

  React.useEffect(() => {
    classAPI.getStats(classId).then(setClassStats).catch(() => setClassStats(null))
  }, [classId, homeworkStats])

  const currentHomework = homeworkStats?.currentHomework

  const handleDelete = async () => {
    try {
      await classHomeworkAPI.deleteHomework(classId, deleteTarget.id)
      addToast('作业已删除', 'success')
      reload()
      reloadClasses()
    } catch (err) {
      addToast(getErrorMessage(err, '删除失败'), 'error')
    } finally {
      setDeleteTarget(null)
    }
  }

  if (loading && !homeworkStats) {
    return (
      <div className="flex items-center justify-center py-16 text-gray-500">
        <Clock className="h-5 w-5 mr-2 animate-spin" />
        加载作业数据...
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-16">
        <p className="text-red-500 mb-3">{error}</p>
        <button onClick={reload} className="text-blue-600 text-sm hover:underline">重试</button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">作业看板</h2>
          <p className="text-sm text-gray-500 mt-1">{info.name} · {info.subject} · 查看作业完成情况</p>
        </div>
        <button
          onClick={() => setEditingHomework(null)}
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
        >
          <Plus className="h-4 w-4 mr-2" />
          布置作业
        </button>
      </div>

      {homeworkStats && currentHomework && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border border-blue-100 p-5">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <p className="text-xs text-blue-600 font-medium uppercase tracking-wide">当前关注作业</p>
              <h3 className="text-lg font-bold text-gray-900 mt-1">{currentHomework.title}</h3>
              <p className="text-sm text-gray-500 mt-1">
                截止 {currentHomework.deadline} ·
                <span className={`ml-1 font-medium ${currentHomework.status === '待批改' ? 'text-orange-600' : 'text-green-600'}`}>
                  {currentHomework.status}
                </span>
              </p>
            </div>
            <button
              onClick={() => navigate(`/class/${classId}/homework/${currentHomework.id}`)}
              className="inline-flex items-center px-4 py-2 bg-white border border-blue-200 text-blue-700 rounded-lg text-sm hover:bg-blue-50 transition-colors"
            >
              查看提交详情
              <ChevronRight className="h-4 w-4 ml-1" />
            </button>
          </div>
          <div className="mt-4">
            <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
              <span>提交进度 {homeworkStats?.submitted}/{homeworkStats?.total}</span>
              <span className="font-medium text-blue-700">{homeworkStats?.submitRate}%</span>
            </div>
            <div className="w-full bg-white rounded-full h-2.5 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all"
                style={{ width: `${Math.min(homeworkStats?.submitRate || 0, 100)}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {homeworkStats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl p-5 border border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">提交进度</p>
                <p className="text-2xl font-bold text-blue-600 mt-1">
                  {homeworkStats.submitted}<span className="text-base text-gray-400">/{homeworkStats.total}</span>
                </p>
              </div>
              <div className="p-3 bg-blue-50 rounded-lg">
                <Upload className="h-6 w-6 text-blue-500" />
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-5 border border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">未提交</p>
                <p className="text-2xl font-bold text-red-500 mt-1">{homeworkStats.notSubmitted}</p>
              </div>
              <div className="p-3 bg-red-50 rounded-lg">
                <XCircle className="h-6 w-6 text-red-400" />
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-5 border border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">待批改份数</p>
                <p className="text-2xl font-bold text-orange-600 mt-1">{homeworkStats.pendingCount}</p>
              </div>
              <div className="p-3 bg-orange-50 rounded-lg">
                <Clock className="h-6 w-6 text-orange-500" />
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-5 border border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                {(currentHomework?.gradedCount || 0) > 0 ? (
                  <>
                    <p className="text-sm text-gray-500">《{currentHomework.title}》平均分 / 及格率</p>
                    <p className="text-2xl font-bold text-purple-600 mt-1">
                      {homeworkStats.avgScore || '-'}
                      <span className="text-base text-gray-400"> / {homeworkStats.passRate ? `${homeworkStats.passRate}%` : '-'}</span>
                    </p>
                    <p className="text-xs text-gray-400 mt-1 leading-snug">
                      统计《{currentHomework.title}》已批改 {currentHomework.gradedCount} 份
                    </p>
                  </>
                ) : (
                  <>
                    <p className="text-sm text-gray-500">这次作业的成绩</p>
                    <p className="text-2xl font-bold text-gray-400 mt-1">这次还没有成绩</p>
                    <button
                      type="button"
                      onClick={() => navigate(`/class/${classId}/exams`)}
                      className="text-xs text-blue-600 mt-1 hover:text-blue-800"
                    >
                      历史均分在成绩档案
                    </button>
                  </>
                )}
              </div>
              <div className="p-3 bg-purple-50 rounded-lg">
                <BarChart3 className="h-6 w-6 text-purple-500" />
              </div>
            </div>
          </div>
        </div>
      )}

      {gradingTasks.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="p-5 border-b border-gray-200 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <ListTodo className="h-5 w-5 text-blue-500" />
              <h3 className="text-lg font-semibold text-gray-900">待处理</h3>
              <span className="px-2 py-0.5 bg-orange-100 text-orange-700 text-xs rounded-full">
                {gradingTasks.length} 次作业
              </span>
            </div>
          </div>
          <div className="p-5 space-y-3">
            {gradingTasks.map((task) => (
              <div key={task.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                <div className="flex items-center space-x-3 flex-1 min-w-0">
                  <div className="p-2 bg-orange-100 rounded-lg shrink-0">
                    <FileCheck className="h-4 w-4 text-orange-600" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{task.title}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{task.progressLabel}</p>
                    <div className="mt-2 w-full max-w-xs">
                      <div className="w-full bg-gray-200 rounded-full h-1.5">
                        <div
                          className="bg-gradient-to-r from-orange-400 to-orange-500 h-1.5 rounded-full transition-all"
                          style={{ width: `${task.progress}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => navigate(`/class/${classId}/homework/${task.homeworkId}`)}
                  className="ml-4 shrink-0 inline-flex items-center px-3 py-1.5 text-sm text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-lg transition-colors"
                >
                  查看
                  <ChevronRight className="h-3.5 w-3.5 ml-0.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200">
        <div className="p-5 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">作业列表</h3>
        </div>
        {recentHomework.length === 0 ? (
          <div className="p-10 text-center text-sm text-gray-400">
            还没有布置作业，点击右上角「布置作业」开始
          </div>
        ) : (
        <>
        <div className="lg:hidden divide-y divide-gray-100">
          {recentHomework.map((hw) => (
            <div key={`card-${hw.assignment_id}`} className="p-4 space-y-2">
              <button
                type="button"
                onClick={() => navigate(`/class/${classId}/homework/${hw.id}`)}
                className="w-full text-left"
              >
                <p className="text-sm font-medium text-gray-900">{hw.title}</p>
                <p className="mt-1 text-xs text-gray-500">{hw.date} · 提交 {hw.submitted}/{hw.total} · {hw.status}</p>
              </button>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => navigate(`/class/${classId}/homework/${hw.id}`)}
                  className="text-blue-600 hover:text-blue-800 text-sm inline-flex items-center"
                >
                  <Eye className="h-3.5 w-3.5 mr-1" />
                  查看
                </button>
                <button type="button" onClick={() => setEditingHomework(hw)} className="text-sm text-gray-500 hover:text-gray-800">编辑</button>
                <button type="button" onClick={() => setDeleteTarget(hw)} className="text-sm text-gray-500 hover:text-red-600">删除</button>
              </div>
            </div>
          ))}
        </div>
        <div className="hidden lg:block overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50">
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase whitespace-nowrap">作业名称</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase whitespace-nowrap">日期</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase whitespace-nowrap">提交情况</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">平均分</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {recentHomework.map((hw) => (
                <tr
                  key={hw.assignment_id}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => navigate(`/class/${classId}/homework/${hw.id}`)}
                >
                  <td className="px-5 py-4 text-sm font-medium text-gray-900 hover:text-blue-600">{hw.title}</td>
                  <td className="px-5 py-4 text-sm text-gray-500">{hw.date}</td>
                  <td className="px-5 py-4">
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-gray-900">{hw.submitted}/{hw.total}</span>
                      <div className="w-16 bg-gray-100 rounded-full h-1.5 overflow-hidden">
                        <div
                          className="h-full bg-blue-500 rounded-full"
                          style={{ width: `${hw.total ? Math.min(100, Math.round((hw.submitted / hw.total) * 100)) : 0}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-5 py-4 text-sm text-gray-900">{hw.avgScore > 0 ? hw.avgScore : '-'}</td>
                  <td className="px-5 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${
                      hw.status === '已批改' ? 'bg-green-100 text-green-800' : 'bg-orange-100 text-orange-800'
                    }`}>
                      {hw.status}
                    </span>
                  </td>
                  <td className="px-5 py-4 whitespace-nowrap">
                    <div className="flex items-center space-x-3 whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => navigate(`/class/${classId}/homework/${hw.id}`)}
                        className="text-blue-600 hover:text-blue-800 text-sm inline-flex items-center"
                      >
                        <Eye className="h-3.5 w-3.5 mr-1" />
                        查看
                      </button>
                      <button onClick={() => setEditingHomework(hw)} className="text-gray-400 hover:text-gray-700" title="编辑">
                        <Edit className="h-4 w-4" />
                      </button>
                      <button onClick={() => setDeleteTarget(hw)} className="text-gray-400 hover:text-red-600" title="删除">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        </>
        )}
      </div>

      {classStats && classStats.total_students > 0 && (
        <ClassStats stats={classStats} />
      )}

      {alertStudents.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="p-5 border-b border-gray-200">
            <div className="flex items-center space-x-2">
              <AlertCircle className="h-5 w-5 text-red-500" />
              <h3 className="text-lg font-semibold text-gray-900">预警学生</h3>
            </div>
          </div>
          <div className="p-5 space-y-3">
            {alertStudents.map((student, idx) => (
              <div key={idx} className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                    <span className="text-sm font-medium text-red-600">{student.name?.[0]}</span>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">{student.name}</p>
                    <p className="text-xs text-red-600">{student.warning}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  {student.score !== null && (
                    <span className="text-sm font-bold text-red-600">{student.score}分</span>
                  )}
                  {student.trend === 'down' ? (
                    <TrendingDown className="h-4 w-4 text-red-500" />
                  ) : (
                    <TrendingUp className="h-4 w-4 text-gray-400" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {editingHomework !== undefined && (
        <HomeworkFormModal
          classId={classId}
          homework={editingHomework}
          onClose={closeHomeworkForm}
          onSaved={() => { closeHomeworkForm(); reload(); reloadClasses() }}
        />
      )}

      <ConfirmDialog
        isOpen={!!deleteTarget}
        title="删除作业"
        message={`删除《${deleteTarget?.title || ''}》将同时删除所有学生的提交与批改记录，确定吗？`}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
        confirmText="确认删除"
        cancelText="再想想"
      />
    </div>
  )
}

const ScoreArchive = ({ classId, info }) => {
  const [exams, setExams] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedExam, setSelectedExam] = useState(null)
  const [chartExamId, setChartExamId] = useState(null)
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    if (!selectedExam) return undefined
    const onKey = (e) => { if (e.key === 'Escape') setSelectedExam(null) }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [selectedExam])

  useEffect(() => {
    setLoading(true)
    classAPI.getScoreArchive(classId)
      .then(d => { setExams(d.items || []); setError(null) })
      .catch(err => setError(getErrorMessage(err, '加载失败')))
      .finally(() => setLoading(false))
  }, [classId])

  const chartExam = exams.find(e => e.assignment_id === chartExamId) || exams[0]
  const openExam = (exam) => {
    setSelectedExam(exam)
    setChartExamId(exam.assignment_id)
  }

  const handleExportPDF = async (exam) => {
    setExporting(true)
    try {
      const element = document.getElementById(`exam-detail-${exam.assignment_id}`)
      if (!element) return
      const { default: html2pdf } = await import('html2pdf.js')
      await html2pdf(element, {
        margin: 10,
        filename: `${exam.name}_成绩分析报告.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2 },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
      })
    } catch (err) {
      console.error('导出PDF失败:', err)
    } finally {
      setExporting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16 text-gray-500">
        <Loader2 className="h-5 w-5 mr-2 animate-spin" />
        加载成绩档案...
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900">成绩档案</h2>
        <p className="text-sm text-gray-500 mt-1">{info.name} · {info.subject} · 根据已批改作业自动统计</p>
      </div>

      {error && <p className="text-sm text-red-500">{error}</p>}

      <div className="bg-white rounded-xl border border-gray-200">
        <div className="p-5 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">历次作业成绩</h3>
        </div>
        {exams.length === 0 ? (
          <div className="p-10 text-center text-sm text-gray-400">暂无已批改的作业成绩</div>
        ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50">
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">作业名称</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">日期</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">已批改</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">平均分</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">最高分</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">最低分</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">及格率</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {exams.map((exam) => (
                <tr key={exam.assignment_id} className="hover:bg-gray-50">
                  <td className="px-5 py-4 text-sm font-medium text-gray-900">{exam.name}</td>
                  <td className="px-5 py-4 text-sm text-gray-500">{exam.date}</td>
                  <td className="px-5 py-4 text-sm text-gray-500">{exam.gradedCount} 人</td>
                  <td className="px-5 py-4 text-sm text-gray-900">{exam.avgScore}</td>
                  <td className="px-5 py-4 text-sm text-green-600">{exam.highest}</td>
                  <td className="px-5 py-4 text-sm text-red-600">{exam.lowest}</td>
                  <td className="px-5 py-4 text-sm text-gray-900">{exam.passRate}%</td>
                  <td className="px-5 py-4">
                    <button onClick={() => openExam(exam)} className="text-blue-600 hover:text-blue-800 text-sm">
                      详情
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        )}
      </div>

      {chartExam && (
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="p-5 border-b border-gray-200 flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-lg font-semibold text-gray-900">成绩分布（{chartExam.name}）</h3>
            <select
              aria-label="选择要看分布的作业"
              value={String(chartExam.assignment_id)}
              onChange={(e) => setChartExamId(exams.find(item => String(item.assignment_id) === e.target.value)?.assignment_id ?? e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm text-gray-700 bg-white"
            >
              {exams.map((exam) => (
                <option key={exam.assignment_id} value={String(exam.assignment_id)}>{exam.name}</option>
              ))}
            </select>
          </div>
          <div className="p-5 space-y-3">
            {chartExam.distribution.map((item, idx) => (
              <div key={idx} className="flex items-center space-x-4">
                <span className="text-sm text-gray-600 w-16">{item.range}</span>
                <div className="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-end pr-2"
                    style={{ width: `${item.percentage}%` }}
                  >
                    {item.count > 0 && <span className="text-xs text-white font-medium">{item.count}人</span>}
                  </div>
                </div>
                <span className="text-sm text-gray-500 w-12 text-right">{item.percentage}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {selectedExam && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/40" onClick={() => setSelectedExam(null)} />
          <div className="relative w-full max-w-4xl bg-white shadow-xl rounded-xl max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-200 p-5 flex items-center justify-between z-10">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{selectedExam.name}</h3>
                <p className="text-sm text-gray-500 mt-0.5">{selectedExam.date} · 已批改 {selectedExam.gradedCount} 人</p>
              </div>
              <button onClick={() => setSelectedExam(null)} className="p-2 hover:bg-gray-100 rounded-lg" aria-label="关闭">
                <X className="h-5 w-5 text-gray-500" />
              </button>
            </div>

            <div id={`exam-detail-${selectedExam.assignment_id}`} className="p-6">
              <div className="grid grid-cols-4 gap-4 mb-6">
                <div className="bg-blue-50 rounded-xl p-4 border border-blue-100">
                  <p className="text-xs text-blue-600 font-medium mb-1">平均分</p>
                  <p className="text-2xl font-bold text-blue-700">{selectedExam.avgScore}</p>
                </div>
                <div className="bg-green-50 rounded-xl p-4 border border-green-100">
                  <p className="text-xs text-green-600 font-medium mb-1">最高分</p>
                  <p className="text-2xl font-bold text-green-700">{selectedExam.highest}</p>
                </div>
                <div className="bg-red-50 rounded-xl p-4 border border-red-100">
                  <p className="text-xs text-red-600 font-medium mb-1">最低分</p>
                  <p className="text-2xl font-bold text-red-700">{selectedExam.lowest}</p>
                </div>
                <div className="bg-purple-50 rounded-xl p-4 border border-purple-100">
                  <p className="text-xs text-purple-600 font-medium mb-1">及格率</p>
                  <p className="text-2xl font-bold text-purple-700">{selectedExam.passRate}%</p>
                </div>
              </div>

              <div className="mb-6">
                <h4 className="text-base font-semibold text-gray-800 mb-4">成绩分布统计</h4>
                <div className="space-y-3">
                  {(selectedExam.distribution || []).map((item) => (
                    <div key={item.range} className="flex items-center gap-3 text-sm">
                      <span className="w-16 text-gray-600">{item.range}</span>
                      <span className="font-medium text-gray-900">{item.count} 人</span>
                      <span className="text-gray-400">{item.percentage}%</span>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="text-base font-semibold text-gray-800 mb-4">成绩前五名</h4>
                <div className="space-y-3">
                  {selectedExam.topStudents.map((student, idx) => (
                    <div key={idx} className="flex items-center p-3 bg-gray-50 rounded-lg">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm mr-4 ${
                        idx === 0 ? 'bg-yellow-400 text-yellow-900' :
                        idx === 1 ? 'bg-gray-300 text-gray-700' :
                        idx === 2 ? 'bg-orange-400 text-orange-900' : 'bg-gray-100 text-gray-600'
                      }`}>
                        {student.rank}
                      </div>
                      <span className="flex-1 font-medium text-gray-900">{student.name}</span>
                      <span className="text-lg font-bold text-blue-600">{student.score}分</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-6 flex justify-end">
                <button
                  onClick={() => handleExportPDF(selectedExam)}
                  disabled={exporting}
                  className="inline-flex items-center px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
                >
                  <FileText className="h-4 w-4 mr-2" />
                  {exporting ? '导出中...' : '导出PDF分析报告'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const MemberFormModal = ({ classId, member, onClose, onSaved }) => {
  const { addToast } = useToast()
  const [form, setForm] = useState({
    name: member?.name || '',
    gender: member?.gender || '男',
    student_no: member?.student_no || '',
  })
  const [saving, setSaving] = useState(false)
  const [nameError, setNameError] = useState('')

  const submit = async () => {
    if (!form.name.trim()) {
      setNameError('请填写学生姓名')
      return
    }
    setNameError('')
    setSaving(true)
    try {
      if (member) {
        await classAPI.updateMember(classId, member.id, form)
        addToast('学生信息已更新', 'success')
      } else {
        await classAPI.addMember(classId, form)
        addToast('学生已添加', 'success')
      }
      onSaved()
    } catch (err) {
      addToast(getErrorMessage(err, '保存失败'), 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      title={member ? '编辑学生' : '添加学生'}
      onClose={onClose}
      footer={(
        <>
          <button onClick={onClose} className="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50">取消</button>
          <button onClick={submit} disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
            {saving ? '保存中...' : '保存'}
          </button>
        </>
      )}
    >
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">姓名 *</label>
        <input className={inputCls} value={form.name} onChange={e => { setForm(f => ({ ...f, name: e.target.value })); setNameError('') }} />
        {nameError && <p className="text-xs text-red-600 mt-1">{nameError}</p>}
        {member && <p className="text-xs text-gray-400 mt-1">改名会同步更新该学生在本班的作业提交记录</p>}
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">性别</label>
          <select className={inputCls} value={form.gender} onChange={e => setForm(f => ({ ...f, gender: e.target.value }))}>
            <option value="男">男</option>
            <option value="女">女</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">学号</label>
          <input className={inputCls} value={form.student_no} onChange={e => setForm(f => ({ ...f, student_no: e.target.value }))} />
        </div>
      </div>
    </Modal>
  )
}

const ImportMembersModal = ({ classId, onClose, onSaved }) => {
  const { addToast } = useToast()
  const [text, setText] = useState('')
  const [file, setFile] = useState(null)
  const [saving, setSaving] = useState(false)

  const submit = async () => {
    if (!text.trim() && !file) {
      addToast('请粘贴名单或选择名单文件', 'error')
      return
    }
    setSaving(true)
    try {
      const res = await classAPI.importMembers(classId, { text, file })
      addToast(res.message, 'success')
      onSaved()
    } catch (err) {
      addToast(getErrorMessage(err, '导入失败'), 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      title="批量导入学生"
      onClose={onClose}
      footer={(
        <>
          <button onClick={onClose} className="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50">取消</button>
          <button onClick={submit} disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
            {saving ? '导入中...' : '开始导入'}
          </button>
        </>
      )}
    >
      <p className="text-sm text-gray-500">每行一个学生，格式：<code className="bg-gray-100 px-1 rounded">姓名,性别,学号</code>（性别、学号可省略，重名会自动跳过）</p>
      <textarea
        className={`${inputCls} font-mono`}
        rows={8}
        value={text}
        onChange={e => setText(e.target.value)}
        placeholder={'张三,男,2024001\n李四,女,2024002\n王五'}
      />
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">或上传名单文件（.txt / .csv）</label>
        <div className="flex items-center gap-3">
          <label className="inline-flex items-center px-3 py-1.5 border border-gray-300 rounded-lg text-sm text-gray-700 bg-white cursor-pointer hover:bg-gray-50">
            选择文件
            <input type="file" accept=".txt,.csv" onChange={e => setFile(e.target.files?.[0] || null)} className="sr-only" />
          </label>
          <span className="text-sm text-gray-500">{file ? file.name : '还没选择文件'}</span>
        </div>
      </div>
    </Modal>
  )
}

const ClassMembers = ({ classId, info }) => {
  const { addToast } = useToast()
  const { reloadClasses } = useClass()
  const [searchTerm, setSearchTerm] = useState('')
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [editing, setEditing] = useState(undefined)
  const [importing, setImporting] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    classAPI.getMembers(classId)
      .then(d => { setStudents(d.items || []); setError(null) })
      .catch(err => setError(getErrorMessage(err, '加载失败')))
      .finally(() => setLoading(false))
  }, [classId])

  useEffect(() => { load() }, [load])

  const afterChange = () => {
    setEditing(undefined)
    setImporting(false)
    load()
    reloadClasses()
  }

  const handleDelete = async () => {
    try {
      await classAPI.removeMember(classId, deleteTarget.id)
      addToast('已移除学生', 'success')
      afterChange()
    } catch (err) {
      addToast(getErrorMessage(err, '移除失败'), 'error')
    } finally {
      setDeleteTarget(null)
    }
  }

  const hasStudentNo = students.some(s => (s.student_no || '').trim())
  const filteredStudents = students
    .filter(s => {
      const term = searchTerm.trim().toLowerCase()
      if (!term) return true
      const nameHit = s.name.toLowerCase().includes(term)
      const noHit = hasStudentNo && (s.student_no || '').includes(searchTerm.trim())
      return nameHit || noHit
    })
    .slice()
    .sort((a, b) => (a.rank || 9999) - (b.rank || 9999) || a.name.localeCompare(b.name, 'zh'))

  const statusCls = (status) => (
    status === '优秀' ? 'bg-green-100 text-green-800' :
    status === '良好' ? 'bg-blue-100 text-blue-800' :
    status === '待提高' ? 'bg-orange-100 text-orange-800' :
    status === '需关注' ? 'bg-red-100 text-red-800' :
    'bg-gray-100 text-gray-500'
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-bold text-gray-900">班级成员</h2>
          <p className="text-sm text-gray-500 mt-1">{info.name} · {loading ? '正在加载学生' : `${students.length}名学生`}</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setImporting(true)}
            className="inline-flex items-center px-4 py-2 border border-blue-200 text-blue-700 rounded-lg text-sm hover:bg-blue-50"
          >
            <Upload className="h-4 w-4 mr-2" />
            批量导入
          </button>
          <button
            onClick={() => setEditing(null)}
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            添加学生
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200">
        <div className="p-5 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">学生列表</h3>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder={hasStudentNo ? '搜索姓名或学号' : '搜索姓名'}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
        </div>
        {loading ? (
          <div className="p-10 flex items-center justify-center text-gray-500 text-sm">
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            加载学生名单...
          </div>
        ) : error ? (
          <div className="p-10 text-center text-sm text-red-500">{error}</div>
        ) : filteredStudents.length === 0 ? (
          <div className="p-10 text-center text-sm text-gray-400">
            {students.length === 0 ? '班级还没有学生，点击「添加学生」或「批量导入」' : '没有匹配的学生'}
          </div>
        ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50">
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">姓名</th>
                {hasStudentNo && <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">学号</th>}
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">性别</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">作业提交</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">平均分</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">班级排名</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">趋势</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredStudents.map((student) => (
                <tr key={student.id} className="hover:bg-gray-50">
                  <td className="px-5 py-4">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                        <span className="text-sm font-medium text-blue-600">{student.name[0]}</span>
                      </div>
                      <span className="text-sm font-medium text-gray-900">{student.name}</span>
                    </div>
                  </td>
                  {hasStudentNo && <td className="px-5 py-4 text-sm text-gray-500">{student.student_no}</td>}
                  <td className="px-5 py-4 text-sm text-gray-500">{student.gender}</td>
                  <td className="px-5 py-4 text-sm text-gray-500">{student.submittedCount}/{student.homeworkCount}</td>
                  <td className="px-5 py-4 text-sm font-medium text-gray-900">{student.avgScore ?? '-'}</td>
                  <td className="px-5 py-4 text-sm text-gray-500 whitespace-nowrap">{student.rank ? `第${student.rank}名` : '-'}</td>
                  <td className="px-5 py-4">
                    {student.trend === 'up' ? (
                      <TrendingUp className="h-4 w-4 text-green-500" />
                    ) : student.trend === 'down' ? (
                      <TrendingDown className="h-4 w-4 text-red-500" />
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </td>
                  <td className="px-5 py-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusCls(student.status)}`}>
                      {student.status}
                    </span>
                  </td>
                  <td className="px-5 py-4">
                    <div className="flex items-center space-x-2">
                      <button onClick={() => setEditing(student)} className="text-gray-400 hover:text-gray-700" title="编辑">
                        <Edit className="h-4 w-4" />
                      </button>
                      <button onClick={() => setDeleteTarget(student)} className="text-gray-400 hover:text-red-600" title="移除">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        )}
      </div>

      {editing !== undefined && (
        <MemberFormModal classId={classId} member={editing} onClose={() => setEditing(undefined)} onSaved={afterChange} />
      )}
      {importing && (
        <ImportMembersModal classId={classId} onClose={() => setImporting(false)} onSaved={afterChange} />
      )}
      <ConfirmDialog
        isOpen={!!deleteTarget}
        title="移除学生"
        message={`确定将「${deleteTarget?.name || ''}」移出班级吗？其历史作业记录会保留。`}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
        confirmText="确认移除"
        cancelText="再想想"
      />
    </div>
  )
}

const ClassDetail = () => {
  const { classId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const { info, notFound, loading: infoLoading } = useClassInfo(classId)

  const tabs = [
    { id: 'homework', label: '作业看板', icon: ClipboardList, path: `/class/${classId}/homework` },
    { id: 'exams', label: '成绩档案', icon: Archive, path: `/class/${classId}/exams` },
    { id: 'members', label: '班级成员', icon: Users, path: `/class/${classId}/members` },
  ]

  const getCurrentTab = () => {
    const path = location.pathname
    if (path.includes('/exams')) return 'exams'
    if (path.includes('/members')) return 'members'
    return 'homework'
  }

  const currentTab = getCurrentTab()

  if (notFound) {
    return (
      <div className="p-6 text-center py-16">
        <p className="text-gray-500 mb-4">班级不存在或已被删除</p>
        <button onClick={() => navigate('/class')} className="text-blue-600 text-sm hover:underline">返回班级列表</button>
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="flex items-center space-x-3 mb-6">
        <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-500 rounded-lg flex items-center justify-center">
          <GraduationCap className="h-5 w-5 text-white" />
        </div>
        {infoLoading ? (
          <div className="w-48"><Loading variant="skeleton" rows={2} /></div>
        ) : (
          <div>
            <h1 className="text-xl font-bold text-gray-900">{info.name}</h1>
            <p className="text-sm text-gray-500">{info.grade ? `${info.grade} · ` : ''}{info.subject || '数学'} · {info.students}名学生</p>
          </div>
        )}
      </div>

      <div className="flex space-x-1 bg-gray-100 rounded-lg p-1 mb-6 w-fit">
        {tabs.map((tab) => {
          const Icon = tab.icon
          const isActive = currentTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => navigate(tab.path)}
              className={`inline-flex items-center space-x-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
                isActive
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{tab.label}</span>
            </button>
          )
        })}
      </div>

      {currentTab === 'homework' && <HomeworkBoard classId={classId} info={info} />}
      {currentTab === 'exams' && <ScoreArchive classId={classId} info={info} />}
      {currentTab === 'members' && <ClassMembers classId={classId} info={info} />}
    </div>
  )
}

const ClassOverview = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const openCreate = searchParams.get('create') === '1'
  const closeCreate = () => {
    if (!searchParams.get('create')) return
    const next = new URLSearchParams(searchParams)
    next.delete('create')
    setSearchParams(next, { replace: true })
  }
  return (
    <div className="p-4 sm:p-6 max-w-4xl">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">我的班级</h1>
        <p className="text-sm text-gray-500 mt-1">新建班级、导入学生名单，点击班级查看作业、成绩与学生</p>
      </div>
      <ClassManager autoOpenCreate={openCreate} onCreateClose={closeCreate} />
    </div>
  )
}

const ClassData = () => {
  return (
    <Routes>
      <Route path=":classId/homework/:homeworkId" element={<HomeworkDetail />} />
      <Route path=":classId/*" element={<ClassDetail />} />
      <Route path="/" element={<ClassOverview />} />
    </Routes>
  )
}

export default ClassData
