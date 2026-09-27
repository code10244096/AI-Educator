import React from 'react'
import { AlertCircle, Inbox, Loader2, RotateCw } from 'lucide-react'

/*
 * 加载 / 空 / 出错 三态（R1-014）
 *
 *   if (loading) return <Loading />                       // 或 <Loading variant="skeleton" rows={4} />
 *   if (error)   return <ErrorState error={error} onRetry={reload} />
 *   if (!items.length) return <Empty title="还没有作业" desc="布置作业后会显示在这里" action={{ label: '布置作业', onClick }} />
 *
 * 规则：加载完成前不渲染“暂无数据/共 0 条”；接口失败显示中文原因 + 重试，不显示空状态。
 */

// 把接口错误转成老师能看懂的中文原因（后端 detail 优先）
export function describeError(error, fallback = '加载失败，请稍后重试') {
  if (!error) return fallback
  if (typeof error === 'string') return error
  const response = error.response
  const detail = response?.data?.detail
  if (typeof detail === 'string' && /[一-鿿]/.test(detail)) return detail
  if (Array.isArray(detail) && typeof detail[0]?.msg === 'string' && /[一-鿿]/.test(detail[0].msg)) return detail[0].msg
  if (!response) {
    if (error.code === 'ECONNABORTED') return '服务器响应超时，请稍后重试'
    if (error.isAxiosError || error.code === 'ERR_NETWORK' || error.name === 'ChunkLoadError' || /fetch|network|import/i.test(error.message || '')) {
      return '无法连接服务器，请检查网络后重试'
    }
    return error.message && /[一-鿿]/.test(error.message) ? error.message : fallback
  }
  const status = response.status
  if (status === 404) return '内容不存在或已被删除'
  if (status === 403) return '没有权限查看该内容'
  if (status === 401) return '登录已过期，请重新登录'
  if (status === 413) return '文件太大，请压缩后重试'
  if (status === 429) return '操作太频繁，请稍后再试'
  if (status >= 500) return '服务器出了点问题，请稍后重试'
  return fallback
}

function requestIdOf(error) {
  const headers = error?.response?.headers
  if (!headers) return ''
  return headers['x-request-id'] || headers['X-Request-ID'] || ''
}

export const Spinner = ({ className = 'h-5 w-5' }) => (
  <Loader2 className={`${className} text-blue-500 animate-spin`} aria-hidden="true" />
)

const SkeletonRows = ({ rows }) => (
  <div className="space-y-3" aria-hidden="true">
    {Array.from({ length: rows }).map((_, i) => (
      <div key={i} className="animate-pulse rounded-xl border border-gray-100 bg-white p-4">
        <div className="h-4 w-1/3 rounded bg-gray-200" />
        <div className="mt-3 h-3 w-2/3 rounded bg-gray-100" />
      </div>
    ))}
  </div>
)

/** 加载中：默认居中 spinner；variant="skeleton" 显示骨架行；variant="inline" 用于按钮旁/小区域 */
export const Loading = ({ text = '加载中…', variant = 'spinner', rows = 3, className = '' }) => {
  if (variant === 'skeleton') {
    return (
      <div className={className} role="status" aria-live="polite" data-state="loading">
        <span className="sr-only">{text}</span>
        <SkeletonRows rows={rows} />
      </div>
    )
  }
  if (variant === 'inline') {
    return (
      <span className={`inline-flex items-center gap-2 text-sm text-gray-500 ${className}`} role="status" data-state="loading">
        <Spinner className="h-4 w-4" />
        {text}
      </span>
    )
  }
  return (
    <div className={`flex flex-col items-center justify-center py-16 text-sm text-gray-500 ${className}`} role="status" aria-live="polite" data-state="loading">
      <Spinner className="h-6 w-6" />
      <span className="mt-3">{text}</span>
    </div>
  )
}

const ActionButton = ({ action, primary }) => {
  if (!action) return null
  if (React.isValidElement(action)) return action
  const Icon = action.icon
  return (
    <button
      type="button"
      onClick={action.onClick}
      className={primary
        ? 'inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700'
        : 'inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50'}
    >
      {Icon && <Icon className="h-4 w-4" />}
      {action.label}
    </button>
  )
}

/** 空状态：说明 + 下一步操作。action / secondaryAction 为 {label, onClick, icon?} 或任意 React 元素 */
export const Empty = ({ icon: Icon = Inbox, title = '暂无内容', desc, action, secondaryAction, compact = false, className = '' }) => (
  <div className={`flex flex-col items-center justify-center text-center ${compact ? 'py-8' : 'py-14'} px-4 ${className}`} data-state="empty">
    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-50">
      <Icon className="h-6 w-6 text-blue-500" />
    </div>
    <h3 className="mt-4 text-base font-medium text-gray-900">{title}</h3>
    {desc && <p className="mt-1 max-w-sm text-sm text-gray-500">{desc}</p>}
    {(action || secondaryAction) && (
      <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
        <ActionButton action={action} primary />
        <ActionButton action={secondaryAction} />
      </div>
    )}
  </div>
)

/** 出错：中文原因 + 重试。传 error（接口异常对象）或 message（直接文案） */
export const ErrorState = ({ error, message, title = '加载失败', onRetry, retrying = false, compact = false, className = '' }) => {
  const reason = message || describeError(error)
  const requestId = requestIdOf(error)
  return (
    <div className={`flex flex-col items-center justify-center text-center ${compact ? 'py-8' : 'py-14'} px-4 ${className}`} role="alert" data-state="error">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-50">
        <AlertCircle className="h-6 w-6 text-red-500" />
      </div>
      <h3 className="mt-4 text-base font-medium text-gray-900">{title}</h3>
      <p className="mt-1 max-w-sm text-sm text-gray-500">{reason}</p>
      {requestId && <p className="mt-1 text-xs text-gray-400">反馈问题时请提供编号：{requestId}</p>}
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          disabled={retrying}
          className="mt-5 inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-60"
        >
          <RotateCw className={`h-4 w-4 ${retrying ? 'animate-spin' : ''}`} />
          重试
        </button>
      )}
    </div>
  )
}

/**
 * 便捷包装：<AsyncView loading error onRetry isEmpty empty={<Empty …/>}>内容</AsyncView>
 * 顺序固定为 加载 → 出错 → 空 → 内容。
 */
export const AsyncView = ({ loading, error, onRetry, isEmpty, empty, loadingView, children }) => {
  if (loading) return loadingView || <Loading />
  if (error) return <ErrorState error={error} onRetry={onRetry} />
  if (isEmpty) return empty || <Empty />
  return children
}
