export const slugify = (title: string) =>
  title.replace(/[^\p{L}\p{N}]+/gu, '-').replace(/^-|-$/g, '') || 'app'

export function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
