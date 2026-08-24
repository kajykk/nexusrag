/**
 * JWT 认证中间件
 */
import { type Request, type Response, type NextFunction } from 'express'
import jwt from 'jsonwebtoken'
import { config } from '../config.js'

export interface AuthRequest extends Request {
  userId?: string
  userEmail?: string
}

export function generateToken(user: { id: string; email: string }): string {
  return jwt.sign({ id: user.id, email: user.email }, config.jwtSecret, {
    expiresIn: config.jwtExpiresIn,
  } as jwt.SignOptions)
}

export function authMiddleware(req: AuthRequest, res: Response, next: NextFunction): void {
  const authHeader = req.headers.authorization
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    res.status(401).json({ success: false, error: '未提供认证令牌' })
    return
  }

  const token = authHeader.slice(7)
  try {
    const decoded = jwt.verify(token, config.jwtSecret) as { id: string; email: string }
    req.userId = decoded.id
    req.userEmail = decoded.email
    next()
  } catch {
    res.status(401).json({ success: false, error: '认证令牌无效或已过期' })
  }
}

/**
 * 可选认证 - 不强制要求登录，但若有 token 则解析
 */
export function optionalAuth(req: AuthRequest, _res: Response, next: NextFunction): void {
  const authHeader = req.headers.authorization
  if (authHeader && authHeader.startsWith('Bearer ')) {
    const token = authHeader.slice(7)
    try {
      const decoded = jwt.verify(token, config.jwtSecret) as { id: string; email: string }
      req.userId = decoded.id
      req.userEmail = decoded.email
    } catch {
      // 忽略错误
    }
  }
  next()
}
