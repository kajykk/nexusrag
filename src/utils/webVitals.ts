/**
 * Web Vitals 采集与上报（LCP / INP / CLS / FCP / TTFB）
 *
 * 通过 PerformanceObserver 采集 Core Web Vitals，通过可注入 reporter 上报
 * （默认 console，可替换为 Sentry / 自建埋点）。
 *
 * 用法：main.ts 中调用 initWebVitals()
 * 阈值与 web-vitals 库一致：LCP 2500/4000ms、INP 200/500ms、
 * CLS 0.1/0.25、TTFB 800/1800ms、FCP 1800/3000ms
 */

export interface WebVitalMetric {
  name: string
  value: number
  rating: 'good' | 'needs-improvement' | 'poor'
  delta?: number
  id?: string
}

export type WebVitalsReporter = (metric: WebVitalMetric) => void

const defaultReporter: WebVitalsReporter = (metric) => {
  if (import.meta.env.PROD) {
    console.info(`[WebVitals] ${metric.name}: ${metric.value.toFixed(1)} (${metric.rating})`)
  }
}

/** 阈值判定（与 web-vitals 库一致） */
export function ratingFor(name: string, value: number): WebVitalMetric['rating'] {
  if (name === 'CLS') {
    if (value <= 0.1) return 'good'
    if (value <= 0.25) return 'needs-improvement'
    return 'poor'
  }
  const good = name === 'LCP' ? 2500 : name === 'INP' ? 200 : name === 'TTFB' ? 800 : 1800
  const poor = name === 'LCP' ? 4000 : name === 'INP' ? 500 : name === 'TTFB' ? 1800 : 3000
  if (value <= good) return 'good'
  if (value <= poor) return 'needs-improvement'
  return 'poor'
}

function observe(_name: string, type: string, callback: (entries: PerformanceEntryList) => void): void {
  if (typeof PerformanceObserver === 'undefined') return
  try {
    const observer = new PerformanceObserver((list) => callback(list.getEntries()))
    observer.observe({ type, buffered: true })
  } catch {
    // 浏览器不支持该指标类型时静默跳过
  }
}

function watchLCP(report: WebVitalsReporter): void {
  let lastValue = 0
  observe('LCP', 'largest-contentful-paint', (entries) => {
    const entry = entries[entries.length - 1] as PerformanceEntry & { startTime: number }
    if (!entry) return
    lastValue = entry.startTime
    report({ name: 'LCP', value: lastValue, rating: ratingFor('LCP', lastValue) })
  })
  window.addEventListener('load', () => {
    setTimeout(() => {
      if (lastValue > 0) {
        report({ name: 'LCP', value: lastValue, rating: ratingFor('LCP', lastValue) })
      }
    }, 0)
  })
}

function watchFCP(report: WebVitalsReporter): void {
  observe('FCP', 'paint', (entries) => {
    const entry = entries.find((e) => e.name === 'first-contentful-paint')
    if (!entry) return
    report({ name: 'FCP', value: entry.startTime, rating: ratingFor('FCP', entry.startTime) })
  })
}

function watchINP(report: WebVitalsReporter): void {
  observe('INP', 'event', (entries) => {
    const last = entries[entries.length - 1] as PerformanceEventTiming | undefined
    if (!last || last.duration <= 0) return
    report({ name: 'INP', value: last.duration, rating: ratingFor('INP', last.duration) })
  })
}

function watchCLS(report: WebVitalsReporter): void {
  let cls = 0
  observe('CLS', 'layout-shift', (entries) => {
    for (const e of entries) {
      const entry = e as PerformanceEntry & { hadRecentInput: boolean; value: number }
      if (!entry.hadRecentInput) cls += entry.value
    }
    report({ name: 'CLS', value: cls, rating: ratingFor('CLS', cls) })
  })
}

function watchTTFB(report: WebVitalsReporter): void {
  const nav = performance.getEntriesByType('navigation')[0] as
    | (PerformanceNavigationTiming & { responseStart: number; requestStart: number })
    | undefined
  if (!nav) return
  const ttfb = nav.responseStart - nav.requestStart
  report({ name: 'TTFB', value: ttfb, rating: ratingFor('TTFB', ttfb) })
}

export function initWebVitals(reporter?: WebVitalsReporter): () => void {
  const report = reporter ?? defaultReporter
  watchLCP(report)
  watchFCP(report)
  watchINP(report)
  watchCLS(report)
  watchTTFB(report)
  return () => {
    // PerformanceObserver 页面生命周期内常驻；返回 no-op 保持接口一致
  }
}