// Offline harness for frontend unit-level acceptance checks (no browser, no Playwright).
// Loads a module from frontend/src through Vite's SSR loader (uses frontend/vite.config.js, so JSX works),
// then either calls an exported function or renders an exported React component to static HTML.
//
//   node ssr_call.mjs call   <module-from-src-root> <exportName> '<json args array>'
//   node ssr_call.mjs render <module-from-src-root> <exportName|default> '<json props object>'
//
// Prints one line: RESULT:<json>   ({"value": ...} for call, {"html": "...", "errors": [...]} for render)
import path from 'node:path'
import { createRequire } from 'node:module'
import { fileURLToPath, pathToFileURL } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const frontend = path.resolve(here, '../../../../frontend')
// vite lives in frontend/node_modules, not next to this script
const { createServer } = await import(pathToFileURL(path.join(frontend, 'node_modules/vite/dist/node/index.js')).href)
const [mode, mod, exp, raw] = process.argv.slice(2)

const errors = []
const origError = console.error
console.error = (...a) => { errors.push(a.map(String).join(' ')); }

const server = await createServer({
  root: frontend,
  logLevel: 'silent',
  server: { middlewareMode: true, hmr: false },
  appType: 'custom',
  optimizeDeps: { noDiscovery: true },
})
let out
try {
  const m = await server.ssrLoadModule(mod.startsWith('/') ? mod : '/' + mod)
  const target = exp === 'default' ? m.default : m[exp]
  if (!target) throw new Error(`export ${exp} not found in ${mod}; exports: ${Object.keys(m)}`)
  if (mode === 'call') {
    const args = raw ? JSON.parse(raw) : []
    out = { value: await target(...args) }
  } else {
    // same instances Vite externalizes for the SSR-loaded module
    const req = createRequire(path.join(frontend, 'package.json'))
    const React = req('react')
    const { renderToStaticMarkup } = req('react-dom/server')
    const props = raw ? JSON.parse(raw) : {}
    const html = renderToStaticMarkup(React.createElement(target, props))
    out = { html, errors }
  }
} catch (e) {
  out = { error: String(e && e.stack || e), errors }
} finally {
  await server.close()
}
console.error = origError
process.stdout.write('RESULT:' + JSON.stringify(out) + '\n')
