export * from './index'

export interface UserBase {
  email: string
  username: string
  full_name?: string
}

export interface UserCreate extends UserBase {
  password: string
}

export interface UserUpdate {
  email?: string
  username?: string
  full_name?: string
  password?: string
}

export interface UserResponse extends UserBase {
  id: string
  is_active: boolean
  is_superuser: boolean
  created_at: string
  updated_at: string
}

export interface Token {
  access_token: string
  refresh_token?: string
  token_type: string
}

export interface TokenPayload {
  sub: string
  exp: number
  iat: number
}