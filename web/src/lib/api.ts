export type Files = Record<string, string>

export interface Me {
  guest_id: string
  invite_code: string
  generations_used: number
  generation_limit: number
}

export interface ProjectSummary {
  id: string
  title: string
  created_at: string
  updated_at: string
  version_count: number
}

export interface Message {
  id: string
  role: 'user' | 'agent' | 'system'
  agent: AgentId | null
  content: string
  version_id: string | null
  created_at: string
}

export interface VersionMeta {
  id: string
  number: number
  source: 'ai' | 'manual' | 'restore'
  summary: string
  file_count: number
  created_at: string
}

export interface Version extends VersionMeta {
  files: Files
}

export interface ProjectDetail extends ProjectSummary {
  messages: Message[]
  versions: VersionMeta[]
  latest_version: Version | null
}

export type AgentId = 'mike' | 'emma' | 'bob' | 'alex' | 'qa'

export type RunEvent =
  | { type: 'user_message'; message: Message }
  | { type: 'agent_start'; agent: AgentId }
  | { type: 'delta'; agent: AgentId; text: string }
  | { type: 'thinking'; agent: AgentId; text: string }
  | { type: 'file_start'; agent: AgentId; path: string }
  | { type: 'file_delta'; agent: AgentId; path: string; text: string }
  | { type: 'file_end'; agent: AgentId; path: string; content: string }
  | { type: 'agent_end'; agent: AgentId; message: Message; ok?: boolean; issues?: string[] }
  | { type: 'version'; version: Version; message_id: string }
  | { type: 'error'; message: string; saved?: Message }
  | { type: 'done' }

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(method: string, url: string, body?: unknown): Promise<T> {
  const resp = await fetch(url, {
    method,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: 'same-origin',
  })
  if (!resp.ok) throw await toError(resp)
  return resp.json() as Promise<T>
}

async function toError(resp: Response): Promise<ApiError> {
  let detail = resp.statusText
  try {
    const data = await resp.json()
    if (typeof data.detail === 'string') detail = data.detail
  } catch {
    // non-JSON error body
  }
  return new ApiError(resp.status, detail)
}

export const api = {
  me: () => request<Me>('GET', '/api/auth/me'),
  invite: (code: string) => request<Me>('POST', '/api/auth/invite', { code }),
  logout: () => request<{ ok: boolean }>('POST', '/api/auth/logout'),
  listProjects: () => request<ProjectSummary[]>('GET', '/api/projects'),
  createProject: (prompt: string) => request<ProjectSummary>('POST', '/api/projects', { prompt }),
  getProject: (id: string) => request<ProjectDetail>('GET', `/api/projects/${id}`),
  deleteProject: (id: string) => request<{ ok: boolean }>('DELETE', `/api/projects/${id}`),
  getVersion: (id: string) => request<Version>('GET', `/api/versions/${id}`),
  restoreVersion: (id: string) => request<Version>('POST', `/api/versions/${id}/restore`),
  saveVersion: (projectId: string, files: Files, summary: string) =>
    request<Version>('POST', `/api/projects/${projectId}/versions`, { files, summary }),
}

/** POSTs a chat message and yields NDJSON run events as they stream in. */
export async function* sendMessage(
  projectId: string,
  content: string,
  signal?: AbortSignal,
): AsyncGenerator<RunEvent> {
  const resp = await fetch(`/api/projects/${projectId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
    credentials: 'same-origin',
    signal,
  })
  if (!resp.ok || !resp.body) throw await toError(resp)
  const reader = resp.body.pipeThrough(new TextDecoderStream()).getReader()
  let buf = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buf += value
    let nl: number
    while ((nl = buf.indexOf('\n')) !== -1) {
      const line = buf.slice(0, nl).trim()
      buf = buf.slice(nl + 1)
      if (line) yield JSON.parse(line) as RunEvent
    }
  }
  if (buf.trim()) yield JSON.parse(buf) as RunEvent
}
