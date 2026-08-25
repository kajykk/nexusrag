/**
 * Express 5 类型收紧后 req.params 值可能为 string | string[]；
 * 统一收窄为单值字符串（取首个），保证与 node:sqlite 参数绑定兼容。
 */
export function paramToStr(v: string | string[] | undefined): string {
  if (Array.isArray(v)) return v[0] ?? ''
  return v ?? ''
}
