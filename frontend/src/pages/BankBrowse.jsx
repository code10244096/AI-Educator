import React, { useCallback, useEffect, useState } from 'react'
import { BookOpen, ChevronLeft, ChevronRight, Loader2, Search } from 'lucide-react'
import { Link } from 'react-router-dom'
import { questionBankAPI, getErrorMessage } from '../utils/api'
import { useAuth } from '../context/AuthContext'
import { BANK_STAGES } from '../utils/stageSubjects'
import MathText from '../components/MathText'
import PageBackground from '../components/PageBackground'

const PAGE_SIZE = 20
const SEARCH_OFFSET_CAP = 10000
const FALLBACK_SUBJECT = '数学'

const previewText = (text) => (text || '').replace(/\s+/g, ' ').trim()

const GRADE_LABELS = { 10: '高一', 11: '高二', 12: '高三' }
const gradeLabel = (grade) => GRADE_LABELS[grade] || (grade ? `${grade}年级` : '')

const DifficultyDots = ({ level }) => {
  const n = Math.max(1, Math.min(5, Number(level) || 0))
  if (!n) return null
  return (
    <span className="inline-flex items-center gap-0.5" title={`难度 ${level}`}>
      {Array.from({ length: 5 }, (_, i) => (
        <span key={i} className={`h-1.5 w-1.5 rounded-full ${i < n ? 'bg-teal-500' : 'bg-gray-200'}`} />
      ))}
    </span>
  )
}

const BankBrowse = () => {
  const { user } = useAuth()
  const subject = user?.subject ? user.subject : FALLBACK_SUBJECT
  const [stage, setStage] = useState(user?.education_stage && BANK_STAGES.includes(user.education_stage) ? user.education_stage : '')
  const [keyword, setKeyword] = useState('')
  const [appliedKeyword, setAppliedKeyword] = useState('')
  const [items, setItems] = useState([])
  const [fuzzy, setFuzzy] = useState(false)
  const [semantic, setSemantic] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [cursors, setCursors] = useState([null])
  const [truncated, setTruncated] = useState(false)
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)

  useEffect(() => {
    document.title = '题库 - AI 教学助手'
    return () => { document.title = 'AI 教学助手' }
  }, [])

  const loadList = useCallback(async (afterId, kw, offset = 0) => {
    setLoading(true)
    setError(null)
    setTruncated(false)
    try {
      const query = (kw || '').trim()
      let rows
      if (query) {
        const data = await questionBankAPI.search(query, subject, stage || undefined, PAGE_SIZE, offset)
        rows = data.results || []
        setFuzzy(Boolean(data.fuzzy))
        setSemantic(Boolean(data.semantic))
      } else {
        rows = await questionBankAPI.getList({
          subject,
          education_level: stage || undefined,
          limit: PAGE_SIZE,
          after_id: afterId || undefined,
        })
        setFuzzy(false)
        setSemantic(false)
      }
      setItems(rows)
      setSelected((prev) => (rows.some((q) => q.id === prev) ? prev : (rows[0]?.id || null)))
    } catch (err) {
      setItems([])
      setFuzzy(false)
      setSemantic(false)
      setError(getErrorMessage(err, '题库加载失败'))
    } finally {
      setLoading(false)
    }
  }, [subject, stage])

  const authPending = user === undefined

  useEffect(() => {
    if (authPending) return
    setCursors([null])
    setTruncated(false)
    setAppliedKeyword('')
    setKeyword('')
    loadList(null, '')
  }, [loadList, authPending])

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
    setTruncated(false)
    setCursors(q ? [0] : [null])
    loadList(null, q, 0)
  }

  const goNext = () => {
    if (appliedKeyword) {
      const currentOffset = typeof cursors[cursors.length - 1] === 'number' ? cursors[cursors.length - 1] : 0
      const nextOffset = currentOffset + PAGE_SIZE
      if (nextOffset >= SEARCH_OFFSET_CAP) {
        setTruncated(true)
        setError('结果过多，请细化筛选')
        return
      }
      setCursors([...cursors, nextOffset])
      loadList(null, appliedKeyword, nextOffset)
      return
    }
    const lastId = items[items.length - 1]?.id
    if (!lastId) return
    const next = [...cursors, lastId]
    setCursors(next)
    loadList(lastId, '')
  }

  const goPrev = () => {
    if (cursors.length <= 1) return
    const next = cursors.slice(0, -1)
    setCursors(next)
    if (appliedKeyword) {
      const offset = typeof next[next.length - 1] === 'number' ? next[next.length - 1] : 0
      loadList(null, appliedKeyword, offset)
      return
    }
    loadList(next[next.length - 1], '')
  }

  const searchOffset = appliedKeyword && typeof cursors[cursors.length - 1] === 'number'
    ? cursors[cursors.length - 1]
    : 0
  const page = cursors.length
  const hasNext = items.length === PAGE_SIZE && !(appliedKeyword && searchOffset + PAGE_SIZE >= SEARCH_OFFSET_CAP)
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
              <p className="text-sm text-gray-600">{subject}题库 · 检索题目，用于教案生成参考</p>
            </div>
          </div>

          {user && (!user.education_stage || !user.subject) && (
            <p className="mb-4 rounded-lg border border-amber-100 bg-amber-50 px-3 py-2 text-xs text-amber-700">
              在<Link to="/settings" className="mx-0.5 font-medium underline">个人资料</Link>里填写任教学段和学科后，这里会默认只展示你的学段与学科。
            </p>
          )}

          <div className="flex flex-wrap items-end gap-3">
            <label className="text-xs text-gray-500">
              学段
              <select
                value={stage}
                onChange={(e) => {
                  setStage(e.target.value)
                }}
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
                placeholder="输入想找的知识点或题目类型，支持语义搜索：三角函数图象、导数单调性、线面垂直…"
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
                {subject}
                {stage ? ` · ${stage}` : ''}
                {appliedKeyword ? ` · “${appliedKeyword}”` : ''}
              </h2>
              <div className="flex items-center gap-1">
                <button type="button" onClick={goPrev} disabled={!hasPrev || loading} className="rounded p-1 text-gray-500 hover:bg-gray-100 disabled:opacity-40" aria-label="上一页">
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="min-w-[3rem] text-center text-xs text-gray-400">第 {page} 页</span>
                <button type="button" onClick={goNext} disabled={!hasNext || loading} className="rounded p-1 text-gray-500 hover:bg-gray-100 disabled:opacity-40" aria-label="下一页">
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
            {truncated && (
              <p className="border-b border-amber-100 bg-amber-50 px-4 py-2 text-xs text-amber-700">结果过多，请细化筛选</p>
            )}
            {appliedKeyword && semantic && items.length > 0 && (
              <p className="border-b border-teal-50 bg-teal-50/60 px-4 py-2 text-xs text-teal-700">
                已按语义理解排序，优先展示与“{appliedKeyword}”最相关的题目
              </p>
            )}
            {appliedKeyword && !semantic && fuzzy && items.length > 0 && (
              <p className="border-b border-teal-50 bg-teal-50/60 px-4 py-2 text-xs text-teal-700">
                没有完全匹配的结果，已为你按相关度模糊匹配 {items.length} 条
              </p>
            )}
            {loading && items.length === 0 ? (
              <p className="flex items-center justify-center gap-2 p-8 text-sm text-gray-400" role="status">
                <Loader2 className="h-4 w-4 animate-spin" />加载中…
              </p>
            ) : error && items.length === 0 ? (
              <p className="p-8 text-center text-sm text-red-600">{error}</p>
            ) : items.length === 0 ? (
              <p className="p-8 text-center text-sm text-gray-500">
                {appliedKeyword
                  ? (fuzzy
                    ? '模糊匹配也没有找到相关题目，换个关键词试试（如：三角、导数、力学）'
                    : '没有找到相关题目，试试更短的关键词（如：三角、导数）')
                  : '你的学科在当前学段下暂无题目，可切换学段或搜索其他关键词'}
              </p>
            ) : (
              <ul className="divide-y divide-gray-50">
                {items.map((q) => (
                  <li key={q.id}>
                    <button
                      type="button"
                      onClick={() => setSelected(q.id)}
                      className={`block w-full px-4 py-3 text-left hover:bg-teal-50/60 ${selected === q.id ? 'bg-teal-50' : ''}`}
                    >
                      <p className="line-clamp-2 text-sm text-gray-800"><MathText text={previewText(q.question_text)} /></p>
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
                  {detail.grade ? <span>{gradeLabel(detail.grade)}</span> : null}
                  {detail.question_type && <span>{detail.question_type}</span>}
                  {detail.difficulty ? <DifficultyDots level={detail.difficulty} /> : null}
                  {[detail.exam_type, detail.year, detail.region].filter(Boolean).length > 0 && (
                    <span className="text-gray-400">{[detail.exam_type, detail.year, detail.region].filter(Boolean).join(' · ')}</span>
                  )}
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
                {detail.common_mistakes ? (
                  <div>
                    <h3 className="mb-2 text-xs font-medium text-gray-400">常见错误</h3>
                    <p className="text-sm text-gray-700">{detail.common_mistakes}</p>
                  </div>
                ) : null}
                {(detail.variants || []).length > 0 && (
                  <div>
                    <h3 className="mb-2 text-xs font-medium text-gray-400">变式题</h3>
                    <ul className="space-y-3">
                      {detail.variants.map((v) => (
                        <li key={v.id} className="rounded-lg border border-gray-100 bg-gray-50/60 p-3">
                          {v.variant_type ? <p className="mb-1 text-xs text-teal-600">{v.variant_type}</p> : null}
                          <div className="text-sm text-gray-800"><MathText text={v.question_text} markdown /></div>
                          {v.answer ? (
                            <div className="mt-2 text-sm text-gray-600">
                              <span className="mr-1 text-xs text-gray-400">答案</span>
                              <MathText text={v.answer} />
                            </div>
                          ) : null}
                          {v.solution ? (
                            <div className="mt-1 text-sm text-gray-600">
                              <span className="mr-1 text-xs text-gray-400">解析</span>
                              <MathText text={v.solution} markdown />
                            </div>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
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
