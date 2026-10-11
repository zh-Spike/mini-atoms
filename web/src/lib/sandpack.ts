import tailwindBrowserUrl from '@tailwindcss/browser?url'
import { dependenciesFor } from './agents'
import type { Files } from './api'

/** Files the runtime provides; the AI never writes them and they are excluded from saves. */
export const RESERVED = new Set(['/index.js', '/public/index.html', '/package.json'])

/** Served by this app, so previews do not depend on cdn.tailwindcss.com (unreachable in some regions). */
const SELF_HOSTED_TAILWIND = new URL(tailwindBrowserUrl, window.location.origin).href
export const CDN_TAILWIND = 'https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4.3.3'

const DARK_VARIANT = '@custom-variant dark (&:where(.dark, .dark *));'

/** HTML for exported projects; CRA honours it. Sandpack ignores this file's <head>. */
export function indexHtml(tailwindSrc: string): string {
  return `<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <script src="${tailwindSrc}"></script>
    <style type="text/tailwindcss">
      ${DARK_VARIANT}
    </style>
  </head>
  <body>
    <div id="root"></div>
  </body>
</html>
`
}

/** Sandpack entry: registers the class-based dark variant with the Tailwind runtime, then renders. */
const SANDPACK_ENTRY = `import React, { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import App from "./App";

const tw = document.createElement("style");
tw.setAttribute("type", "text/tailwindcss");
tw.textContent = ${JSON.stringify(DARK_VARIANT)};
document.head.appendChild(tw);

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>
);
`

export type SandpackFiles = Record<string, { code: string; active?: boolean; hidden?: boolean }>

export interface SandpackSetup {
  files: SandpackFiles
  dependencies: Files
  /** Pass as `options.externalResources`; Sandpack injects these into the preview's <head>. */
  externalResources: string[]
}

export function toSandpack(files: Files): SandpackSetup {
  const out: SandpackFiles = {}
  for (const [path, code] of Object.entries(files)) out[path] = { code }
  if (!out['/styles.css']) out['/styles.css'] = { code: '/* 自定义样式 */\n' }
  out['/index.js'] = { code: SANDPACK_ENTRY, hidden: true }
  if (out['/App.js']) out['/App.js'].active = true
  return {
    files: out,
    dependencies: dependenciesFor(files),
    externalResources: [SELF_HOSTED_TAILWIND],
  }
}
