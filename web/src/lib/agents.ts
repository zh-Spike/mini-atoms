import type { AgentId } from './api'

export interface AgentMeta {
  name: string
  role: string
  color: string
  working: string
}

export const AGENTS: Record<AgentId, AgentMeta> = {
  mike: { name: 'Mike', role: '团队负责人', color: 'bg-zinc-800', working: '正在理解你的需求' },
  emma: { name: 'Emma', role: '产品经理', color: 'bg-pink-500', working: '正在撰写 PRD' },
  bob: { name: 'Bob', role: '架构师', color: 'bg-amber-500', working: '正在设计架构' },
  alex: { name: 'Alex', role: '工程师', color: 'bg-sky-500', working: '正在编写代码' },
  qa: { name: 'Quinn', role: '测试工程师', color: 'bg-emerald-500', working: '正在检查代码' },
}

export const PIPELINE: AgentId[] = ['emma', 'bob', 'alex', 'qa']

const PACKAGE_VERSIONS: Record<string, string> = {
  'lucide-react': '^0.460.0',
  recharts: '^2.13.3',
  'date-fns': '^3.6.0',
  clsx: '^2.1.1',
}

const IMPORT_RE = /(?:from\s+|import\s*\(\s*|import\s+|require\s*\(\s*)['"]([^'"./][^'"]*)['"]/g

/** Sandpack needs explicit dependencies for every bare import outside react/react-dom. */
export function dependenciesFor(files: Record<string, string>): Record<string, string> {
  const deps: Record<string, string> = {}
  for (const src of Object.values(files)) {
    for (const m of src.matchAll(IMPORT_RE)) {
      const spec = m[1]
      const name = spec.startsWith('@') ? spec.split('/').slice(0, 2).join('/') : spec.split('/')[0]
      if (PACKAGE_VERSIONS[name]) deps[name] = PACKAGE_VERSIONS[name]
    }
  }
  return deps
}
