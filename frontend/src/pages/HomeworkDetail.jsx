import React, { useState, useMemo, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  CheckCircle,
  Clock,
  Search,
  Eye,
  FileCheck,
  BrainCircuit,
  Users,
  BarChart3,
  Upload,
  XCircle,
  FileText,
  Beaker,
  Loader2,
  X,
} from 'lucide-react'
import { getKnowledgePoints } from '../data/homeworkData'
import { homeworkAPI } from '../utils/api'
import { useHomeworkDetail } from '../hooks/useClassHomework'

const classInfo = {
  class1: { name: '高三1班', students: 45, subject: '数学' },
  class2: { name: '高三2班', students: 42, subject: '数学' },
  class3: { name: '高三3班', students: 40, subject: '数学' },
}

const STATUS_FILTERS = [
  { id: 'all', label: '全部' },
  { id: 'submitted', label: '已提交' },
  { id: 'not_submitted', label: '未提交' },
  { id: 'graded', label: '已批改' },
  { id: 'pending_grade', label: '待批改' },
]

const HomeworkDetail = () => {
  const { classId, homeworkId } = useParams()
  const navigate = useNavigate()
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [selectedStudent, setSelectedStudent] = useState(null)
  const [datasetDetail, setDatasetDetail] = useState(null)
  const [loadingDataset, setLoadingDataset] = useState(false)
  const [gradingResult, setGradingResult] = useState(null)
  const [loadingResult, setLoadingResult] = useState(false)

  const { homework, students, loading, error, invalidate } = useHomeworkDetail(classId, homeworkId)
  const info = classInfo[classId] || classInfo.class1
  const knowledgePoints = getKnowledgePoints(Number(homeworkId))

  const stats = useMemo(() => {
    const submitted = students.filter(s => s.submitStatus === '已提交').length
    const notSubmitted = students.filter(s => s.submitStatus === '未提交').length
    const graded = students.filter(s => s.gradingStatus === '已批改').length
    const pendingGrade = students.filter(s => s.gradingStatus === '待批改').length
    const scores = students.filter(s => s.score !== null).map(s => s.score)
    const avgScore = scores.length
      ? Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 10) / 10
      : null

    return { submitted, notSubmitted, graded, pendingGrade, avgScore }
  }, [students])

  useEffect(() => {
    if (!selectedStudent?.datasetFileId) {
      setDatasetDetail(null)
      return
    }
    setLoadingDataset(true)
    homeworkAPI.getDatasetDetail(selectedStudent.datasetFileId)
      .then(data => setDatasetDetail(data))
      .catch(() => setDatasetDetail(null))
      .finally(() => setLoadingDataset(false))
  }, [selectedStudent])

  const handleViewStudent = async (student) => {
    if (student.isTestData) {
      setSelectedStudent(student)
      setGradingResult(null)
    } else if (student.grading_result_id) {
      setLoadingResult(true)
      try {
        const result = await homeworkAPI.getResult(student.grading_result_id)
        setGradingResult(result)
        setSelectedStudent(student)
      } catch {
        setGradingResult(null)
      } finally {
        setLoadingResult(false)
      }
    }
  }

  const buildGraderUrl = (student) => {
    const params = new URLSearchParams()
    if (student.datasetFileId) params.set('dataset', student.datasetFileId)
    if (classId) params.set('classId', classId)
    if (homeworkId) params.set('homeworkId', homeworkId)
    if (student.submission_id) params.set('submissionId', student.submission_id)
    if (student.name) params.set('studentName', student.name)
    if (homework?.assignment_id) params.set('assignmentId', homework.assignment_id)
    return `/grader?${params.toString()}`
  }

  const handleGradeWithDataset = (student) => {
    navigate(buildGraderUrl(student))
  }

  const filteredStudents = useMemo(() => {
    return students.filter(s => {
      const matchesSearch = s.name.toLowerCase().includes(searchTerm.toLowerCase())
      let matchesFilter = true
      switch (statusFilter) {
        case 'submitted': matchesFilter = s.submitStatus === '已提交'; break
        case 'not_submitted': matchesFilter = s.submitStatus === '未提交'; break
        case 'graded': matchesFilter = s.gradingStatus === '已批改'; break
        case 'pending_grade': matchesFilter = s.gradingStatus === '待批改'; break
        default: break
      }
      return matchesSearch && matchesFilter
    })
  }, [students, searchTerm, statusFilter])

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center py-16 text-gray-500">
        <Loader2 className="h-5 w-5 mr-2 animate-spin" />
        加载作业详情...
      </div>
    )
  }

  if (error || !homework) {
    return (
      <div className="p-6 text-center">
        <p className="text-gray-500">{error || '未找到该作业'}</p>
        <button
          onClick={() => navigate(`/class/${classId}/homework`)}
          className="mt-4 text-blue-600 hover:text-blue-800 text-sm"
        >
          返回作业看板
        </button>
      </div>
    )
  }

  const getSubmitBadge = (status) => {
    if (status === '已提交') {
      return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">已提交</span>
    }
    return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">未提交</span>
  }

  const getGradingBadge = (status) => {
    switch (status) {
      case '已批改':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">已批改</span>
      case '待批改':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">待批改</span>
      default:
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500">-</span>
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center space-x-4">
        <button
          onClick={() => navigate(`/class/${classId}/homework`)}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="h-5 w-5 text-gray-600" />
        </button>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-gray-900">{homework.title}</h1>
          <p className="text-sm text-gray-500 mt-1">
            {info.name} · {info.subject} · 布置日期 {homework.date} · 截止 {homework.deadline}
          </p>
        </div>
        {homework.status === '待批改' && stats.pendingGrade > 0 && (
          <button
            onClick={() => {
              const pending = students.find(s => s.gradingStatus === '待批改')
              if (pending) handleGradeWithDataset(pending)
              else navigate('/grader')
            }}
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
          >
            <FileCheck className="h-4 w-4 mr-2" />
            去批改 ({stats.pendingGrade} 份待批)
          </button>
        )}
      </div>

      {homework.description && (
        <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 flex items-start justify-between gap-3">
          <p className="text-sm text-blue-800">{homework.description}</p>
          {homework.hasTestData && (
            <span className="shrink-0 inline-flex items-center px-2.5 py-1 bg-purple-100 text-purple-700 text-xs rounded-full">
              <Beaker className="h-3 w-3 mr-1" />
              含 dataset 测试数据
            </span>
          )}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-white rounded-xl p-4 border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-500">已提交</p>
              <p className="text-xl font-bold text-green-600 mt-1">{stats.submitted}/{homework.total}</p>
            </div>
            <Upload className="h-5 w-5 text-green-500" />
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-500">未提交</p>
              <p className="text-xl font-bold text-red-500 mt-1">{stats.notSubmitted}</p>
            </div>
            <XCircle className="h-5 w-5 text-red-400" />
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-500">已批改</p>
              <p className="text-xl font-bold text-blue-600 mt-1">{stats.graded}</p>
            </div>
            <CheckCircle className="h-5 w-5 text-blue-500" />
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-500">待批改</p>
              <p className="text-xl font-bold text-orange-600 mt-1">{stats.pendingGrade}</p>
            </div>
            <Clock className="h-5 w-5 text-orange-500" />
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-500">平均分</p>
              <p className="text-xl font-bold text-purple-600 mt-1">{stats.avgScore ?? '-'}</p>
            </div>
            <BarChart3 className="h-5 w-5 text-purple-500" />
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200">
        <div className="p-5 border-b border-gray-200">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center space-x-2">
              <Users className="h-5 w-5 text-gray-500" />
              <h3 className="text-lg font-semibold text-gray-900">学生提交名录</h3>
              <span className="text-sm text-gray-400">共 {filteredStudents.length} 人</span>
            </div>
            <div className="flex items-center space-x-3">
              <div className="flex space-x-1 bg-gray-100 rounded-lg p-1">
                {STATUS_FILTERS.map(f => (
                  <button
                    key={f.id}
                    onClick={() => setStatusFilter(f.id)}
                    className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                      statusFilter === f.id
                        ? 'bg-white text-gray-900 shadow-sm'
                        : 'text-gray-500 hover:text-gray-700'
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
                  placeholder="搜索学生..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50">
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">学生</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">提交状态</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">提交时间</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">附件</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">批改状态</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">得分</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">错题数</th>
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
                      <div>
                        <span className="text-sm font-medium text-gray-900">{student.name}</span>
                        {student.isTestData && (
                          <span className="ml-2 inline-flex items-center px-1.5 py-0.5 bg-purple-50 text-purple-600 text-[10px] rounded">
                            测试数据
                          </span>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-5 py-4">{getSubmitBadge(student.submitStatus)}</td>
                  <td className="px-5 py-4 text-sm text-gray-500">{student.submitTime || '-'}</td>
                  <td className="px-5 py-4 text-sm text-gray-500">
                    {student.fileCount > 0 ? `${student.fileCount} 个文件` : '-'}
                  </td>
                  <td className="px-5 py-4">{getGradingBadge(student.gradingStatus)}</td>
                  <td className="px-5 py-4 text-sm font-medium text-gray-900">
                    {student.score !== null ? `${student.score} 分` : '-'}
                  </td>
                  <td className="px-5 py-4 text-sm text-gray-500">
                    {student.wrongCount !== null ? student.wrongCount : '-'}
                  </td>
                  <td className="px-5 py-4">
                    <div className="flex items-center space-x-2">
                      {student.isTestData && (
                        <button
                          onClick={() => handleViewStudent(student)}
                          className="text-purple-600 hover:text-purple-800 text-sm inline-flex items-center"
                        >
                          <FileText className="h-3.5 w-3.5 mr-1" />
                          作业
                        </button>
                      )}
                      {student.gradingStatus === '待批改' ? (
                        <button
                          onClick={() => handleGradeWithDataset(student)}
                          className="text-blue-600 hover:text-blue-800 text-sm"
                        >
                          批改
                        </button>
                      ) : student.gradingStatus === '已批改' ? (
                        <button
                          onClick={() => handleViewStudent(student)}
                          className="text-blue-600 hover:text-blue-800 text-sm inline-flex items-center"
                        >
                          <Eye className="h-3.5 w-3.5 mr-1" />
                          查看
                        </button>
                      ) : (
                        <span className="text-sm text-gray-400">-</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filteredStudents.length === 0 && (
          <div className="p-8 text-center text-gray-400 text-sm">没有匹配的学生记录</div>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 relative overflow-hidden">
        <div className="p-5 border-b border-gray-200">
          <div className="flex items-center space-x-2">
            <BrainCircuit className="h-5 w-5 text-purple-500" />
            <h3 className="text-lg font-semibold text-gray-900">知识点掌握情况</h3>
            <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded-full">即将上线</span>
          </div>
        </div>
        {homework.status === '已批改' && knowledgePoints.length > 0 ? (
          <div className="p-5 space-y-4">
            {knowledgePoints.map((kp, idx) => (
              <div key={idx} className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700">{kp.name}</span>
                  <span className="text-sm text-gray-500">掌握率 {kp.mastery}%</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      kp.mastery >= 70 ? 'bg-green-500' : kp.mastery >= 50 ? 'bg-orange-500' : 'bg-red-500'
                    }`}
                    style={{ width: `${kp.mastery}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 text-center">
            <BrainCircuit className="h-10 w-10 text-gray-200 mx-auto mb-3" />
            <p className="text-sm text-gray-500">作业批改完成后，将自动生成班级知识点掌握分析</p>
          </div>
        )}
        <div className="absolute inset-0 bg-white/40 backdrop-blur-[1px] pointer-events-none" style={{ top: '57px' }} />
      </div>

      {selectedStudent && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/30" onClick={() => { setSelectedStudent(null); setGradingResult(null) }} />
          <div className="relative w-full max-w-lg bg-white shadow-xl h-full overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-200 p-5 flex items-center justify-between z-10">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{selectedStudent.name} 的作业</h3>
                <p className="text-sm text-gray-500 mt-0.5">
                  {gradingResult ? `得分 ${gradingResult.score} · 错题 ${gradingResult.wrong_count}` :
                    datasetDetail?.title || '加载中...'}
                </p>
              </div>
              <button onClick={() => { setSelectedStudent(null); setGradingResult(null) }} className="p-2 hover:bg-gray-100 rounded-lg">
                <X className="h-5 w-5 text-gray-500" />
              </button>
            </div>
            <div className="p-5">
              {loadingResult ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
                </div>
              ) : gradingResult ? (
                <div className="space-y-3">
                  {gradingResult.grading_result?.questions?.map((q, idx) => (
                    <div key={idx} className={`p-3 rounded-lg border ${q.is_correct ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}`}>
                      <p className="text-sm font-medium">第{q.question_number}题 {q.is_correct ? '✓' : '✗'}</p>
                      <p className="text-xs text-gray-600 mt-1">学生答案：{q.student_answer}</p>
                      {!q.is_correct && <p className="text-xs text-green-700 mt-1">正确答案：{q.correct_answer}</p>}
                    </div>
                  ))}
                </div>
              ) : loadingDataset ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
                </div>
              ) : datasetDetail ? (
                <>
                  <div className="mb-4 p-3 bg-purple-50 border border-purple-100 rounded-lg">
                    <p className="text-xs text-purple-700">
                      数据来源：dataset/测试集/批改作业/{datasetDetail.filename}
                    </p>
                  </div>
                  <pre className="whitespace-pre-wrap text-xs text-gray-700 bg-gray-50 rounded-lg p-4 border max-h-96 overflow-y-auto">
                    {datasetDetail.student_content}
                  </pre>
                  <button
                    onClick={() => handleGradeWithDataset(selectedStudent)}
                    className="mt-4 w-full inline-flex items-center justify-center px-4 py-2.5 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
                  >
                    <FileCheck className="h-4 w-4 mr-2" />
                    使用此测试数据 AI 批改
                  </button>
                </>
              ) : (
                <p className="text-sm text-gray-500 text-center py-8">暂无详情</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default HomeworkDetail
