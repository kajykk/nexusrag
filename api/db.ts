/**
 * SQLite 数据库初始化 - 使用 Node 24 内置的 node:sqlite（无需原生编译）
 */
import { DatabaseSync } from 'node:sqlite'
import fs from 'fs'
import path from 'path'
import { config } from './config.js'

// 确保数据目录存在
const dbDir = path.dirname(config.storage.dbPath)
if (!fs.existsSync(dbDir)) {
  fs.mkdirSync(dbDir, { recursive: true })
}

const db = new DatabaseSync(config.storage.dbPath)

// 启用 WAL 模式与外键
db.exec('PRAGMA journal_mode = WAL')
db.exec('PRAGMA foreign_keys = ON')

// 初始化所有表
db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
  );

  CREATE TABLE IF NOT EXISTS knowledge_bases (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    description TEXT,
    document_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
  );

  CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    kb_id TEXT NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size INTEGER,
    status TEXT DEFAULT 'pending',
    chunk_count INTEGER DEFAULT 0,
    error TEXT,
    created_at TEXT DEFAULT (datetime('now'))
  );

  CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    kb_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    vector_id TEXT NOT NULL,
    token_count INTEGER,
    metadata TEXT
  );

  CREATE TABLE IF NOT EXISTS chat_sessions (
    id TEXT PRIMARY KEY,
    kb_id TEXT NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id),
    title TEXT,
    mode TEXT DEFAULT 'normal',
    created_at TEXT DEFAULT (datetime('now'))
  );

  CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    citations TEXT,
    created_at TEXT DEFAULT (datetime('now'))
  );

  CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);
  CREATE INDEX IF NOT EXISTS idx_chunks_kb ON chunks(kb_id);
  CREATE INDEX IF NOT EXISTS idx_documents_kb ON documents(kb_id);
  CREATE INDEX IF NOT EXISTS idx_sessions_kb ON chat_sessions(kb_id);
  CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages(session_id);
`)

/**
 * 包装一层，让 API 更接近 better-sqlite3
 * 主要是 transaction() 方法的替代实现
 */
export type DbValue = null | undefined | number | bigint | string | Uint8Array

export interface DBProxy {
  prepare: (sql: string) => Statement
  exec: (sql: string) => void
  transaction: <T>(fn: () => T) => () => T
}

export interface Statement {
  run: (...args: DbValue[]) => { changes: number; lastInsertRowid: number | bigint }
  get: (...args: DbValue[]) => unknown
  all: (...args: DbValue[]) => unknown[]
}

const proxy: DBProxy = {
  prepare(sql: string): Statement {
    const stmt = db.prepare(sql) as unknown as {
      run: (...args: DbValue[]) => { changes: number; lastInsertRowid: number | bigint }
      get: (...args: DbValue[]) => unknown
      all: (...args: DbValue[]) => unknown[]
    }
    return {
      // node:sqlite 的 run 接受参数数组
      run: (...args: DbValue[]) => stmt.run(...args),
      get: (...args: DbValue[]) => stmt.get(...args),
      all: (...args: DbValue[]) => stmt.all(...args),
    }
  },
  exec(sql: string) {
    db.exec(sql)
  },
  transaction<T>(fn: () => T): () => T {
    return () => {
      db.exec('BEGIN')
      try {
        const result = fn()
        db.exec('COMMIT')
        return result
      } catch (err) {
        db.exec('ROLLBACK')
        throw err
      }
    }
  },
}

export default proxy
