import {
  SandpackCodeEditor,
  SandpackFileExplorer,
  SandpackPreview,
  SandpackProvider,
  useSandpack,
} from '@codesandbox/sandpack-react'
import clsx from 'clsx'
import { Save, Wrench } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { Files } from '../lib/api'
import { dependenciesFor } from '../lib/agents'

const RESERVED = new Set(['/index.js', '/public/index.html', '/package.json'])

const INDEX_HTML = `<!DOCTYPE html>
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

interface Props {
  files: Files
  versionKey: string
  tab: 'preview' | 'code'
  canFix: boolean
  onSave: (files: Files) => void
  onDirtyChange: (dirty: boolean) => void
  onFixError: (error: string) => void
  saveRequest: number
}

export default function PreviewPanel(props: Props) {
  const { files, versionKey } = props
  const sandpackFiles = useMemo(() => {
    const out: Record<string, { code: string; active?: boolean; hidden?: boolean }> = {}
    for (const [path, code] of Object.entries(files)) out[path] = { code }
    if (!out['/styles.css']) out['/styles.css'] = { code: '/* 自定义样式 */\n' }
    out['/public/index.html'] = { code: INDEX_HTML, hidden: true }
    if (out['/App.js']) out['/App.js'].active = true
    return out
  }, [files])
  const dependencies = useMemo(() => dependenciesFor(files), [files])

  return (
    <SandpackProvider
      key={versionKey}
      template="react"
      files={sandpackFiles}
      customSetup={{ dependencies }}
      options={{
        recompileMode: 'delayed',
        recompileDelay: 600,
      }}
      className="h-full"
    >
      <Panels {...props} />
    </SandpackProvider>
  )
}

function Panels({ files, tab, canFix, onSave, onDirtyChange, onFixError, saveRequest }: Props) {
  const { sandpack } = useSandpack()
  const [initial] = useState<Record<string, string>>(() =>
    Object.fromEntries(Object.entries(sandpack.files).map(([p, f]) => [p, f.code])),
  )

  const changed = useMemo(() => {
    const out: Files = {}
    for (const [path, f] of Object.entries(sandpack.files)) {
      if (RESERVED.has(path)) continue
      if (initial[path] !== f.code) out[path] = f.code
    }
    return out
  }, [sandpack.files, initial])
  const dirty = Object.keys(changed).length > 0

  useEffect(() => onDirtyChange(dirty), [dirty, onDirtyChange])

  const lastSave = useRef(saveRequest)
  useEffect(() => {
    if (saveRequest === lastSave.current) return
    lastSave.current = saveRequest
    if (dirty) onSave({ ...files, ...changed })
  }, [saveRequest, dirty, files, changed, onSave])

  const error = sandpack.error?.message

  return (
    <div className="relative h-full">
      <div className={clsx('h-full', tab !== 'preview' && 'hidden')}>
        <SandpackPreview
          className="h-full"
          showOpenInCodeSandbox={false}
          showRefreshButton
          style={{ height: '100%' }}
        />
      </div>
      <div className={clsx('flex h-full', tab !== 'code' && 'hidden')}>
        <div className="w-44 shrink-0 overflow-y-auto border-r border-zinc-200 bg-white xl:w-56">
          <SandpackFileExplorer autoHiddenFiles style={{ height: '100%' }} />
        </div>
        <div className="min-w-0 flex-1">
          <SandpackCodeEditor showTabs={false} showLineNumbers style={{ height: '100%' }} />
        </div>
      </div>
      {error && canFix && (
        <div className="absolute right-4 bottom-4 left-4 flex items-center justify-between gap-3 rounded-xl border border-red-200 bg-white/95 px-4 py-3 shadow-lg backdrop-blur">
          <p className="line-clamp-2 font-mono text-xs text-red-700">{error}</p>
          <button
            onClick={() => onFixError(error)}
            className="flex shrink-0 items-center gap-1.5 rounded-lg bg-red-600 px-3 py-1.5 text-sm text-white hover:bg-red-700"
          >
            <Wrench className="size-3.5" /> 让 Alex 修复
          </button>
        </div>
      )}
      {dirty && tab === 'code' && (
        <div className="pointer-events-none absolute top-2 right-3 flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800">
          <Save className="size-3" /> 有未保存的修改
        </div>
      )}
    </div>
  )
}
