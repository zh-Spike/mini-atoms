import { useCallback, useLayoutEffect, useRef, useState } from 'react'
import {
  sendMessage,
  type AgentId,
  type Files,
  type Message,
  type RunEvent,
  type RunStats,
  type Version,
} from '../lib/api'

const THINKING_TAIL = 240

export interface LiveTurn {
  agent: AgentId
  text: string
  thinking: string
  files: { path: string; done: boolean }[]
}

/** One parallel Alex + QA lane of a race run. */
export interface LaneState {
  label: string
  agent: AgentId | null
  files: Files
  doneFiles: string[]
  currentFile: string | null
  qaOk: boolean | null
  error: string | null
  finished: boolean
}

export interface RunState {
  live: LiveTurn | null
  liveFiles: Files
  currentFile: string | null
  completed: AgentId[]
  race: LaneState[] | null
}

interface Handlers {
  onMessage: (m: Message) => void
  onVersion: (v: Version, messageId: string) => void
  onLaneDone: (lane: number, label: string, v: Version, m: Message) => void
  onNotice: (text: string) => void
  onError: (text: string) => void
  onFinish: (stats: RunStats | null) => void
}

const emptyRun = (): RunState => ({
  live: null,
  liveFiles: {},
  currentFile: null,
  completed: [],
  race: null,
})

const newLane = (label: string): LaneState => ({
  label,
  agent: null,
  files: {},
  doneFiles: [],
  currentFile: null,
  qaOk: null,
  error: null,
  finished: false,
})

function applyLaneEvent(lane: LaneState, ev: RunEvent) {
  switch (ev.type) {
    case 'agent_start':
      lane.agent = ev.agent
      break
    case 'file_start':
      lane.files[ev.path] = ''
      lane.currentFile = ev.path
      lane.doneFiles = lane.doneFiles.filter((p) => p !== ev.path)
      break
    case 'file_delta':
      lane.files[ev.path] = (lane.files[ev.path] ?? '') + ev.text
      break
    case 'file_end':
      lane.files[ev.path] = ev.content
      lane.doneFiles.push(ev.path)
      break
    case 'agent_end':
      if (ev.agent === 'qa' && ev.ok !== undefined) lane.qaOk = ev.ok
      break
  }
}

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
      setState({
        ...s,
        liveFiles: { ...s.liveFiles },
        race: s.race?.map((l) => ({ ...l, files: { ...l.files } })) ?? null,
      })
    })
  }, [])

  const start = useCallback(
    async (content: string, race = false) => {
      if (abortRef.current) return
      const ctrl = new AbortController()
      abortRef.current = ctrl
      stateRef.current = emptyRun()
      setState(stateRef.current)
      const h = handlersRef.current
      const s = stateRef.current
      let stats: RunStats | null = null
      try {
        for await (const ev of sendMessage(projectId, content, race, ctrl.signal)) {
          if ('lane' in ev && ev.lane !== undefined && s.race) {
            const lane = s.race[ev.lane]
            if (ev.type === 'lane_done') {
              lane.finished = true
              lane.agent = null
              h.onLaneDone(ev.lane, lane.label, ev.version, ev.message)
            } else if (ev.type === 'lane_finished') {
              lane.finished = true
              lane.agent = null
              lane.qaOk = ev.ok
            } else if (ev.type === 'lane_error') {
              lane.finished = true
              lane.agent = null
              lane.error = ev.message
            } else {
              applyLaneEvent(lane, ev)
            }
            flush()
            continue
          }
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
              if (ev.message) h.onMessage(ev.message)
              if (!s.completed.includes(ev.agent)) s.completed.push(ev.agent)
              s.live = null
              break
            case 'race_start':
              s.race = ev.lanes.map(newLane)
              s.live = null
              break
            case 'race_done':
              s.race?.forEach((l) => (l.finished = true))
              break
            case 'version':
              h.onVersion(ev.version, ev.message_id)
              break
            case 'notice':
              h.onNotice(ev.text)
              break
            case 'error':
              if (ev.saved) h.onMessage(ev.saved)
              else h.onError(ev.message)
              break
            case 'done':
              stats = ev.stats ?? null
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
        h.onFinish(stats)
      }
    },
    [projectId, flush],
  )

  const stop = useCallback(() => abortRef.current?.abort(), [])

  return { run: state, start, stop }
}
