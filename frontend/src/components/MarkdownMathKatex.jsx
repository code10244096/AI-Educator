import React, { useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'
import { toMarkdownMath } from '../utils/mathText'

const REMARK_PLUGINS = [remarkMath]
const REHYPE_PLUGINS = [[rehypeKatex, { strict: 'ignore', output: 'html' }]]

const MarkdownMathKatex = ({ text, className = '', components }) => {
  const source = useMemo(() => toMarkdownMath(text), [text])
  return (
    <div className={`markdown-math break-words ${className}`}>
      <ReactMarkdown remarkPlugins={REMARK_PLUGINS} rehypePlugins={REHYPE_PLUGINS} components={components}>
        {source}
      </ReactMarkdown>
    </div>
  )
}

export default MarkdownMathKatex
