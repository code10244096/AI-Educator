import React, { useCallback, useEffect, useState } from 'react'
import { BookOpen, ChevronLeft, ChevronRight, Loader2, Search } from 'lucide-react'
import { questionBankAPI, getErrorMessage } from '../utils/api'
import { useAuth } from '../context/AuthContext'
import { BANK_STAGES, BANK_SUBJECTS, bankSubjects } from '../utils/stageSubjects'
import MathText from '../components/MathText'
import PageBackground from '../components/PageBackground'

const PAGE_SIZE = 20

const previewText = (text) => (text || '').replace(/\s+/g, ' ').trim()

const BankBrowse = () => {
  const { user } = useAuth()
  const [subjects, setSubjects] = useState(BANK_SUBJECTS)
  const [counts, setCounts] = useState({})
  const [subject, setSubject] = useState(user?.subject || '语文')
  const [stage, setStage] = useState(user?.education_stage && BANK_STAGES.includes(user.education_stage) ? user.education_stage : '')
  const [keyword, setKeyword] = useState('')
  const [appliedKeyword, setAppliedKeyword] = useState('')
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [cursors, setCursors] = useState([null])
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)

  useEffect(() => {
    document.title = '题库 - AI 教学助手'
    return () => { document.title = 'AI 教学助手' }
  }, [])

  useEffect(() => {
    questionBankAPI.getSubjects()
      .then((data) => {
        setSubjects(bankSubjects(data.subjects || []))
        setCounts(data.by_subject || {})
      })
      .catch(() => {
        questionBankAPI.getStats()
          .then((data) => {
            setSubjects(bankSubjects(Object.keys(data.by_subject || {})))
            setCounts(data.by_subject || {})
          })
          .catch(() => {})
      })
  }, [])

  const loadList = useCallback(async (afterId, kw) => {
    setLoading(true)
    setError(null)
    try {
      const query = (kw || '').trim()
      let rows
      if (query) {
        rows = await questionBankAPI.search(query, subject || undefined, stage || undefined, PAGE_SIZE)
      } else {
        rows = await questionBankAPI.getList({
          subject: subject || undefined,
          education_level: stage || undefined,
          limit: PAGE_SIZE,
          after_id: afterId || undefined,
        })
      }
      setItems(rows)
      setSelected((prev) => (rows.some((q) => q.id === prev) ? prev : (rows[0]?.id || null)))
    } catch (err) {
      setItems([])
      setError(getErrorMessage(err, '题库加载失败'))
    } finally {
      setLoading(false)
    }
  }, [subject, stage])

  useEffect(() => {
    setCursors([null])
    setAppliedKeyword('')
    setKeyword('')
    loadList(null, '')
  }, [loadList])

  useEffect(() => {
    if (!selected) {
      setDetail(null)
      return undefined
    }
    let cancelled = false
    setDetailLoading(true)
    questionBankAPI.getById(selected)
      .then((data) => { if (!cancelled) setDetail(data) })
      .catch((err) => { if (!cancelled) setError(getErrorMessage(err, '题目详情加载失败')) })
      .finally(() => { if (!cancelled) setDetailLoading(false) })
    return () => { cancelled = true }
  }, [selected])

  const handleSearch = () => {
    const q = keyword.trim()
    setAppliedKeyword(q)
    setCursors([null])
    loadList(null, q)
  }

  const goNext = () => {
    const lastId = items[items.length - 1]?.id
    if (!lastId || appliedKeyword) return
    const next = [...cursors, lastId]
    setCursors(next)
    loadList(lastId, '')
  }

  const goPrev = () => {
    if (cursors.length <= 1) return
    const next = cursors.slice(0, -1)
    setCursors(next)
    loadList(next[next.length - 1], appliedKeyword)
  }

  const page = cursors.length
  const hasNext = !appliedKeyword && items.length === PAGE_SIZE
  const hasPrev = cursors.length > 1

  return (
    <PageBackground gradient="bank">
      <div className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
        <div className="rounded-2xl border border-white/20 bg-white/90 p-6 shadow-xl backdrop-blur-md">
          <div className="mb-6 flex items-center space-x-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-teal-500 to-cyan-500 shadow-lg">
              <BookOpen className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-teal-600 to-cyan-600">题库</h1>
              <p className="text-sm text-gray-600">按学科浏览、检索题目，用于教案生成参考</p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2" role="tablist" aria-label="学科">
            {bankSubjects([subject, ...subjects]).map((item) => {
              const active = subject === item
              const count = counts[item]
              return (
                <button
                  key={item}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  onClick={() => setSubject(item)}
                  className={`rounded-full border px-3 py-1.5 text-sm ${
                    active
                      ? 'border-teal-600 bg-teal-50 font-medium text-teal-800'
                      : 'border-gray-200 text-gray-700 hover:border-teal-300 hover:bg-teal-50/50'
                  }`}
                >
                  {item}
                  {count != null ? <span className="ml-1 text-xs text-gray-400">{count}</span> : null}
                </button>
              )
            })}
          </div>

          <div className="mt-4 flex flex-wrap items-end gap-3">
            <label className="text-xs text-gray-500">
              学段
              <select
                value={stage}
                onChange={(e) => setStage(e.target.value)}
                className="mt-1 block rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
              >
                <option value="">全部学段</option>
                {BANK_STAGES.map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
            </label>
            <div className="relative min-w-[16rem] flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleSearch() }}
                placeholder="搜索题干关键词，回车"
                className="w-full rounded-lg border border-gray-300 py-2 pl-9 pr-3 text-sm"
              />
            </div>
            <button
              type="button"
              onClick={handleSearch}
              className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700"
            >
              搜索
            </button>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-5">
          <section className="rounded-2xl border border-white/20 bg-white/90 shadow-xl backdrop-blur-md lg:col-span-2">
            <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
              <h2 className="text-sm font-medium text-gray-700">
                {subject || '全部学科'}
                {stage ? ` · ${stage}` : ''}
                {appliedKeyword ? ` · “${appliedKeyword}”` : ''}
              </h2>
              <div className="flex items-center gap-1">
                <button type="button" onClick={goPrev} disabled={!hasPrev || loading} className="rounded p-1 text-gray-500 hover:bg-gray-100 disabled:opacity-40" aria-label="上一页">
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="min-w-[2rem] text-center text-xs text-gray-400">{page}</span>
                <button type="button" onClick={goNext} disabled={!hasNext || loading} className="rounded p-1 text-gray-500 hover:bg-gray-100 disabled:opacity-40" aria-label="下一页">
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
            {loading && items.length === 0 ? (
              <p className="flex items-center justify-center gap-2 p-8 text-sm text-gray-400" role="status">
                <Loader2 className="h-4 w-4 animate-spin" />加载中…
              </p>
            ) : error && items.length === 0 ? (
              <p className="p-8 text-center text-sm text-red-600">{error}</p>
            ) : items.length === 0 ? (
              <p className="p-8 text-center text-sm text-gray-500">这个筛选下没有题目</p>
            ) : (
              <ul className="divide-y divide-gray-50">
                {items.map((q) => (
                  <li key={q.id}>
                    <button
                      type="button"
                      onClick={() => setSelected(q.id)}
                      className={`block w-full px-4 py-3 text-left hover:bg-teal-50/60 ${selected === q.id ? 'bg-teal-50' : ''}`}
                    >
                      <p className="line-clamp-2 text-sm text-gray-800">{previewText(q.question_text)}</p>
                      <p className="mt-1 text-xs text-gray-400">
                        {[q.subject, q.education_level, q.question_type].filter(Boolean).join(' · ')}
                      </p>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="rounded-2xl border border-white/20 bg-white/90 p-5 shadow-xl backdrop-blur-md lg:col-span-3">
            {!selected ? (
              <p className="py-16 text-center text-sm text-gray-400">从左侧选择一道题查看详情</p>
            ) : detailLoading && !detail ? (
              <p className="flex items-center justify-center gap-2 py-16 text-sm text-gray-400" role="status">
                <Loader2 className="h-4 w-4 animate-spin" />正在打开题目
              </p>
            ) : detail ? (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500">
                  <span className="rounded-full bg-teal-50 px-2 py-0.5 text-teal-700">{detail.subject}</span>
                  {detail.education_level && <span>{detail.education_level}</span>}
                  {detail.grade ? <span>{detail.grade}年级</span> : null}
                  {detail.question_type && <span>{detail.question_type}</span>}
                  {detail.difficulty ? <span>难度 {detail.difficulty}</span> : null}
                </div>
                <div>
                  <h3 className="mb-2 text-xs font-medium text-gray-400">题目</h3>
                  <div className="text-sm text-gray-800"><MathText text={detail.question_text} markdown /></div>
                </div>
                <div>
                  <h3 className="mb-2 text-xs font-medium text-gray-400">答案</h3>
                  <div className="text-sm text-gray-800"><MathText text={detail.answer || '暂无'} /></div>
                </div>
                {detail.solution ? (
                  <div>
                    <h3 className="mb-2 text-xs font-medium text-gray-400">解析</h3>
                    <div className="text-sm text-gray-700"><MathText text={detail.solution} markdown /></div>
                  </div>
                ) : null}
                {detail.teaching_tips ? (
                  <div>
                    <h3 className="mb-2 text-xs font-medium text-gray-400">教学提示</h3>
                    <p className="text-sm text-gray-700">{detail.teaching_tips}</p>
                  </div>
                ) : null}
                {detail.common_mistakes ? (
                  <div>
                    <h3 className="mb-2 text-xs font-medium text-gray-400">常见错误</h3>
                    <p className="text-sm text-gray-700">{detail.common_mistakes}</p>
                  </div>
                ) : null}
                {(detail.knowledge_points || []).length > 0 && (
                  <p className="text-xs text-gray-400">知识点：{detail.knowledge_points.join('、')}</p>
                )}
              </div>
            ) : (
              <p className="py-16 text-center text-sm text-gray-400">无法加载这道题</p>
            )}
          </section>
        </div>
      </div>
    </PageBackground>
  )
}

export default BankBrowse
