import React, { useMemo, lazy, Suspense } from 'react'
import ReactMarkdown from 'react-markdown'
import { toMarkdownMath } from '../utils/mathText'

// Markdown + 公式渲染（教案、变式题等长文本）。由 MathText 的 markdown 模式按需加载。
// rehype-katex / katex CSS 只在正文确实含公式时才拉取，避免打开页面就下 261KB。
const MarkdownMathKatex = lazy(() => import('./MarkdownMathKatex'))

const hasMarkdownMath = (source) =>
  /\$\$[\s\S]+?\$\$|\$[^$\n]+\$|\\begin\{[a-zA-Z*]+\}/.test(source)

const PlainMarkdown = ({ source, className, components }) => (
  <div className={`markdown-math break-words ${className}`}>
    <ReactMarkdown components={components}>{source}</ReactMarkdown>
  </div>
)

const MarkdownMath = ({ text, className = '', components }) => {
  const source = useMemo(() => toMarkdownMath(text), [text])
  const needsKatex = hasMarkdownMath(source)

  if (!needsKatex) {
    return <PlainMarkdown source={source} className={className} components={components} />
  }

  return (
    <Suspense fallback={<PlainMarkdown source={source} className={className} components={components} />}>
      <MarkdownMathKatex text={text} className={className} components={components} />
    </Suspense>
  )
}

export default MarkdownMath
