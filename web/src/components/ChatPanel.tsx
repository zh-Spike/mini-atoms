import clsx from 'clsx'
import { ArrowUp, Check, FileCode2, Loader2, Square, Timer } from 'lucide-react'
import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import Markdown from 'react-markdown'
import type { LiveTurn } from '../hooks/useAgentRun'
import type { Message, RunStats } from '../lib/api'
import { AGENTS } from '../lib/agents'
import { useModels } from '../lib/models'
import AgentAvatar from './AgentAvatar'
import { RaceModelPicker, RaceToggle } from './RaceControl'

interface Props {
  messages: Message[]
  live: LiveTurn | null
  running: boolean
  versionNumbers: Record<string, number>
  stats: RunStats | null
  onSend: (text: string, raceModels: string[] | null) => void
  onStop: () => void
  onOpenVersion: (versionId: string) => void
}

export default function ChatPanel(props: Props) {
  const { messages, live, running, versionNumbers, stats, onSend, onStop, onOpenVersion } = props
  const [input, setInput] = useState('')
  const [race, setRace] = useState<string[] | null>(null)
  const models = useModels()
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = listRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages.length, live?.text, live?.files.length])

  function send() {
    if (!input.trim() || running) return
    onSend(input.trim(), race)
    setInput('')
    setRace(null)
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div ref={listRef} className="flex-1 space-y-5 overflow-y-auto px-4 py-5">
        {messages.length === 0 && !live && (
          <p className="pt-10 text-center text-sm text-zinc-400">描述你想做的应用，团队会立刻开工</p>
        )}
        {messages.map((m) => (
          <MessageItem
            key={m.id}
            message={m}
            versionNumber={m.version_id ? versionNumbers[m.version_id] : undefined}
            onOpenVersion={onOpenVersion}
          />
        ))}
        {live && <LiveItem live={live} />}
      </div>

      <div className="border-t border-zinc-200 p-3">
        {stats && !running && (
          <p className="mb-2 flex items-center gap-1 text-[11px] text-zinc-400">
            <Timer className="size-3" /> 上一轮用时 {(stats.duration_ms / 1000).toFixed(1)} 秒
            {stats.tokens > 0 && ` · ${stats.tokens.toLocaleString()} tokens`}
          </p>
        )}
        <div className="rounded-xl border border-zinc-300 bg-white p-2 focus-within:border-violet-400">
          {race && models && !running && (
            <RaceModelPicker info={models} value={race} onChange={setRace} />
          )}
          <textarea
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={running ? '团队正在工作…' : '继续提需求，例如：加一个深色模式'}
            className="w-full resize-none px-1 text-sm outline-none"
          />
          <div className="flex items-center justify-between">
            <RaceToggle info={models} value={race} onChange={setRace} disabled={running} />
            {running ? (
              <button
                onClick={onStop}
                className="flex size-8 items-center justify-center rounded-full bg-zinc-800 text-white"
                aria-label="停止"
              >
                <Square className="size-3.5 fill-current" />
              </button>
            ) : (
              <button
                onClick={send}
                disabled={!input.trim()}
                className="flex size-8 items-center justify-center rounded-full bg-violet-600 text-white disabled:opacity-40"
                aria-label="发送"
              >
                <ArrowUp className="size-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function MessageItem({
  message,
  versionNumber,
  onOpenVersion,
}: {
  message: Message
  versionNumber?: number
  onOpenVersion: (id: string) => void
}) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-violet-600 px-3.5 py-2 text-sm whitespace-pre-wrap text-white">
          {message.content}
        </div>
      </div>
    )
  }
  if (message.role === 'system' || !message.agent) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
        {message.content}
      </div>
    )
  }
  const meta = AGENTS[message.agent]
  return (
    <div className="flex gap-2.5">
      <AgentAvatar agent={message.agent} />
      <div className="min-w-0 flex-1">
        <div className="text-xs text-zinc-500">
          <span className="font-medium text-zinc-800">{meta.name}</span> · {meta.role}
        </div>
        <div className="prose prose-sm prose-zinc mt-1 max-w-none rounded-2xl rounded-tl-sm bg-white px-3.5 py-2.5 shadow-sm ring-1 ring-zinc-200 prose-headings:mt-3 prose-headings:mb-1 prose-headings:text-sm prose-p:my-1 prose-ul:my-1 prose-li:my-0">
          <Markdown>{message.content}</Markdown>
        </div>
        {message.version_id && versionNumber !== undefined && (
          <button
            onClick={() => onOpenVersion(message.version_id!)}
            className="mt-1.5 inline-flex items-center gap-1 rounded-full border border-violet-200 bg-violet-50 px-2.5 py-0.5 text-xs text-violet-700 hover:bg-violet-100"
          >
            <FileCode2 className="size-3" /> 查看 v{versionNumber}
          </button>
        )}
      </div>
    </div>
  )
}

function LiveItem({ live }: { live: LiveTurn }) {
  const meta = AGENTS[live.agent]
  return (
    <div className="flex gap-2.5">
      <AgentAvatar agent={live.agent} pulse />
      <div className="min-w-0 flex-1">
        <div className="text-xs text-zinc-500">
          <span className="font-medium text-zinc-800">{meta.name}</span> · {meta.working}
          <span className="animate-pulse">…</span>
        </div>
        {!live.text.trim() && live.files.length === 0 && live.thinking && (
          <div className="mt-1 line-clamp-3 rounded-xl border border-dashed border-zinc-300 px-3 py-2 text-xs leading-relaxed text-zinc-400 italic">
            {live.thinking}
          </div>
        )}
        {(live.text.trim() || live.files.length > 0) && (
          <div className="mt-1 rounded-2xl rounded-tl-sm bg-white px-3.5 py-2.5 shadow-sm ring-1 ring-zinc-200">
            {live.text.trim() && (
              <div className="prose prose-sm prose-zinc max-w-none prose-headings:mt-3 prose-headings:mb-1 prose-headings:text-sm prose-p:my-1 prose-ul:my-1 prose-li:my-0">
                <Markdown>{live.text}</Markdown>
              </div>
            )}
            {live.files.length > 0 && (
              <ul className={clsx('space-y-1', live.text.trim() && 'mt-2')}>
                {live.files.map((f) => (
                  <li key={f.path} className="flex items-center gap-2 font-mono text-xs text-zinc-600">
                    {f.done ? (
                      <Check className="size-3.5 text-emerald-500" />
                    ) : (
                      <Loader2 className="size-3.5 animate-spin text-sky-500" />
                    )}
                    {f.path}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
