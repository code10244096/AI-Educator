import React, { useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'
import { toMarkdownMath } from '../utils/mathText'

// Markdown + 公式渲染（教案、变式题等长文本）。由 MathText 的 markdown 模式按需加载，不进首屏包。
const REMARK_PLUGINS = [remarkMath]
const REHYPE_PLUGINS = [[rehypeKatex, { strict: 'ignore', output: 'html' }]]

const MarkdownMath = ({ text, className = '', components }) => {
  const source = useMemo(() => toMarkdownMath(text), [text])
  return (
    <div className={`markdown-math break-words ${className}`}>
      <ReactMarkdown remarkPlugins={REMARK_PLUGINS} rehypePlugins={REHYPE_PLUGINS} components={components}>
        {source}
      </ReactMarkdown>
    </div>
  )
}

export default MarkdownMath
