/**
 * cn 工具函数单元测试（clsx + tailwind-merge）
 */
import { describe, it, expect } from 'vitest'
import { cn } from '../src/lib/utils'

describe('cn', () => {
  it('合并多个类名', () => {
    expect(cn('a', 'b', 'c')).toBe('a b c')
  })

  it('条件类名：falsy 值被忽略', () => {
    expect(cn('a', false && 'b', undefined, 'c')).toBe('a c')
  })

  it('冲突的 tailwind 类以后者为准', () => {
    expect(cn('px-2', 'px-4')).toBe('px-4')
  })
})
