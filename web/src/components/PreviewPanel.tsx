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
import { RESERVED, toSandpack } from '../lib/sandpack'

export type Device = 'desktop' | 'mobile'

interface Props {
  files: Files
  versionKey: string
  tab: 'preview' | 'code'
  device: Device
  canFix: boolean
  onSave: (files: Files) => void
  onDirtyChange: (dirty: boolean) => void
  onFixError: (error: string) => void
  saveRequest: number
}

export default function PreviewPanel(props: Props) {
  const { files, versionKey } = props
  const sandpack = useMemo(() => toSandpack(files), [files])

  return (
    <SandpackProvider
      key={versionKey}
      template="react"
      files={sandpack.files}
      customSetup={{ dependencies: sandpack.dependencies }}
      options={{
        recompileMode: 'delayed',
        recompileDelay: 600,
        externalResources: sandpack.externalResources,
      }}
      className="h-full"
    >
      <Panels {...props} />
    </SandpackProvider>
  )
}

function Panels({
  files,
  tab,
  device,
  canFix,
  onSave,
  onDirtyChange,
  onFixError,
  saveRequest,
}: Props) {
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
      <div
        className={clsx(
          'h-full',
          tab !== 'preview' && 'hidden',
          device === 'mobile' && 'sm:flex sm:justify-center sm:overflow-auto sm:bg-zinc-100 sm:p-4',
        )}
      >
        <div
          className={clsx(
            'h-full',
            device === 'mobile' &&
              'sm:w-[390px] sm:max-w-full sm:shrink-0 sm:overflow-hidden sm:rounded-[28px] sm:border-[6px] sm:border-zinc-800 sm:bg-white sm:shadow-xl',
          )}
        >
          <SandpackPreview
            className="h-full"
            showOpenInCodeSandbox={false}
            showRefreshButton
            style={{ height: '100%' }}
          />
        </div>
      </div>
      <div className={clsx('flex h-full', tab !== 'code' && 'hidden')}>
        <div className="hidden w-44 shrink-0 overflow-y-auto border-r border-zinc-200 bg-white sm:block xl:w-56">
          <SandpackFileExplorer autoHiddenFiles style={{ height: '100%' }} />
        </div>
        <div className="min-w-0 flex-1">
          <SandpackCodeEditor showTabs showLineNumbers style={{ height: '100%' }} />
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
