import { describe, expect, it } from 'vitest'
import type { WSProgressMessage } from '@/api/types'

describe('api/types - WSProgressMessage', () => {
  it('stage 字段值包含 connected/queued/running/succeeded/failed', () => {
    const validStages: WSProgressMessage['stage'][] = [
      'connected',
      'queued',
      'running',
      'succeeded',
      'failed',
    ]
    expect(validStages).toHaveLength(5)
    expect(validStages).toContain('connected')
    expect(validStages).toContain('queued')
    expect(validStages).toContain('running')
    expect(validStages).toContain('succeeded')
    expect(validStages).toContain('failed')
  })

  it('可以构造各 stage 值的 WSProgressMessage 对象', () => {
    const stages: WSProgressMessage['stage'][] = [
      'connected',
      'queued',
      'running',
      'succeeded',
      'failed',
    ]
    stages.forEach((stage) => {
      const msg: WSProgressMessage = {
        analysis_id: 1,
        stage,
        progress: 0,
        message: `stage=${stage}`,
      }
      expect(msg.stage).toBe(stage)
      expect(msg.analysis_id).toBe(1)
    })
  })

  it('stage 字段值为预定义的五个状态之一', () => {
    const validStages = ['connected', 'queued', 'running', 'succeeded', 'failed']
    const msg: WSProgressMessage = {
      analysis_id: 1,
      stage: 'running',
      progress: 50,
      message: 'processing',
    }
    expect(validStages).toContain(msg.stage)
  })
})
