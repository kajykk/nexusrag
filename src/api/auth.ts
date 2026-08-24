import client from './client'

export interface User {
  id: string
  email: string
  name: string
  created_at: string
}

export interface AuthResp {
  user: User
  token: string
}

export const authApi = {
  async register(email: string, password: string, name: string): Promise<AuthResp> {
    const { data } = await client.post('/auth/register', { email, password, name })
    return data.data
  },
  async login(email: string, password: string): Promise<AuthResp> {
    const { data } = await client.post('/auth/login', { email, password })
    return data.data
  },
  async demo(): Promise<AuthResp> {
    const { data } = await client.post('/auth/demo')
    return data.data
  },
  async me(): Promise<User> {
    const { data } = await client.get('/auth/me')
    return data.data
  },
}
