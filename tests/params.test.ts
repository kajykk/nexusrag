/**
 * params 工具单元测试
 */
import { describe, it, expect } from 'vitest'
import { paramToStr } from '../api/utils/params.js'

describe('paramToStr', () => {
  it('字符串原样返回', () => {
    expect(paramToStr('abc')).toBe('abc')
  })

  it('数组取首个元素', () => {
    expect(paramToStr(['a', 'b'])).toBe('a')
  })

  it('undefined 返回空字符串', () => {
    expect(paramToStr(undefined)).toBe('')
  })

  it('空数组返回空字符串', () => {
    expect(paramToStr([])).toBe('')
  })
})
