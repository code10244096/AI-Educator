export const STAGE_SUBJECTS = {
  小学: ['语文', '数学', '英语'],
  初中: ['语文', '数学', '英语', '物理', '化学', '生物', '政治', '历史', '地理'],
  高中: ['语文', '数学', '英语', '物理', '化学', '生物', '政治', '历史', '地理'],
  大学: ['数学', '大学物理', '大学化学', '大学英语', '计算机', '大学语文', '经济学', '管理学'],
}

const GRADES_BY_STAGE = {
  小学: ['一年级', '二年级', '三年级', '四年级', '五年级', '六年级'],
  初中: ['初一', '初二', '初三'],
  高中: ['高一', '高二', '高三'],
  大学: ['本科'],
}

const NAME_EXAMPLES = {
  小学: '例如：三年级2班',
  初中: '例如：初二3班',
  高中: '例如：高一5班',
  大学: '例如：计算机1班',
}

export function gradesFor(stage) {
  return GRADES_BY_STAGE[stage] || GRADES_BY_STAGE['高中']
}

export function subjectsFor(stage) {
  return STAGE_SUBJECTS[stage] || []
}

export function classNameExample(stage) {
  return NAME_EXAMPLES[stage] || NAME_EXAMPLES['高中']
}

export function defaultSubject(stage, subject) {
  const options = subjectsFor(stage)
  if (subject && options.includes(subject)) return subject
  return options[0] || ''
}
