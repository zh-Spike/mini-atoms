import { dependenciesFor } from './agents'
import type { Files } from './api'

/** Files the runtime provides; the AI never writes them and they are excluded from saves. */
export const RESERVED = new Set(['/index.js', '/public/index.html', '/package.json'])

export const INDEX_HTML = `<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <script src="https://cdn.tailwindcss.com"></script>
    <script>tailwind.config = { darkMode: 'class' }</script>
  </head>
  <body>
    <div id="root"></div>
  </body>
</html>
`

export type SandpackFiles = Record<string, { code: string; active?: boolean; hidden?: boolean }>

export function toSandpack(files: Files): { files: SandpackFiles; dependencies: Files } {
  const out: SandpackFiles = {}
  for (const [path, code] of Object.entries(files)) out[path] = { code }
  if (!out['/styles.css']) out['/styles.css'] = { code: '/* 自定义样式 */\n' }
  out['/public/index.html'] = { code: INDEX_HTML, hidden: true }
  if (out['/App.js']) out['/App.js'].active = true
  return { files: out, dependencies: dependenciesFor(files) }
}
