import React, { useState } from 'react'
import { Routes, Route, useNavigate, useLocation, useParams, Link } from 'react-router-dom'
import {
  ClipboardList,
  Archive,
  Users,
  TrendingUp,
  TrendingDown,
  AlertCircle,
  CheckCircle,
  Clock,
  BarChart3,
  Search,
  Plus,
  Edit,
  Eye,
  BookOpen,
  GraduationCap,
  Upload,
  XCircle,
  FileCheck,
  ChevronRight,
  ListTodo,
} from 'lucide-react'
import HomeworkDetail from './HomeworkDetail'
import { useHomeworkBoard } from '../hooks/useClassHomework'
import ClassStats from '../components/ClassStats'
import { classAPI } from '../utils/api'

const classInfo = {
  class1: { name: '高三1班', students: 45, subject: '数学' },
  class2: { name: '高三2班', students: 42, subject: '数学' },
  class3: { name: '高三3班', students: 40, subject: '数学' },
}

const HomeworkBoard = ({ classId }) => {
  const navigate = useNavigate()
  const info = classInfo[classId] || classInfo.class1
  const { stats: homeworkStats, homeworkList: recentHomework, gradingTasks, alertStudents, loading, error, reload } = useHomeworkBoard(classId)
  const [classStats, setClassStats] = React.useState(null)

  React.useEffect(() => {
    classAPI.getStats(classId).then(setClassStats).catch(() => setClassStats(null))
  }, [classId, homeworkStats])

  const currentHomework = homeworkStats?.currentHomework

  if (loading) {
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
                style={{ width: `${homeworkStats?.submitRate || 0}%` }}
              />
            </div>
          </div>
        </div>
      )}

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
              <p className="text-sm text-gray-500">班级平均分</p>
              <p className="text-2xl font-bold text-purple-600 mt-1">{homeworkStats.avgScore || '-'}</p>
            </div>
            <div className="p-3 bg-purple-50 rounded-lg">
              <BarChart3 className="h-6 w-6 text-purple-500" />
            </div>
          </div>
        </div>
      </div>

      {gradingTasks.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="p-5 border-b border-gray-200 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <ListTodo className="h-5 w-5 text-blue-500" />
              <h3 className="text-lg font-semibold text-gray-900">我的任务</h3>
              <span className="px-2 py-0.5 bg-orange-100 text-orange-700 text-xs rounded-full">
                {gradingTasks.length} 项待完成
              </span>
            </div>
            <Link to="/tasks" className="text-sm text-blue-600 hover:text-blue-800">
              查看全部任务
            </Link>
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
          <h3 className="text-lg font-semibold text-gray-900">最近作业</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50">
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">作业名称</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">日期</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">提交情况</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">平均分</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {recentHomework.map((hw) => (
                <tr
                  key={hw.id}
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
                          style={{ width: `${Math.round((hw.submitted / hw.total) * 100)}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-5 py-4 text-sm text-gray-900">{hw.avgScore > 0 ? hw.avgScore : '-'}</td>
                  <td className="px-5 py-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      hw.status === '已批改' ? 'bg-green-100 text-green-800' : 'bg-orange-100 text-orange-800'
                    }`}>
                      {hw.status}
                    </span>
                  </td>
                  <td className="px-5 py-4">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        navigate(`/class/${classId}/homework/${hw.id}`)
                      }}
                      className="text-blue-600 hover:text-blue-800 text-sm inline-flex items-center"
                    >
                      <Eye className="h-3.5 w-3.5 mr-1" />
                      查看
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
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
                    <span className="text-sm font-medium text-red-600">{student.name[0]}</span>
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
    </div>
  )
}

const ExamArchive = ({ classId }) => {
  const info = classInfo[classId] || classInfo.class1
  
  const exams = [
    { id: 1, name: '期末考试', date: '2024-01-20', avgScore: 82.5, highest: 98, lowest: 45, passRate: 88.9 },
    { id: 2, name: '期中考试', date: '2023-11-15', avgScore: 78.3, highest: 95, lowest: 38, passRate: 84.4 },
    { id: 3, name: '月考（12月）', date: '2023-12-10', avgScore: 75.8, highest: 92, lowest: 42, passRate: 82.2 },
    { id: 4, name: '月考（11月）', date: '2023-11-05', avgScore: 80.1, highest: 96, lowest: 50, passRate: 86.7 },
    { id: 5, name: '月考（10月）', date: '2023-10-08', avgScore: 77.5, highest: 94, lowest: 40, passRate: 83.3 },
  ]
  
  const scoreDistribution = [
    { range: '90-100', count: 8, percentage: 17.8 },
    { range: '80-89', count: 15, percentage: 33.3 },
    { range: '70-79', count: 12, percentage: 26.7 },
    { range: '60-69', count: 6, percentage: 13.3 },
    { range: '60以下', count: 4, percentage: 8.9 },
  ]
  
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">考试档案</h2>
          <p className="text-sm text-gray-500 mt-1">{info.name} · {info.subject} · 历次考试成绩</p>
        </div>
        <button className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
          <Plus className="h-4 w-4 mr-2" />
          录入成绩
        </button>
      </div>
      
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="p-5 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">历次考试</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50">
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">考试名称</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">日期</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">平均分</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">最高分</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">最低分</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">及格率</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {exams.map((exam) => (
                <tr key={exam.id} className="hover:bg-gray-50">
                  <td className="px-5 py-4 text-sm font-medium text-gray-900">{exam.name}</td>
                  <td className="px-5 py-4 text-sm text-gray-500">{exam.date}</td>
                  <td className="px-5 py-4 text-sm text-gray-900">{exam.avgScore}</td>
                  <td className="px-5 py-4 text-sm text-green-600">{exam.highest}</td>
                  <td className="px-5 py-4 text-sm text-red-600">{exam.lowest}</td>
                  <td className="px-5 py-4 text-sm text-gray-900">{exam.passRate}%</td>
                  <td className="px-5 py-4">
                    <div className="flex items-center space-x-2">
                      <button className="text-blue-600 hover:text-blue-800 text-sm">详情</button>
                      <button className="text-gray-400 hover:text-gray-600 text-sm">导出</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="p-5 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">成绩分布（期末考试）</h3>
        </div>
        <div className="p-5">
          <div className="space-y-3">
            {scoreDistribution.map((item, idx) => (
              <div key={idx} className="flex items-center space-x-4">
                <span className="text-sm text-gray-600 w-16">{item.range}</span>
                <div className="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-end pr-2"
                    style={{ width: `${item.percentage}%` }}
                  >
                    <span className="text-xs text-white font-medium">{item.count}人</span>
                  </div>
                </div>
                <span className="text-sm text-gray-500 w-12 text-right">{item.percentage}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

const ClassMembers = ({ classId }) => {
  const info = classInfo[classId] || classInfo.class1
  const [searchTerm, setSearchTerm] = useState('')
  
  const students = [
    { id: 1, name: '张三', gender: '男', avgScore: 85.2, rank: 3, trend: 'up', status: '优秀' },
    { id: 2, name: '李四', gender: '女', avgScore: 92.5, rank: 1, trend: 'up', status: '优秀' },
    { id: 3, name: '王五', gender: '男', avgScore: 78.3, rank: 8, trend: 'down', status: '良好' },
    { id: 4, name: '赵六', gender: '女', avgScore: 88.7, rank: 4, trend: 'stable', status: '优秀' },
    { id: 5, name: '孙七', gender: '男', avgScore: 65.2, rank: 25, trend: 'down', status: '待提高' },
    { id: 6, name: '周八', gender: '女', avgScore: 72.8, rank: 15, trend: 'up', status: '良好' },
    { id: 7, name: '吴九', gender: '男', avgScore: 55.3, rank: 35, trend: 'down', status: '预警' },
    { id: 8, name: '郑十', gender: '女', avgScore: 90.1, rank: 2, trend: 'up', status: '优秀' },
  ]
  
  const filteredStudents = students.filter(s =>
    s.name.toLowerCase().includes(searchTerm.toLowerCase())
  )
  
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">班级成员</h2>
          <p className="text-sm text-gray-500 mt-1">{info.name} · {info.students}名学生</p>
        </div>
        <button className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
          <Plus className="h-4 w-4 mr-2" />
          添加学生
        </button>
      </div>
      
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="p-5 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">学生列表</h3>
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
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50">
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">姓名</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">性别</th>
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
                  <td className="px-5 py-4 text-sm text-gray-500">{student.gender}</td>
                  <td className="px-5 py-4 text-sm font-medium text-gray-900">{student.avgScore}</td>
                  <td className="px-5 py-4 text-sm text-gray-500">第 {student.rank} 名</td>
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
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      student.status === '优秀' ? 'bg-green-100 text-green-800' :
                      student.status === '良好' ? 'bg-blue-100 text-blue-800' :
                      student.status === '待提高' ? 'bg-orange-100 text-orange-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {student.status}
                    </span>
                  </td>
                  <td className="px-5 py-4">
                    <div className="flex items-center space-x-2">
                      <button className="text-blue-600 hover:text-blue-800 text-sm">
                        <Eye className="h-4 w-4" />
                      </button>
                      <button className="text-gray-400 hover:text-gray-600 text-sm">
                        <Edit className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

const ClassDetail = () => {
  const { classId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const info = classInfo[classId] || classInfo.class1
  
  const tabs = [
    { id: 'homework', label: '作业看板', icon: ClipboardList, path: `/class/${classId}/homework` },
    { id: 'exams', label: '考试档案', icon: Archive, path: `/class/${classId}/exams` },
    { id: 'members', label: '班级成员', icon: Users, path: `/class/${classId}/members` },
  ]
  
  const getCurrentTab = () => {
    const path = location.pathname
    if (path.includes('/exams')) return 'exams'
    if (path.includes('/members')) return 'members'
    return 'homework'
  }
  
  const currentTab = getCurrentTab()
  
  return (
    <div className="p-6">
      <div className="flex items-center space-x-3 mb-6">
        <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-500 rounded-lg flex items-center justify-center">
          <GraduationCap className="h-5 w-5 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900">{info.name}</h1>
          <p className="text-sm text-gray-500">{info.subject} · {info.students}名学生</p>
        </div>
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
      
      {currentTab === 'homework' && <HomeworkBoard classId={classId} />}
      {currentTab === 'exams' && <ExamArchive classId={classId} />}
      {currentTab === 'members' && <ClassMembers classId={classId} />}
    </div>
  )
}

const ClassData = () => {
  return (
    <Routes>
      <Route path=":classId/homework/:homeworkId" element={<HomeworkDetail />} />
      <Route path=":classId/*" element={<ClassDetail />} />
      <Route path="/" element={
        <div className="p-6 flex items-center justify-center h-64">
          <div className="text-center">
            <Users className="h-12 w-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500">请从左侧选择一个班级</p>
          </div>
        </div>
      } />
    </Routes>
  )
}

export default ClassData
