/**
 * Sandpack hashes the project files with `crypto.subtle.digest` to build its preview id, but
 * browsers only expose `crypto.subtle` in secure contexts (HTTPS or localhost). On plain HTTP the
 * call throws and the preview never connects. The id only needs to be stable, not secure, so a
 * non-cryptographic hash is enough here.
 */
function fnv1a(bytes: Uint8Array, seed: number): number {
  let h = (0x811c9dc5 ^ seed) >>> 0
  for (const b of bytes) {
    h ^= b
    h = Math.imul(h, 0x01000193) >>> 0
  }
  return h
}

if (typeof window !== 'undefined' && window.crypto && !window.crypto.subtle) {
  const digest = async (_algorithm: unknown, data: BufferSource): Promise<ArrayBuffer> => {
    const bytes =
      data instanceof ArrayBuffer
        ? new Uint8Array(data)
        : new Uint8Array(data.buffer, data.byteOffset, data.byteLength)
    const out = new DataView(new ArrayBuffer(32))
    for (let i = 0; i < 8; i++) out.setUint32(i * 4, fnv1a(bytes, i * 0x9e3779b9))
    return out.buffer
  }
  Object.defineProperty(window.crypto, 'subtle', {
    value: { digest } as unknown as SubtleCrypto,
    configurable: true,
  })
}

export {}
