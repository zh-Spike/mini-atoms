import clsx from 'clsx'
import { FlaskConical } from 'lucide-react'
import { useModels } from '../lib/models'

/** Shown when the server has no model configured and replays prebuilt apps instead. */
export default function DemoBadge({ className }: { className?: string }) {
  const models = useModels()
  if (!models?.demo) return null
  return (
    <span
      title="服务端未接入模型，生成结果为预置的示例应用；流程、预览、版本和分享都真实可用"
      className={clsx(
        'items-center gap-1 rounded-full border border-amber-300 bg-amber-50 px-2.5 py-1 text-xs whitespace-nowrap text-amber-800',
        className ?? 'flex',
      )}
    >
      <FlaskConical className="size-3.5" />
      演示模式
    </span>
  )
}
