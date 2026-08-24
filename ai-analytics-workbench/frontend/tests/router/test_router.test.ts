import { describe, expect, it } from 'vitest'
import router from '@/router'

describe('router - 路由配置', () => {
  it('routes are defined：包含 datasets/analysis/reports 三个路由', () => {
    const routes = router.options.routes
    const names = routes.map((r) => r.name).filter(Boolean)
    expect(names).toContain('datasets')
    expect(names).toContain('analysis')
    expect(names).toContain('reports')
  })

  it('root redirects to datasets：/ 重定向到 /datasets', () => {
    const rootRoute = router.options.routes.find((r) => r.path === '/')
    expect(rootRoute).toBeDefined()
    expect(rootRoute?.redirect).toBe('/datasets')
  })
})
