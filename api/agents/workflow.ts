/**
 * Agent 深度研究工作流
 * 基于 Plan → Retrieve → Reflect → Synthesize 模式
 * 使用 Function Calling 让 LLM 自主决策多轮检索
 */
import { chat, chatStream } from '../llm/client.js'
import { retrieve, rerank, toCitations } from '../rag/pipeline.js'
import type { Citation, RetrievedChunk, StreamChunk } from '../types/index.js'

/**
 * Agent 工作流入口
 */
export async function runAgentWorkflow(
  kbId: string,
  query: string,
  history: { role: 'user' | 'assistant'; content: string }[],
  onStep: (chunk: StreamChunk) => void,
  options?: { topK?: number; maxRounds?: number },
): Promise<{ answer: string; citations: Citation[] }> {
  const maxRounds = options?.maxRounds || 3
  const topK = options?.topK || 4

  // Step 1: Plan - 拆解子问题
  onStep({
    type: 'status',
    data: { status: '正在拆解问题...' },
  })

  const subQueries = await planSubqueries(query, history)
  onStep({
    type: 'status',
    data: { status: `已拆解为 ${subQueries.length} 个子问题：\n${subQueries.map((q, i) => `${i + 1}. ${q}`).join('\n')}` },
  })

  // Step 2: 多轮检索 + 反思
  const allResults: RetrievedChunk[] = []
  const seenChunkIds = new Set<string>()
  let round = 0

  while (round < maxRounds) {
    round++
    onStep({
      type: 'status',
      data: { status: `第 ${round} 轮检索中...` },
    })

    // 并行检索所有子问题
    const queriesToSearch = round === 1 ? subQueries : [query]
    for (const q of queriesToSearch) {
      const results = await retrieve(kbId, q, topK)
      const reranked = rerank(q, results)
      for (const r of reranked) {
        if (!seenChunkIds.has(r.chunk.id)) {
          allResults.push(r)
          seenChunkIds.add(r.chunk.id)
        }
      }
    }

    onStep({
      type: 'status',
      data: { status: `已检索到 ${allResults.length} 个相关片段` },
    })

    // Reflect: 评估信息是否充分
    const reflection = await reflect(query, allResults)
    onStep({
      type: 'status',
      data: { status: `反思：${reflection.thought}\n充分性：${reflection.sufficient ? '✓ 充分' : '✗ 仍需补充'}` },
    })

    if (reflection.sufficient || round >= maxRounds) {
      break
    }

    // 不充分时，根据反思生成新的检索查询
    if (reflection.newQueries && reflection.newQueries.length > 0) {
      onStep({
        type: 'status',
        data: { status: `根据反思，将搜索：${reflection.newQueries.join(', ')}` },
      })
      // 用新的查询覆盖下一轮
      const newResults = await Promise.all(
        reflection.newQueries.map((q) => retrieve(kbId, q, topK)),
      )
      for (const results of newResults) {
        const reranked = rerank(query, results)
        for (const r of reranked) {
          if (!seenChunkIds.has(r.chunk.id)) {
            allResults.push(r)
            seenChunkIds.add(r.chunk.id)
          }
        }
      }
    }
  }

  // 去重 + 排序，取 top
  allResults.sort((a, b) => b.score - a.score)
  const finalResults = allResults.slice(0, 10)
  const citations = toCitations(finalResults)

  // Step 3: Synthesize - 综合生成报告
  onStep({
    type: 'status',
    data: { status: '正在综合生成研究报告...' },
  })

  const context = finalResults
    .map((r, i) => `[${i + 1}] (来源: ${r.doc.name})\n${r.chunk.content}`)
    .join('\n\n---\n\n')

  const systemPrompt = `你是 NexusRAG Agent 深度研究助手。你刚刚通过多轮反思检索收集了以下上下文。

任务：基于检索到的上下文，为用户的问题生成一份**结构化研究报告**。

要求：
1. 使用 Markdown 格式，含标题、列表、表格等
2. 引用必须使用 [1][2] 这样的标注，对应编号
3. 报告结构：
   - **核心结论**（1-2 句话直接回答）
   - **详细分析**（按逻辑分点展开）
   - **关键证据**（引用检索到的原文片段）
   - **延伸思考**（基于上下文的合理推论）
4. 如有不足，明确指出信息缺口

## 检索到的上下文（共 ${finalResults.length} 个片段）

${context || '（未检索到相关内容）'}

## 引用列表

${citations.map((c) => `[${c.id}] ${c.docName} - ${c.content.slice(0, 80)}...`).join('\n')}
`

  const messages: { role: 'system' | 'user' | 'assistant'; content: string }[] = [
    { role: 'system', content: systemPrompt },
    ...history.slice(-4).map((h) => ({ role: h.role, content: h.content })),
    { role: 'user', content: query },
  ]

  onStep({ type: 'citation', data: { citations } })

  // 流式输出最终答案
  let answer = ''
  await chatStream(messages, (token) => {
    answer += token
    onStep({ type: 'token', data: { content: token } })
  }, { temperature: 0.4, maxTokens: 2000 })

  onStep({ type: 'done', data: {} })

  return { answer, citations }
}

/**
 * Plan 阶段：拆解子问题
 */
async function planSubqueries(
  query: string,
  history: { role: 'user' | 'assistant'; content: string }[],
): Promise<string[]> {
  const messages = [
    {
      role: 'system' as const,
      content: `你是 RAG 检索规划专家。用户提出一个问题，你需要将其拆解为 2-4 个具体的检索子查询，以便更全面地检索知识库。

要求：
1. 每个子查询应该是一个完整、具体的检索问题
2. 子查询之间应该互补，覆盖原问题的不同方面
3. 返回 JSON 格式：{"queries": ["子查询1", "子查询2", ...]}
4. 不要返回任何其他内容`,
    },
    ...history.slice(-2).map((h) => ({ role: h.role as 'user' | 'assistant', content: h.content })),
    { role: 'user' as const, content: query },
  ]

  try {
    const result = await chat(messages, { temperature: 0.2, json: true })
    const parsed = JSON.parse(result)
    return parsed.queries || [query]
  } catch {
    return [query]
  }
}

/**
 * Reflect 阶段：评估信息充分性
 */
async function reflect(
  originalQuery: string,
  results: RetrievedChunk[],
): Promise<{ sufficient: boolean; thought: string; newQueries?: string[] }> {
  if (results.length === 0) {
    return {
      sufficient: false,
      thought: '当前未检索到任何相关内容',
      newQueries: [originalQuery],
    }
  }

  if (results.length >= 8) {
    return {
      sufficient: true,
      thought: `已收集 ${results.length} 个相关片段，信息充足`,
    }
  }

  const context = results
    .map((r, i) => `[${i + 1}] ${r.chunk.content.slice(0, 200)}`)
    .join('\n')

  const messages = [
    {
      role: 'system' as const,
      content: `你是 RAG 反思专家。基于用户问题和已检索到的内容，评估信息是否充足。

返回 JSON：
{
  "sufficient": true/false,
  "thought": "简短评估（一句话）",
  "newQueries": ["补充查询1", "补充查询2"]  // 仅在 sufficient=false 时提供
}

要求：
- 如检索内容已能直接回答问题 → sufficient=true
- 如信息明显不足 → sufficient=false 并给出 1-2 个补充查询
- 不要返回任何其他内容`,
    },
    {
      role: 'user' as const,
      content: `原始问题：${originalQuery}\n\n已检索内容：\n${context}`,
    },
  ]

  try {
    const result = await chat(messages, { temperature: 0.1, json: true })
    return JSON.parse(result)
  } catch {
    return {
      sufficient: true,
      thought: '反思失败，按当前信息继续',
    }
  }
}
