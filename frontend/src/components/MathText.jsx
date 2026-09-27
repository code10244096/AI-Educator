import React, { Suspense, lazy, useEffect, useMemo, useState } from 'react'
import { splitMath, cleanTex, normalizeMathText } from '../utils/mathText'

/*
 * 数学公式统一渲染组件（R1-012）
 *
 *   <MathText text={q.question_text} />                 行内文本（题干、学生答案、解析……）
 *   <MathText text={q.explanation} block />             块级（外层 div）
 *   <MathText text={plan.content} markdown />           Markdown 文档（教案、变式题），含标题/列表
 *
 * - 支持 \( \)、\[ \]、$…$、$$…$$、\displaystyle、字面量 \n，以及不带定界符的裸 LaTeX（\frac、x^2、x_1）
 * - KaTeX 与其 CSS 在首次遇到公式时才加载；加载完成前公式段以原文淡色显示
 * - 任一公式渲染失败时该段显示原文，不抛异常、不白屏
 */

let katexLib = null
let katexPromise = null

export function loadKatex() {
  if (katexLib) return Promise.resolve(katexLib)
  if (!katexPromise) {
    katexPromise = Promise.all([import('katex'), import('katex/dist/katex.min.css')])
      .then(([mod]) => {
        katexLib = mod.default || mod
        return katexLib
      })
      .catch((err) => {
        katexPromise = null
        throw err
      })
  }
  return katexPromise
}

const renderCache = new Map()
const CACHE_LIMIT = 800

function renderTex(katex, tex, display) {
  const key = `${display ? 'D' : 'I'}${tex}`
  if (renderCache.has(key)) return renderCache.get(key)
  let html = null
  try {
    html = katex.renderToString(cleanTex(tex), {
      displayMode: display,
      throwOnError: true,
      strict: 'ignore',
      trust: false,
      output: 'html',
    })
  } catch {
    html = null // 非法 LaTeX：交给调用方显示原文
  }
  if (renderCache.size > CACHE_LIMIT) renderCache.clear()
  renderCache.set(key, html)
  return html
}

function useKatex(needed) {
  const [katex, setKatex] = useState(katexLib)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    if (!needed || katex) return undefined
    let alive = true
    loadKatex()
      .then((k) => { if (alive) setKatex(() => k) })
      .catch(() => { if (alive) setFailed(true) })
    return () => { alive = false }
  }, [needed, katex])
  return { katex, failed }
}

// 文字段：保留换行
const TextSegment = ({ text }) => {
  const lines = text.split('\n')
  return lines.map((line, i) => (
    <React.Fragment key={i}>
      {i > 0 && <br />}
      {line}
    </React.Fragment>
  ))
}

const MathSegment = ({ token, katex, failed }) => {
  if (katex) {
    const html = renderTex(katex, token.tex, token.display)
    if (html) {
      return token.display ? (
        <span className="block max-w-full overflow-x-auto overflow-y-hidden py-1" dangerouslySetInnerHTML={{ __html: html }} />
      ) : (
        <span className="math-inline" dangerouslySetInnerHTML={{ __html: html }} />
      )
    }
    return <span className="math-raw break-all">{token.raw}</span>
  }
  // KaTeX 未就绪（首次加载中）或加载失败：显示原文
  return <span className={`break-all ${failed ? '' : 'text-gray-400'}`}>{token.raw}</span>
}

class MathErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidUpdate(prevProps) {
    if (prevProps.text !== this.props.text && this.state.hasError) {
      this.setState({ hasError: false })
    }
  }

  render() {
    if (this.state.hasError) return this.props.fallback
    return this.props.children
  }
}

const MarkdownMath = lazy(() => import('./MarkdownMath'))

const PlainFallback = ({ text, className, muted }) => (
  <div className={`${className || ''} whitespace-pre-wrap break-words ${muted ? 'text-gray-400' : ''}`}>
    {normalizeMathText(text)}
  </div>
)

const InlineMathText = ({ text, block, className }) => {
  const tokens = useMemo(() => splitMath(text), [text])
  const hasMath = tokens.some(t => t.type === 'math')
  const { katex, failed } = useKatex(hasMath)
  const Tag = block ? 'div' : 'span'
  return (
    <Tag className={`math-text break-words ${className || ''}`}>
      {tokens.map((t, i) => (t.type === 'text'
        ? <TextSegment key={i} text={t.text} />
        : <MathSegment key={i} token={t} katex={katex} failed={failed} />))}
    </Tag>
  )
}

const MathText = ({ text, block = false, markdown = false, className = '', components }) => {
  if (text === null || text === undefined || text === '') return null
  const str = typeof text === 'string' ? text : String(text)
  const fallback = <PlainFallback text={str} className={className} />

  if (markdown) {
    return (
      <MathErrorBoundary text={str} fallback={fallback}>
        <Suspense fallback={<PlainFallback text={str} className={className} muted />}>
          <MarkdownMath text={str} className={className} components={components} />
        </Suspense>
      </MathErrorBoundary>
    )
  }

  return (
    <MathErrorBoundary text={str} fallback={block ? fallback : <span className={className}>{normalizeMathText(str)}</span>}>
      <InlineMathText text={str} block={block} className={className} />
    </MathErrorBoundary>
  )
}

export default MathText
