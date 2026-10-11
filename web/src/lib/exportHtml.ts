import { dependenciesFor } from './agents'
import type { Files } from './api'
import { slugify, triggerDownload } from './download'
import { DARK_VARIANT, RESERVED, SELF_HOSTED_TAILWIND } from './sandpack'

const REACT = '18.3.1'
const ESM = 'https://esm.sh'
const RESOLVE_SUFFIXES = ['', '.js', '.jsx', '/index.js', '/index.jsx']
const SPECIFIER_RE = /(\bfrom\s*|\bimport\s*\(\s*|\bimport\s+)(['"])([^'"]+)\2/g
const MODULE_PREFIX = '@app'

function resolve(importer: string, spec: string, files: Files): string | null {
  const parts = importer.split('/').slice(0, -1)
  for (const seg of spec.split('/')) {
    if (seg === '..') parts.pop()
    else if (seg !== '.') parts.push(seg)
  }
  const base = parts.join('/') || '/'
  const hit = RESOLVE_SUFFIXES.map((s) => base + s).find((p) => p in files)
  return hit ?? null
}

function importMap(files: Files): Record<string, string> {
  const external = '?external=react,react-dom'
  const map: Record<string, string> = {
    react: `${ESM}/react@${REACT}`,
    'react/jsx-runtime': `${ESM}/react@${REACT}/jsx-runtime`,
    'react-dom': `${ESM}/react-dom@${REACT}${external}`,
    'react-dom/client': `${ESM}/react-dom@${REACT}/client${external}`,
  }
  for (const [name, range] of Object.entries(dependenciesFor(files))) {
    const version = range.replace(/^[\^~]/, '')
    map[name] = `${ESM}/${name}@${version}${external}`
    map[`${name}/`] = `${ESM}/${name}@${version}/`
  }
  return map
}

const toDataUrl = (code: string) => `data:text/javascript;charset=utf-8,${encodeURIComponent(code)}`
const inlineScript = (code: string) => code.replace(/<\/script/gi, '<\\/script')

/**
 * Builds one HTML file that runs the app without a build step: each source file is compiled with
 * sucrase and becomes a data-URL module, wired together (and to esm.sh packages) by an import map.
 * The Tailwind runtime is inlined, so only the npm packages need the network.
 */
export async function buildStandaloneHtml(title: string, files: Files): Promise<string> {
  const [{ transform }, tailwind] = await Promise.all([
    import('sucrase'),
    fetch(SELF_HOSTED_TAILWIND).then((r) => r.text()),
  ])
  const imports = importMap(files)
  const styles: string[] = []

  for (const [path, code] of Object.entries(files)) {
    if (RESERVED.has(path)) continue
    if (path.endsWith('.css')) {
      styles.push(code)
      continue
    }
    if (!/\.(jsx?|mjs)$/.test(path)) continue
    const compiled = transform(code, {
      transforms: ['jsx'],
      jsxRuntime: 'automatic',
      production: true,
      filePath: path,
    }).code
    const linked = compiled.replace(SPECIFIER_RE, (whole, lead: string, q: string, spec: string) => {
      if (!spec.startsWith('.') && !spec.startsWith('/')) return whole
      if (spec.endsWith('.css')) return `${lead}${q}data:text/javascript,${q}`
      const target = resolve(path, spec, files)
      return target ? `${lead}${q}${MODULE_PREFIX}${target}${q}` : whole
    })
    imports[`${MODULE_PREFIX}${path}`] = toDataUrl(linked)
  }

  const entry = `import { createElement } from "react";
import { createRoot } from "react-dom/client";
import App from "${MODULE_PREFIX}/App.js";
createRoot(document.getElementById("root")).render(createElement(App));`

  return `<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>${title.replace(/</g, '&lt;')}</title>
    <script>${inlineScript(tailwind)}</script>
    <style type="text/tailwindcss">
      ${DARK_VARIANT}
    </style>
    <style>
${styles.join('\n')}
    </style>
    <script type="importmap">${inlineScript(JSON.stringify({ imports }))}</script>
  </head>
  <body>
    <div id="root"></div>
    <script>
      window.addEventListener('error', (e) => {
        const box = document.createElement('pre')
        box.style.cssText = 'margin:16px;padding:12px;color:#b91c1c;background:#fef2f2;white-space:pre-wrap'
        box.textContent = '应用运行出错：' + (e.message || e) + '\\n（依赖从 esm.sh 加载，需要联网）'
        document.body.appendChild(box)
      })
    </script>
    <script type="module">${inlineScript(entry)}</script>
  </body>
</html>
`
}

/** Exports a version as a single HTML file that opens directly in a browser. */
export async function downloadProjectHtml(title: string, files: Files) {
  const html = await buildStandaloneHtml(title, files)
  triggerDownload(new Blob([html], { type: 'text/html' }), `${slugify(title)}.html`)
}
