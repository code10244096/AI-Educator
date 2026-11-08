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

// 历史数据里的占位哨兵文案（后端已改为写空串，这里兼容旧数据）：空或哨兵视为空白
const SENTINEL_TEXTS = new Set(['未提供', '未知', '未作答'])
export const isBlankText = (v) => {
  if (v === null || v === undefined) return true
  const s = String(v).trim()
  return !s || SENTINEL_TEXTS.has(s)
}
/** 空白（含哨兵）显示为「—」，否则返回原文 */
export const orDash = (v) => (isBlankText(v) ? '—' : v)

// 数据源（Word/LaTeX 转换、HTML 导出）常混入的结构标签与 HTML 实体。
// 只处理白名单内的结构标签，避免误吃数学比较式里的 a<b。
const STRUCT_TAGS_RE = /<\/?(?:p|div|br|hr|li|ul|ol|span|strong|em|b|i|u)(?:\s[^>]*)?>/gi
const HTML_ENTITIES = [
  [/(&#0*39|&apos);/g, "'"],
  [/&quot;/g, '"'],
  [/&#0*34;/g, '"'],
  [/&lt;/g, '<'],
  [/&gt;/g, '>'],
  [/&#0*60;/g, '<'],
  [/&#0*62;/g, '>'],
  [/&#0*160;|&nbsp;/g, ' '],
  [/&amp;/g, '&'], // 放最后：&amp;lt; 只解码一层，避免双重解码
]

/** 结构标签 → 换行；HTML 实体 → 字符（React 文本节点会重新转义，安全） */
function stripHtmlNoise(s) {
  let out = s.replace(STRUCT_TAGS_RE, '\n')
  for (const [re, ch] of HTML_ENTITIES) out = out.replace(re, ch)
  return out
}

/** 统一换行：CRLF、字面量 \n；双重转义的 \\( \\) \\[ \\] 还原为单个反斜杠 */
export function normalizeMathText(input) {
  if (input === null || input === undefined) return ''
  const s = stripHtmlNoise(String(input)).replace(/\r\n?/g, '\n').replace(/\\\\([()[\]])/g, '\\$1')
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
const BARE_RUN_RE = /[A-Za-z0-9\\{}^_=<>+\-*/|().,;:'![\]~ ≤≥≠±×÷·∞°∈∉⊆⊂∪∩→⇒⇔αβγθπλμσφω√∠△⊥∥]+/g
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
// 换行后出现选项标号（A. / 1、之类）——源数据丢闭合 $$ 的征兆，公式配对应放弃
const OPTION_LINE_RE = /\n[ \t]*(?:[A-DＡ-Ｄ]|\d{1,2})\s*[.、．:：]/
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
          const body = s.slice(i + 2, end)
          // 源数据丢闭合 $$ 时，公式体会一口吞掉换行后的选项；识别选项行就放弃本次配对
          if (!OPTION_LINE_RE.test(body)) {
            pushMath(body, true, s.slice(i, end + 2))
            i = end + 2
            continue
          }
        }
      } else {
        let end = i + 1
        while (end < s.length && !(s[end] === '$' && s[end - 1] !== '\\')) end += 1
        const body = s.slice(i + 1, end)
        if (end < s.length && body.trim() && !body.includes('\n\n') && !OPTION_LINE_RE.test(body)) {
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

/** TAL-SCQ5K 等源数据的分裂分式：\frac{分子},{分母}（分子组后直接跟半角逗号）
 * 归一化为 \frac{分子}{分母}。用花括号平衡匹配定位分子组，避免误伤
 * \left({\frac{\pi}{3}},{\frac{5\pi}{6}}\right) 这类坐标/区间里的合法逗号。
 * 兼容 \dfrac \tfrac \cfrac。
 */
export function fixSplitFractions(tex) {
  const s = String(tex)
  const FRAC_RE = /\\[dtc]?frac/g
  let out = ''
  let i = 0
  while (i < s.length) {
    FRAC_RE.lastIndex = i
    const m = FRAC_RE.exec(s)
    if (!m) {
      out += s.slice(i)
      break
    }
    out += s.slice(i, m.index)
    let j = m.index + m[0].length
    while (j < s.length && (s[j] === ' ' || s[j] === '\t')) j += 1
    let k = -1
    if (s[j] === '{') {
      let depth = 0
      k = j
      while (k < s.length) {
        if (s[k] === '{') depth += 1
        else if (s[k] === '}') {
          depth -= 1
          if (depth === 0) break
        }
        k += 1
      }
    }
    // k = 分子组闭合 } 的下标；其后紧跟 ",{" 即为分裂分式，吃掉这个逗号
    if (k !== -1 && k < s.length && s[k + 1] === ',' && s[k + 2] === '{') {
      out += s.slice(m.index, k + 1)
      i = k + 2 // 跳过 ','，后面的 {分母} 由正常流程拷贝
      continue
    }
    out += s.slice(m.index, j)
    i = j
  }
  return out
}

/** 公式段送进 KaTeX 前的清理：
 * - 双重转义的命令 \\frac → \frac
 * - 转换工具残留的文本模式命令 \textless \textbar 等 → 数学模式符号（KaTeX 不认这些）
 * - 源数据里 \frac{分子},{分母} 的分裂分式 → \frac{分子}{分母}
 */
const TEXT_COMMAND_MAP = [
  [/\\textasciitilde/g, '\\sim'],
  [/\\textless/g, '<'],
  [/\\textgreater/g, '>'],
  [/\\textbar/g, '|'],
  [/\\textbackslash/g, '\\backslash'],
  [/\\textquotesingle/g, "'"],
  [/\\textquotedbl/g, '"'],
]
const ENV_NAMES = 'cases|array|aligned|align|gather|gathered|matrix|pmatrix|bmatrix|vmatrix|Vmatrix|subarray'
const ENV_RE = new RegExp(`\\\\begin\\{(${ENV_NAMES})\\}`, 'g')
const ENV_END_RE = new RegExp(`\\\\end\\{(${ENV_NAMES})\\}`, 'g')

export function cleanTex(tex) {
  let out = String(tex).replace(/\\\\(?=[A-Za-z])/g, '\\').trim()
  for (const [re, ch] of TEXT_COMMAND_MAP) out = out.replace(re, ch)
  // 转换工具残留的结构修复：
  // 1) 环境结束符前多余的换行 \\（cases/array 最后一行不许换行）
  out = out.replace(new RegExp(`(\\\\[\\\\\\s]*)(\\\\end\\{(?:${ENV_NAMES})\\})`, 'g'), '$2')
  // 2) ulem 的下划线 \uline → \underline
  out = out.replace(/\\uline(?=\s*\{)/g, '\\underline')
  // 3) \left { / \right } → \left\{ / \right\}（花括号是定界符时必须转义）
  out = out.replace(/\\left\s*\{/g, '\\left\\{').replace(/\\right\s*\}/g, '\\right\\}')
  // 4) align 只能 display 模式；行内段降级为 aligned
  out = out
    .replace(/\\begin\{align\}/g, '\\begin{aligned}')
    .replace(/\\end\{align\}/g, '\\end{aligned}')
  // 5) \begin{array},{l} → \begin{array}{l}
  out = out.replace(/\\begin\{array\}\s*,\s*(?=\{)/g, '\\begin{array}')
  // 6) 纯排版命令
  out = out.replace(/\\(?:hfill|break|allowbreak|noindent)\b/g, ' ')
  // 7) 全角标点变体 → 半角
  out = out.replace(/︰/g, ':').replace(/，/g, ',')
  // 8) 源数据分裂分式 \frac{a},{b} → \frac{a}{b}（放最后：前面步骤可能改动标点；KaTeX 渲染层兜底，数据层另有清洗）
  out = fixSplitFractions(out)
  return out
}

/** Markdown 文档（教案等）：\( \) → $ $，\[ \] → $$ $$，公式体过 cleanTex，交给 remark-math 处理 */
export function toMarkdownMath(input) {
  const s = normalizeMathText(input)
  return s
    .replace(/\\\[([\s\S]+?)\\\]/g, (_, tex) => `\n$$\n${cleanTex(tex)}\n$$\n`)
    .replace(/\\\(([\s\S]+?)\\\)/g, (_, tex) => `$${cleanTex(tex)}$`)
    .replace(/\$\$([\s\S]+?)\$\$/g, (_, tex) => `\n$$\n${cleanTex(tex)}\n$$\n`)
    .replace(/\$([^$\n]+?)\$/g, (_, tex) => `$${cleanTex(tex)}$`)
}
