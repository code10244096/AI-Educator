// 数学公式文本预处理（纯函数，不依赖 KaTeX，便于单独测试）
//
// 模型输出里常见的写法：
//   \( ... \)  \[ ... \]  $ ... $  $$ ... $$  以及不带定界符的裸 LaTeX（如 \displaystyle =\frac{a}{b}>0）
//   JSON 双重转义留下的字面量 \n（两个字符）、\\frac、\\( 等
// splitMath 把文本切成 [{type:'text', text}] / [{type:'math', tex, display, raw}]，
// 交给 MathText 组件逐段渲染；渲染失败的段落按 raw 原文显示。

// 以 n 开头的 LaTeX 命令：遇到 “\n” 后面紧跟这些单词时不当作换行
const LATEX_N_COMMANDS = new Set([
  'ne', 'neq', 'neg', 'nabla', 'natural', 'nearrow', 'nexists', 'ni', 'nmid', 'not', 'notin', 'nu',
  'nwarrow', 'newline', 'ngeq', 'nleq', 'ngeqslant', 'nleqslant', 'ngtr', 'nless', 'nparallel',
  'nsubseteq', 'nsupseteq', 'nRightarrow', 'nLeftarrow', 'nLeftrightarrow', 'nleftarrow',
  'nleftrightarrow', 'nrightarrow', 'ncong', 'nsim', 'nprec', 'nsucc', 'nvdash', 'nolimits',
  'normalsize', 'nonumber', 'notag', 'newcommand',
])

const isLetter = (c) => (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')

/** 统一换行：CRLF、字面量 \n；双重转义的 \\( \\) \\[ \\] 还原为单个反斜杠 */
export function normalizeMathText(input) {
  if (input === null || input === undefined) return ''
  const s = String(input).replace(/\r\n?/g, '\n').replace(/\\\\([()[\]])/g, '\\$1')
  let out = ''
  let i = 0
  while (i < s.length) {
    if (s[i] !== '\\') {
      out += s[i]
      i += 1
      continue
    }
    let j = i
    while (j < s.length && s[j] === '\\') j += 1
    const run = j - i
    // 奇数个反斜杠 + n：最后一个反斜杠转义了 n
    if (run % 2 === 1 && s[j] === 'n') {
      let k = j + 1
      while (k < s.length && isLetter(s[k])) k += 1
      const word = s.slice(j, k)
      if (!LATEX_N_COMMANDS.has(word)) {
        out += s.slice(i, j - 1) + '\n'
        i = j + 1
        continue
      }
    }
    out += s.slice(i, j)
    i = j
  }
  return out
}

// 裸 LaTeX 片段：连续的 ASCII 数学字符（中文与全角标点会打断）
const BARE_RUN_RE = /[A-Za-z0-9\\{}^_=<>+\-*/|().,;:'![\] ≤≥≠±×÷·∞°∈∉⊆⊂∪∩→⇒⇔αβγθπλμσφω√∠△⊥∥]+/g
const HAS_COMMAND_RE = /\\[A-Za-z]+/
const HAS_SCRIPT_RE = /[A-Za-z0-9)}\]]\s*[\^_]\s*[{A-Za-z0-9(\\+-]/
const EDGE_PUNCT_LEAD_RE = /^[\s,.;:!]+/
const EDGE_PUNCT_TRAIL_RE = /[\s,.;:!]+$/

function pushText(tokens, text) {
  if (!text) return
  const last = tokens[tokens.length - 1]
  if (last && last.type === 'text') last.text += text
  else tokens.push({ type: 'text', text })
}

/** 在普通文本里找出裸 LaTeX（含 \命令 或 x^2 / x_1 这类上下标）并标记为行内公式 */
function splitBareLatex(text, tokens) {
  let last = 0
  BARE_RUN_RE.lastIndex = 0
  let m
  while ((m = BARE_RUN_RE.exec(text)) !== null) {
    const run = m[0]
    if (!HAS_COMMAND_RE.test(run) && !HAS_SCRIPT_RE.test(run)) continue
    const lead = run.match(EDGE_PUNCT_LEAD_RE)?.[0].length || 0
    const trail = run.slice(lead).match(EDGE_PUNCT_TRAIL_RE)?.[0].length || 0
    const tex = run.slice(lead, run.length - trail)
    if (!tex) continue
    const start = m.index + lead
    pushText(tokens, text.slice(last, start))
    tokens.push({ type: 'math', tex, display: false, raw: tex, bare: true })
    last = start + tex.length
  }
  pushText(tokens, text.slice(last))
}

/** 把文本切成文字段与公式段 */
export function splitMath(input) {
  const s = normalizeMathText(input)
  const tokens = []
  let buf = ''
  const flush = () => {
    if (buf) splitBareLatex(buf, tokens)
    buf = ''
  }
  const pushMath = (tex, display, raw) => {
    flush()
    if (tex.trim()) tokens.push({ type: 'math', tex, display, raw })
  }

  let i = 0
  while (i < s.length) {
    const c = s[i]
    const next = s[i + 1]
    if (c === '\\' && next === '\\') {
      buf += '\\\\'
      i += 2
      continue
    }
    if (c === '\\' && (next === '(' || next === '[')) {
      const close = next === '(' ? '\\)' : '\\]'
      const end = s.indexOf(close, i + 2)
      if (end !== -1) {
        pushMath(s.slice(i + 2, end), next === '[', s.slice(i, end + 2))
        i = end + 2
        continue
      }
    }
    if (c === '\\' && next === '$') {
      buf += '$'
      i += 2
      continue
    }
    if (c === '$') {
      if (next === '$') {
        const end = s.indexOf('$$', i + 2)
        if (end !== -1) {
          pushMath(s.slice(i + 2, end), true, s.slice(i, end + 2))
          i = end + 2
          continue
        }
      } else {
        let end = i + 1
        while (end < s.length && !(s[end] === '$' && s[end - 1] !== '\\')) end += 1
        const body = s.slice(i + 1, end)
        if (end < s.length && body.trim() && !body.includes('\n\n')) {
          pushMath(body, false, s.slice(i, end + 1))
          i = end + 1
          continue
        }
      }
    }
    buf += c
    i += 1
  }
  flush()
  return tokens
}

/** 公式段送进 KaTeX 前的清理：双重转义的命令 \\frac → \frac */
export function cleanTex(tex) {
  return String(tex).replace(/\\\\(?=[A-Za-z])/g, '\\').trim()
}

/** Markdown 文档（教案等）：\( \) → $ $，\[ \] → $$ $$，交给 remark-math 处理 */
export function toMarkdownMath(input) {
  const s = normalizeMathText(input)
  return s
    .replace(/\\\[([\s\S]+?)\\\]/g, (_, tex) => `\n$$\n${tex.trim()}\n$$\n`)
    .replace(/\\\(([\s\S]+?)\\\)/g, (_, tex) => `$${tex.trim()}$`)
}
