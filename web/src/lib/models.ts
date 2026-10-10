import { useEffect, useState } from 'react'
import { api, type ModelsInfo } from './api'

const STORAGE_KEY = 'mini-atoms:race-models'
let cached: Promise<ModelsInfo> | null = null

/** Models available for Race, fetched once per page load. */
export function useModels(): ModelsInfo | null {
  const [info, setInfo] = useState<ModelsInfo | null>(null)
  useEffect(() => {
    cached ??= api.models()
    cached.then(setInfo, () => {
      cached = null
    })
  }, [])
  return info
}

/** The user's last race line-up, or the first two models. */
export function initialRaceModels(info: ModelsInfo): string[] {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]') as string[]
    const valid = saved.filter((m) => info.race_models.includes(m)).slice(0, info.max_race_lanes)
    if (valid.length >= 2) return valid
  } catch {
    // ignore malformed storage
  }
  return info.race_models.slice(0, 2)
}

export function rememberRaceModels(models: string[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(models))
}
