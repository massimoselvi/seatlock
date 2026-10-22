// Renders every view of the running Structurizr workspace to an SVG file.
//
//   node export-diagrams.mjs [output-dir]
//
// Environment:
//   STRUCTURIZR_URL  the diagrams page of the running server
//                    (default http://localhost:8080/workspace/1/diagrams)
//   CHROME_PATH      a Chrome or Chromium executable. Without it, Playwright's own browser is used
//                    (install it once with: pnpm exec playwright-core install chromium)
//
// The server must be running first. export.sh starts it, runs this script and stops it.
import { mkdirSync, writeFileSync } from 'node:fs'
import { chromium } from 'playwright-core'

const url = process.env.STRUCTURIZR_URL ?? 'http://localhost:8080/workspace/1/diagrams'
const outDir = process.argv[2] ?? new URL('../diagrams/', import.meta.url).pathname
const chromePath = process.env.CHROME_PATH

mkdirSync(outDir, { recursive: true })

const browser = await chromium.launch(chromePath ? { executablePath: chromePath } : {})
try {
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } })
  await page.goto(url, { timeout: 30_000 })
  await page.waitForFunction(
    () => window.structurizr?.scripting?.isDiagramRendered(),
    null,
    { timeout: 30_000 },
  )

  const views = await page.evaluate(() => structurizr.scripting.getViews())
  console.log(`${views.length} views`)

  for (const { key } of views) {
    // exportViews takes the keys to export and calls back once for each one.
    const diagram = await page.evaluate(
      viewKey =>
        new Promise((resolve, reject) => {
          const timer = setTimeout(() => reject(new Error(`timeout exporting ${viewKey}`)), 30_000)
          structurizr.scripting.exportViews(
            [viewKey],
            { format: 'svg', prefix: '', animation: false },
            (_view, exported) => {
              clearTimeout(timer)
              resolve(exported.content)
            },
            () => {},
          )
        }),
      key,
    )
    // The content is a base64 data URL.
    const svg = Buffer.from(diagram.split(',')[1], 'base64').toString('utf8')
    writeFileSync(`${outDir}/${key}.svg`, svg)
    console.log(`  ${key}.svg  ${Math.round(svg.length / 1024)} KB`)
  }
} finally {
  await browser.close()
}
