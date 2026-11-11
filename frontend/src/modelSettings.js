// 个人模型凭据：只保存在当前浏览器，不写入服务端数据库／日志。
// 每次请求临时随请求头发往本站后端用于调用模型，请求结束即丢弃。
const STORAGE_KEY = 'velum.model'

const DEFAULT_BASE_URL = 'https://api.deepseek.com'

export function readModelSettings() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { apiKey: '', baseUrl: '', model: '' }
    const p = JSON.parse(raw)
    return {
      apiKey: typeof p.apiKey === 'string' ? p.apiKey : '',
      baseUrl: typeof p.baseUrl === 'string' ? p.baseUrl : '',
      model: typeof p.model === 'string' ? p.model : '',
    }
  } catch (e) {
    return { apiKey: '', baseUrl: '', model: '' }
  }
}

export function saveModelSettings(next) {
  const clean = {
    apiKey: String(next.apiKey || '').trim(),
    baseUrl: String(next.baseUrl || '').trim(),
    model: String(next.model || '').trim(),
  }
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(clean)) } catch (e) { /* 隐私模式下忽略 */ }
  return clean
}

export function clearModelSettings() {
  try { localStorage.removeItem(STORAGE_KEY) } catch (e) { /* ignore */ }
}

export function hasPersonalKey(settings = readModelSettings()) {
  return !!settings.apiKey
}

export function maskedKey(key) {
  if (!key) return ''
  if (key.length <= 8) return `${key.slice(0, 2)}••••`
  return `${key.slice(0, 3)}••••${key.slice(-4)}`
}

export function modelHeaders(settings = readModelSettings()) {
  const h = {}
  if (settings.apiKey) h['X-Velum-Api-Key'] = settings.apiKey
  if (settings.baseUrl) h['X-Velum-Base-Url'] = settings.baseUrl
  if (settings.model) h['X-Velum-Model'] = settings.model
  return h
}

export { DEFAULT_BASE_URL }
