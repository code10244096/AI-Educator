const STUDENT_NAMES = [
  '张三', '李四', '王五', '赵六', '孙七', '周八', '吴九', '郑十',
  '陈一', '刘二', '杨三', '黄四', '林五', '何六', '高七', '马八',
  '罗九', '梁十', '宋一', '唐二', '许三', '韩四', '冯五', '邓六',
  '曹七', '彭八', '曾九', '萧十', '田一', '董二', '袁三', '潘四',
  '于五', '蒋六', '蔡七', '余八', '杜九', '叶十', '程一', '苏二',
  '魏三', '吕四', '丁五', '任六', '沈七',
]

const KNOWLEDGE_POINTS = {
  1: [
    { name: '三角函数图像', mastery: 72, weakCount: 8 },
    { name: '诱导公式', mastery: 65, weakCount: 12 },
    { name: '三角恒等变换', mastery: 58, weakCount: 15 },
  ],
  2: [
    { name: '等差数列求和', mastery: 81, weakCount: 5 },
    { name: '等比数列求和', mastery: 74, weakCount: 9 },
    { name: '递推数列', mastery: 62, weakCount: 11 },
  ],
  3: [
    { name: '空间几何体', mastery: 70, weakCount: 10 },
    { name: '线面关系', mastery: 66, weakCount: 13 },
    { name: '体积计算', mastery: 55, weakCount: 16 },
  ],
  4: [
    { name: '古典概型', mastery: 0, weakCount: 0 },
    { name: '条件概率', mastery: 0, weakCount: 0 },
    { name: '统计图表', mastery: 0, weakCount: 0 },
  ],
  5: [
    { name: '导数定义', mastery: 78, weakCount: 6 },
    { name: '单调性判断', mastery: 71, weakCount: 9 },
    { name: '极值与最值', mastery: 68, weakCount: 10 },
  ],
}

function generateSubmissions(homework) {
  const { id, submitted, total, status, avgScore } = homework
  const graded = status === '已批改'
  const students = []

  for (let i = 0; i < total; i++) {
    const name = STUDENT_NAMES[i] || `学生${i + 1}`
    const isSubmitted = i < submitted

    if (!isSubmitted) {
      students.push({
        id: i + 1,
        name,
        submitStatus: '未提交',
        submitTime: null,
        score: null,
        gradingStatus: '未提交',
        wrongCount: null,
        fileCount: 0,
      })
      continue
    }

    const hasTestData = homework.hasTestData && i === 0
    const datasetFileId = hasTestData ? homework.datasetFileId : null

    if (graded) {
      const variance = ((i * 17 + id * 7) % 31) - 15
      const score = hasTestData
        ? avgScore
        : Math.max(40, Math.min(100, Math.round(avgScore + variance)))
      students.push({
        id: i + 1,
        name,
        submitStatus: '已提交',
        submitTime: `${homework.date} ${String(8 + (i % 12)).padStart(2, '0')}:${String((i * 7) % 60).padStart(2, '0')}`,
        score,
        gradingStatus: '已批改',
        wrongCount: Math.round((100 - score) / 10),
        fileCount: hasTestData ? 1 : 1 + (i % 2),
        datasetFileId,
        isTestData: hasTestData,
      })
    } else {
      students.push({
        id: i + 1,
        name,
        submitStatus: '已提交',
        submitTime: `${homework.date} ${String(9 + (i % 10)).padStart(2, '0')}:${String((i * 5) % 60).padStart(2, '0')}`,
        score: null,
        gradingStatus: '待批改',
        wrongCount: null,
        fileCount: 1,
        datasetFileId,
        isTestData: hasTestData,
      })
    }
  }

  return students
}

// dataset/测试集/批改作业 中的 10 份高考数学作业集，id 与 dataset file_id 一一对应
const DATASET_HOMEWORK_META = [
  { id: 10, title: '高考数学作业集10', date: '2024-01-18', status: '待批改', submitted: 38, avgScore: 0 },
  { id: 9, title: '高考数学作业集9', date: '2024-01-15', status: '已批改', submitted: 42, avgScore: 90 },
  { id: 8, title: '高考数学作业集8', date: '2024-01-12', status: '已批改', submitted: 45, avgScore: 85 },
  { id: 7, title: '高考数学作业集7', date: '2024-01-10', status: '已批改', submitted: 44, avgScore: 78 },
  { id: 6, title: '高考数学作业集6', date: '2024-01-08', status: '已批改', submitted: 43, avgScore: 82 },
  { id: 5, title: '高考数学作业集5', date: '2024-01-05', status: '已批改', submitted: 45, avgScore: 88 },
  { id: 4, title: '高考数学作业集4', date: '2024-01-03', status: '已批改', submitted: 45, avgScore: 86 },
  { id: 3, title: '高考数学作业集3', date: '2024-01-01', status: '已批改', submitted: 44, avgScore: 80 },
  { id: 2, title: '高考数学作业集2', date: '2023-12-28', status: '已批改', submitted: 45, avgScore: 84 },
  { id: 1, title: '高考数学作业集1', date: '2023-12-25', status: '已批改', submitted: 45, avgScore: 87 },
]

const HOMEWORK_BY_CLASS = {
  class1: DATASET_HOMEWORK_META.map(hw => ({
    ...hw,
    datasetFileId: hw.id,
    deadline: hw.date,
    total: 45,
    description: `来自 dataset 测试集的真实作业数据（${hw.title}）`,
    hasTestData: true,
  })),
  class2: [
    {
      id: 1,
      title: '函数与导数综合',
      date: '2024-01-14',
      deadline: '2024-01-15',
      submitted: 40,
      total: 42,
      avgScore: 76.3,
      status: '已批改',
      description: '函数性质与导数应用综合练习',
    },
    {
      id: 2,
      title: '解析几何专项',
      date: '2024-01-10',
      deadline: '2024-01-11',
      submitted: 38,
      total: 42,
      avgScore: 0,
      status: '待批改',
      description: '直线、圆与圆锥曲线综合',
    },
  ],
  class3: [
    {
      id: 1,
      title: '不等式证明练习',
      date: '2024-01-13',
      deadline: '2024-01-14',
      submitted: 35,
      total: 40,
      avgScore: 74.5,
      status: '已批改',
      description: '基本不等式与证明方法训练',
    },
  ],
}

const submissionsCache = {}

export function getHomeworkList(classId) {
  return HOMEWORK_BY_CLASS[classId] || HOMEWORK_BY_CLASS.class1
}

export function getHomeworkById(classId, homeworkId) {
  const list = getHomeworkList(classId)
  return list.find(hw => hw.id === Number(homeworkId))
}

export function getStudentSubmissions(classId, homeworkId) {
  const key = `${classId}-${homeworkId}`
  if (!submissionsCache[key]) {
    const homework = getHomeworkById(classId, homeworkId)
    if (!homework) return []
    submissionsCache[key] = generateSubmissions(homework)
  }
  return submissionsCache[key]
}

export function getKnowledgePoints(homeworkId) {
  return KNOWLEDGE_POINTS[homeworkId] || []
}

export function getHomeworkStats(classId) {
  const list = getHomeworkList(classId)
  const current = list.find(hw => hw.status === '待批改') || list[0]

  const totalSubmitted = list.reduce((sum, hw) => sum + hw.submitted, 0)
  const totalStudents = list.reduce((sum, hw) => sum + hw.total, 0)
  const gradedHomeworks = list.filter(hw => hw.status === '已批改')
  const pendingHomeworks = list.filter(hw => hw.status === '待批改')

  const gradedSubmissions = gradedHomeworks.reduce((sum, hw) => sum + hw.submitted, 0)
  const pendingSubmissions = pendingHomeworks.reduce((sum, hw) => {
    const submissions = generateSubmissions(hw)
    return sum + submissions.filter(s => s.gradingStatus === '待批改').length
  }, 0)

  const avgScores = gradedHomeworks.map(hw => hw.avgScore).filter(s => s > 0)
  const avgScore = avgScores.length
    ? Math.round((avgScores.reduce((a, b) => a + b, 0) / avgScores.length) * 10) / 10
    : 0

  const submitRate = current.total > 0
    ? Math.round((current.submitted / current.total) * 1000) / 10
    : 0

  return {
    currentHomework: current,
    submitRate,
    submitted: current.submitted,
    notSubmitted: current.total - current.submitted,
    total: current.total,
    gradedCount: gradedSubmissions,
    pendingCount: pendingSubmissions,
    pendingHomeworkCount: pendingHomeworks.length,
    totalHomeworks: list.length,
    avgScore,
    passRate: 82.3,
  }
}

export function getGradingTasks(classId) {
  const list = getHomeworkList(classId)
  return list
    .filter(hw => hw.status === '待批改')
    .map(hw => {
      const submissions = generateSubmissions(hw)
      const pendingCount = submissions.filter(s => s.gradingStatus === '待批改').length
      const progress = hw.submitted > 0
        ? Math.round(((hw.submitted - pendingCount) / hw.submitted) * 100)
        : 0

      return {
        id: `hw-${classId}-${hw.id}`,
        type: 'homework-grading',
        title: `批改：${hw.title}`,
        homeworkId: hw.id,
        classId,
        status: pendingCount > 0 ? 'pending' : 'completed',
        progress,
        progressLabel: `已批改 ${hw.submitted - pendingCount}/${hw.submitted} 份`,
        pendingCount,
        submitted: hw.submitted,
        createdAt: hw.date,
        priority: pendingCount > 5 ? 'high' : 'medium',
      }
    })
}

export function getDatasetFileId(classId, homeworkId) {
  const homework = getHomeworkById(classId, homeworkId)
  return homework?.datasetFileId ?? null
}

export function getAlertStudents(classId) {
  const list = getHomeworkList(classId)
  const latestPending = list.find(hw => hw.status === '待批改')
  if (!latestPending) {
    return [
      { name: '吴九', score: 55, trend: 'down', warning: '近期平均分低于60分' },
      { name: '孙七', score: 58, trend: 'down', warning: '错题率持续偏高' },
    ]
  }

  const submissions = generateSubmissions(latestPending)
  const notSubmitted = submissions.filter(s => s.submitStatus === '未提交')

  return notSubmitted.slice(0, 3).map((s, idx) => ({
    name: s.name,
    score: null,
    trend: 'down',
    warning: idx === 0 ? '未提交当前作业' : '作业提交逾期',
  }))
}
