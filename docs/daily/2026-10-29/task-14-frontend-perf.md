# task-14：前端首屏/功能页加载优化（跨境带宽背景）

## 背景与诊断结论（已实测，勿重复排查）

- 服务器在新加坡，国内访问 **RTT ≈ 490ms**、晚高峰实测吞吐 **~10KB/s**；服务器本机回环 ttfb 8ms，后端/容器无性能问题。**瓶颈是跨境带宽，优化目标是减少传输字节数与关键路径请求数。**
- 构建产物现状（frontend/dist，Oct 27 构建）：
  - `index-wYMWcN8L.js` 291KB：首屏入口（React/react-dom/router/contexts/Navbar/Sidebar/Workbench），已 gzip（~95KB），服务端 gzip 已开。
  - `index-DUJ10AqV.js` 132KB：react-markdown + remark-math + rehype-katex 体系。
  - `katex-C5jXJg4s.js` 261KB：被 DUJ chunk **静态引用**。
  - `html2pdf-COurf3V_.js` **983KB**：`src/pages/LessonPlanGenerator.jsx:19` **静态 import**，打开教案页即拉 1MB。
- App.jsx 已对 11 个页面做路由级 lazy；`MathText.jsx` 已动态 import katex（好）；`ClassData.jsx`/`TaskDetail.jsx` 已动态 import html2pdf（好）。

## 需求

1. **html2pdf 改动态引入**：`LessonPlanGenerator.jsx` 参照 `ClassData.jsx:580` 的写法，`import html2pdf from 'html2pdf.js'` 改为导出函数内 `await import('html2pdf.js')`。验收：构建产物中 html2pdf chunk 不再被 LessonPlanGenerator chunk 静态依赖（构建日志可看出 chunk 拆分变化）。

2. **数学渲染栈按需加载**：`src/components/MarkdownMath.jsx` 当前静态 import `rehype-katex` 和 `katex.min.css`。改造为**首次真正渲染数学内容时才加载**（React.lazy + Suspense 包裹内部实现，fallback 渲染纯文本/Markdown 原文），不得改变渲染结果。这样打开教案/题库等含公式的页面时，先出页面框架，公式栈随后补入。

3. **vendor 分包稳定缓存**：`vite.config.js` 增加 `build.rollupOptions.output.manualChunks`，把 `react`、`react-dom`、`react-router-dom`（含其内部依赖 scheduler 等）单独打包为 `vendor-react` chunk。目的：后端迭代时该 chunk 哈希不变，老用户浏览器复用缓存，只下载变化的业务代码。

4. **不要**改路由结构、不要改任何业务逻辑/API 调用、不要引入新依赖。CSS 处理保持现状（katex css 随动态 import 走）。

## 验收方式（我执行）

- `npm run build` 成功；比对优化前后各 chunk 大小与静态依赖图（html2pdf/katex 不得出现在非动态路径）。
- 生产部署后 curl 实测：教案页相关资源 gzip 后总下载量从 ~1.4MB 降到目标 <400KB。
- 全量 pytest 回归（不应有后端改动）。

## 最终回复格式

- 改动文件清单 + 每处改动说明
- 构建产物前后对比表（chunk 名、优化前大小、优化后大小、加载时机变化）
- 你判断的风险点
