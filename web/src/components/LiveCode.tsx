import clsx from 'clsx'
import { Check, Loader2 } from 'lucide-react'
import { useEffect, useRef } from 'react'
import type { Files } from '../lib/api'

/** Read-only "watch the engineer type" view shown while Alex streams files. */
export default function LiveCode({
  files,
  currentFile,
  doneFiles,
}: {
  files: Files
  currentFile: string | null
  doneFiles: Set<string>
}) {
  const preRef = useRef<HTMLPreElement>(null)
  const code = currentFile ? (files[currentFile] ?? '') : ''

  useEffect(() => {
    const el = preRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [code])

  return (
    <div className="flex h-full bg-zinc-950 text-zinc-100">
      <ul className="w-56 shrink-0 space-y-0.5 overflow-y-auto border-r border-zinc-800 p-2">
        {Object.keys(files).map((path) => (
          <li
            key={path}
            className={clsx(
              'flex items-center gap-2 rounded px-2 py-1 font-mono text-xs',
              path === currentFile ? 'bg-zinc-800 text-white' : 'text-zinc-400',
            )}
          >
            {doneFiles.has(path) ? (
              <Check className="size-3.5 shrink-0 text-emerald-400" />
            ) : (
              <Loader2 className="size-3.5 shrink-0 animate-spin text-sky-400" />
            )}
            <span className="truncate">{path}</span>
          </li>
        ))}
      </ul>
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="border-b border-zinc-800 px-4 py-2 font-mono text-xs text-zinc-400">
          {currentFile ?? '等待中…'}
        </div>
        <pre ref={preRef} className="flex-1 overflow-auto p-4 font-mono text-[13px] leading-relaxed">
          {code}
          <span className="inline-block h-4 w-2 translate-y-0.5 animate-pulse bg-sky-400" />
        </pre>
      </div>
    </div>
  )
}
