export type Files = Record<string, string>

export interface Me {
  user_id: string
  username: string
  generations_used: number
  generation_limit: number
  is_admin: boolean
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
  source: 'ai' | 'manual' | 'restore' | 'race'
  label: string | null
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
  share: ShareInfo | null
}

export interface ShareInfo {
  slug: string
  version_id: string
  version_number: number
  views: number
  updated_at: string
}

export interface SharedApp {
  title: string
  files: Files
  version_number: number
  views: number
  updated_at: string
}

export interface ModelsInfo {
  default: string
  race_models: string[]
  max_race_lanes: number
}

export interface AgentUsage {
  agent: AgentId
  model: string
  tokens: number
  duration_ms: number
  calls: number
}

export interface RunStats {
  duration_ms: number
  tokens: number
  by_agent?: AgentUsage[]
}

export type RunStatus = 'running' | 'ok' | 'error' | 'aborted'

export interface RunSummary {
  id: string
  project_id: string
  project_title: string | null
  username?: string
  mode: 'build' | 'edit' | 'rebuild'
  race_lanes: number
  status: RunStatus
  tokens: number
  prompt_tokens: number
  completion_tokens: number
  duration_ms: number
  qa_ok: boolean | null
  qa_issues: string[]
  version_id: string | null
  error: string | null
  created_at: string
}

export interface LLMCallTrace {
  id: string
  agent: AgentId
  step: string
  lane: number | null
  model: string
  protocol: string
  thinking: string
  output: string
  prompt_tokens: number
  completion_tokens: number
  ttft_ms: number | null
  duration_ms: number
  status: 'ok' | 'error' | 'aborted'
  error: string | null
  started_at: string
  /** Only in admin traces. */
  messages?: { role: string; content: string }[]
}

export interface RunDetail extends RunSummary {
  calls: LLMCallTrace[]
}

export interface RunTotals {
  runs: number
  ok: number
  error: number
  aborted: number
  running: number
  success_rate: number | null
  tokens: number
  prompt_tokens: number
  completion_tokens: number
  p50_duration_ms: number | null
  p95_duration_ms: number | null
}

export interface DailyPoint {
  date: string
  runs: number
  ok: number
  error: number
  tokens: number
  users: number
}

export interface ModelUsage {
  model: string
  calls: number
  errors: number
  success_rate: number | null
  avg_ttft_ms: number | null
  p95_ttft_ms: number | null
  avg_duration_ms: number
  tokens: number
}

export interface AgentTotals {
  agent: AgentId
  calls: number
  tokens: number
  avg_duration_ms: number
}

export interface UsageReport {
  days: number
  quota: { used: number; limit: number }
  totals: RunTotals
  daily: DailyPoint[]
  by_model: ModelUsage[]
  by_agent: AgentTotals[]
  recent: RunSummary[]
}

export interface AdminOverview {
  days: number
  users: { total: number; new: number; active: number }
  projects: { total: number; new: number }
  totals: RunTotals
  daily: DailyPoint[]
  by_model: ModelUsage[]
  by_agent: AgentTotals[]
  quality: {
    qa_pass_rate: number | null
    fix_rate: number | null
    race_runs: number
    race_adopted: number
  }
  top_users: { username: string; runs: number; tokens: number }[]
  quota_alerts: { username: string; used: number; limit: number }[]
  invites: { code: string; used: number; max: number; enabled: boolean }[]
  shares: {
    total: number
    views_total: number
    views_window: number
    top: { slug: string; title: string | null; views: number }[]
  }
}

export interface AdminRunPage {
  total: number
  page: number
  page_size: number
  models: string[]
  items: RunSummary[]
}

export type ComponentState = 'up' | 'down' | 'unconfigured'

export interface ServiceStatus {
  status: 'operational' | 'degraded' | 'down'
  version: string
  uptime_s: number
  checked_at: string
  components: {
    name: 'app' | 'database' | 'llm_gateway'
    status: ComponentState
    latency_ms: number | null
    detail: string
  }[]
  runs_24h: {
    runs: number
    ok: number
    error: number
    success_rate: number | null
    p50_duration_ms: number | null
  }
  hourly: { hour: string; ok: number; error: number }[]
  models_24h: Pick<ModelUsage, 'model' | 'calls' | 'errors' | 'success_rate' | 'avg_ttft_ms'>[]
}

export interface ShareStats {
  days: number
  views_total: number
  views_window: number
  daily: { date: string; views: number }[]
  referrers: { host: string; views: number }[]
  devices: { device: 'desktop' | 'mobile'; views: number }[]
}

export type AgentId = 'mike' | 'emma' | 'bob' | 'alex' | 'qa'

/** Events inside a race lane carry `lane`; their `agent_end` has no saved message. */
type Lane = { lane?: number }

export type RunEvent =
  | { type: 'run_start'; run_id: string }
  | { type: 'user_message'; message: Message }
  | ({ type: 'agent_start'; agent: AgentId } & Lane)
  | ({ type: 'delta'; agent: AgentId; text: string } & Lane)
  | ({ type: 'thinking'; agent: AgentId; text: string } & Lane)
  | ({ type: 'file_start'; agent: AgentId; path: string } & Lane)
  | ({ type: 'file_delta'; agent: AgentId; path: string; text: string } & Lane)
  | ({ type: 'file_end'; agent: AgentId; path: string; content: string } & Lane)
  | ({
      type: 'agent_end'
      agent: AgentId
      message?: Message
      ok?: boolean
      issues?: string[]
    } & Lane)
  | { type: 'version'; version: Version; message_id: string }
  | { type: 'race_start'; lanes: string[] }
  | { type: 'lane_finished'; lane: number; ok: boolean }
  | { type: 'lane_done'; lane: number; version: Version; message: Message }
  | { type: 'lane_error'; lane: number; message: string }
  | { type: 'race_done'; version_ids: string[] }
  | { type: 'notice'; text: string }
  | { type: 'error'; message: string; saved?: Message }
  | { type: 'done'; run_id?: string; stats?: RunStats }

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
  login: (username: string, password: string) =>
    request<Me>('POST', '/api/auth/login', { username, password }),
  register: (inviteCode: string, username: string, password: string) =>
    request<Me>('POST', '/api/auth/register', { invite_code: inviteCode, username, password }),
  logout: () => request<{ ok: boolean }>('POST', '/api/auth/logout'),
  listProjects: () => request<ProjectSummary[]>('GET', '/api/projects'),
  createProject: (prompt: string) => request<ProjectSummary>('POST', '/api/projects', { prompt }),
  getProject: (id: string) => request<ProjectDetail>('GET', `/api/projects/${id}`),
  deleteProject: (id: string) => request<{ ok: boolean }>('DELETE', `/api/projects/${id}`),
  getVersion: (id: string) => request<Version>('GET', `/api/versions/${id}`),
  restoreVersion: (id: string) => request<Version>('POST', `/api/versions/${id}/restore`),
  saveVersion: (projectId: string, files: Files, summary: string) =>
    request<Version>('POST', `/api/projects/${projectId}/versions`, { files, summary }),
  publish: (projectId: string) => request<ShareInfo>('POST', `/api/projects/${projectId}/share`),
  unpublish: (projectId: string) =>
    request<{ ok: boolean }>('DELETE', `/api/projects/${projectId}/share`),
  getShared: (slug: string, referrer = '') =>
    request<SharedApp>('GET', `/api/share/${slug}?ref=${encodeURIComponent(referrer)}`),
  shareStats: (projectId: string, days = 7) =>
    request<ShareStats>('GET', `/api/projects/${projectId}/share/stats?days=${days}`),
  models: () => request<ModelsInfo>('GET', '/api/models'),
  usage: (days = 7) => request<UsageReport>('GET', `/api/me/usage?days=${days}`),
  getRun: (id: string) => request<RunDetail>('GET', `/api/runs/${id}`),
  adminOverview: (days = 7) => request<AdminOverview>('GET', `/api/admin/overview?days=${days}`),
  adminRuns: (filters: { status?: string; model?: string; username?: string; page?: number }) => {
    const q = new URLSearchParams()
    for (const [k, v] of Object.entries(filters)) if (v) q.set(k, String(v))
    return request<AdminRunPage>('GET', `/api/admin/runs?${q}`)
  },
  adminRun: (id: string) => request<RunDetail>('GET', `/api/admin/runs/${id}`),
  status: () => request<ServiceStatus>('GET', '/api/status'),
}

/** POSTs a chat message and yields NDJSON run events as they stream in. */
export async function* sendMessage(
  projectId: string,
  content: string,
  raceModels: string[] | null,
  signal?: AbortSignal,
): AsyncGenerator<RunEvent> {
  const resp = await fetch(`/api/projects/${projectId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, race: raceModels !== null, race_models: raceModels ?? [] }),
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
