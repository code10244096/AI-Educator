import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * 通用数据加载：const { data, loading, error, reload, setData } = useAsync(() => api.get(), [deps])
 * - 首次加载 loading=true；reload() 重新请求（重试按钮用）
 * - reload({ silent: true }) 后台刷新：不切回加载态，失败时保留旧数据
 */
export default function useAsync(fetcher, deps = [], { immediate = true } = {}) {
  const [data, setData] = useState(undefined)
  const [loading, setLoading] = useState(immediate)
  const [error, setError] = useState(null)
  const seq = useRef(0)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const reload = useCallback(async ({ silent = false } = {}) => {
    const id = ++seq.current
    if (!silent) {
      setLoading(true)
      setError(null)
    }
    try {
      const result = await fetcherRef.current()
      if (id === seq.current) {
        setData(result)
        setError(null)
      }
      return result
    } catch (err) {
      if (id === seq.current && !silent) setError(err)
      return undefined
    } finally {
      if (id === seq.current && !silent) setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (immediate) reload()
    return () => { seq.current += 1 }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return { data, loading, error, reload, setData }
}
