import { strToU8, zipSync } from 'fflate'
import { dependenciesFor } from './agents'
import type { Files } from './api'
import { CDN_TAILWIND, indexHtml, RESERVED } from './sandpack'

const ENTRY = `import React, { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

import App from "./App";

const root = createRoot(document.getElementById("root"));
root.render(
  <StrictMode>
    <App />
  </StrictMode>
);
`

/** Packs a version as a Create React App project mirroring the Sandpack runtime. */
export function downloadProjectZip(title: string, files: Files) {
  const slug = title.replace(/[^\p{L}\p{N}]+/gu, '-').replace(/^-|-$/g, '') || 'app'
  const pkg = {
    name: 'mini-atoms-app',
    private: true,
    version: '0.1.0',
    scripts: { start: 'react-scripts start', build: 'react-scripts build' },
    dependencies: {
      react: '^19.0.0',
      'react-dom': '^19.0.0',
      'react-scripts': '5.0.1',
      ...dependenciesFor(files),
    },
    browserslist: { production: ['>0.2%', 'not dead'], development: ['last 1 chrome version'] },
  }
  const entries: Record<string, Uint8Array> = {
    'package.json': strToU8(JSON.stringify(pkg, null, 2) + '\n'),
    'public/index.html': strToU8(indexHtml(CDN_TAILWIND)),
    'src/index.js': strToU8(ENTRY),
    'README.md': strToU8(`# ${title}\n\n由 mini-atoms 生成。\n\n\`\`\`bash\nnpm install\nnpm start\n\`\`\`\n`),
  }
  if (!files['/styles.css']) entries['src/styles.css'] = strToU8('')
  for (const [path, code] of Object.entries(files)) {
    if (!RESERVED.has(path)) entries[`src${path}`] = strToU8(code)
  }
  const blob = new Blob([zipSync(entries)], { type: 'application/zip' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${slug}.zip`
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
