import { ApiError } from './index'

export interface ApiResponse<T> {
  data: T
  status: number
}

export interface ApiRequestConfig {
  headers?: Record<string, string>
  params?: Record<string, string | number | boolean>
  timeout?: number
}

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  email: string
  username: string
  password: string
  full_name?: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in?: number
}

export interface ErrorResponse {
  detail: string
  code?: string
  errors?: ApiError['errors']
}

export type { ApiError }