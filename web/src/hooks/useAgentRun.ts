import { useCallback, useLayoutEffect, useRef, useState } from 'react'
import { sendMessage, type AgentId, type Files, type Message, type Version } from '../lib/api'

const THINKING_TAIL = 240

export interface LiveTurn {
  agent: AgentId
  text: string
  thinking: string
  files: { path: string; done: boolean }[]
}

export interface RunState {
  live: LiveTurn | null
  liveFiles: Files
  currentFile: string | null
  completed: AgentId[]
}

interface Handlers {
  onMessage: (m: Message) => void
  onVersion: (v: Version, messageId: string) => void
  onError: (text: string) => void
  onFinish: () => void
}

const emptyRun = (): RunState => ({ live: null, liveFiles: {}, currentFile: null, completed: [] })

/**
 * Drives one streamed agent run. File deltas arrive by the thousand, so state lives in a ref
 * and React re-renders at most once per animation frame.
 */
export function useAgentRun(projectId: string, handlers: Handlers) {
  const stateRef = useRef<RunState>(emptyRun())
  const [state, setState] = useState<RunState | null>(null)
  const frame = useRef(0)
  const abortRef = useRef<AbortController | null>(null)
  const handlersRef = useRef(handlers)
  useLayoutEffect(() => {
    handlersRef.current = handlers
  })

  const flush = useCallback(() => {
    if (frame.current) return
    frame.current = requestAnimationFrame(() => {
      frame.current = 0
      const s = stateRef.current
      setState({ ...s, liveFiles: { ...s.liveFiles } })
    })
  }, [])

  const start = useCallback(
    async (content: string) => {
      if (abortRef.current) return
      const ctrl = new AbortController()
      abortRef.current = ctrl
      stateRef.current = emptyRun()
      setState(stateRef.current)
      const h = handlersRef.current
      const s = stateRef.current
      try {
        for await (const ev of sendMessage(projectId, content, ctrl.signal)) {
          switch (ev.type) {
            case 'user_message':
              h.onMessage(ev.message)
              break
            case 'agent_start':
              s.live = { agent: ev.agent, text: '', thinking: '', files: [] }
              break
            case 'delta':
              if (s.live) s.live.text += ev.text
              break
            case 'thinking':
              if (s.live) s.live.thinking = (s.live.thinking + ev.text).slice(-THINKING_TAIL)
              break
            case 'file_start':
              s.live?.files.push({ path: ev.path, done: false })
              s.liveFiles[ev.path] = ''
              s.currentFile = ev.path
              break
            case 'file_delta':
              s.liveFiles[ev.path] = (s.liveFiles[ev.path] ?? '') + ev.text
              break
            case 'file_end': {
              s.liveFiles[ev.path] = ev.content
              const f = s.live?.files.find((x) => x.path === ev.path)
              if (f) f.done = true
              break
            }
            case 'agent_end':
              h.onMessage(ev.message)
              if (!s.completed.includes(ev.agent)) s.completed.push(ev.agent)
              s.live = null
              break
            case 'version':
              h.onVersion(ev.version, ev.message_id)
              break
            case 'error':
              if (ev.saved) h.onMessage(ev.saved)
              else h.onError(ev.message)
              break
            case 'done':
              break
          }
          flush()
        }
      } catch (err) {
        if (!ctrl.signal.aborted) h.onError(err instanceof Error ? err.message : String(err))
      } finally {
        abortRef.current = null
        cancelAnimationFrame(frame.current)
        frame.current = 0
        setState(null)
        h.onFinish()
      }
    },
    [projectId, flush],
  )

  const stop = useCallback(() => abortRef.current?.abort(), [])

  return { run: state, start, stop }
}
