import { modelHeaders } from './modelSettings.js'

const BASE = '/api'

async function request(path, options = {}) {
  const { headers: extraHeaders, ...rest } = options
  const res = await fetch(BASE + path, {
    credentials: 'include',
    ...rest,
    headers: {
      'Content-Type': 'application/json',
      ...modelHeaders(),
      ...(extraHeaders || {}),
    },
  })
  let data = {}
  try { data = await res.json() } catch (e) { /* ignore non-json */ }
  if (!res.ok) {
    const msg = (data && data.detail) ? data.detail : '暂时无法完成，请稍后重试'
    throw new Error(msg)
  }
  return data
}

const body = (payload) => ({ method: 'POST', body: JSON.stringify(payload) })

export const api = {
  health: () => request('/health'),
  scenes: () => request('/scenes'),
  spreads: () => request('/spreads'),
  cards: () => request('/cards'),
  ritual: () => request('/ritual'),
  routes: () => request('/routes'),
  checkQuestion: (payload) => request('/question/check', body(payload)),
  retrieve: (payload) => request('/retrieve', body(payload)),
  createSession: (payload) => request('/sessions', body(payload)),
  saveCards: (id, cards) => request(`/sessions/${id}/cards`, body({ cards })),
  reading: (id) => request(`/sessions/${id}/reading`, body({})),
  session: (id) => request(`/sessions/${id}`),
  sessions: () => request('/sessions'),
  rules: () => request('/rules'),
  rule: (id) => request(`/rules/${id}`),
  saveRule: (id, content) => request(`/rules/${id}`, { method: 'PUT', body: JSON.stringify({ content }) }),
  rebuild: () => request('/index/rebuild', body({})),
  agentStatus: () => request('/agent/status'),
  // 允许用「表单里尚未保存」的凭据做一次探测，不经过 localStorage
  agentProbe: (creds) => request('/agent/probe', {
    ...body({}),
    ...(creds ? {
      headers: {
        'X-Velum-Api-Key': creds.apiKey || '',
        'X-Velum-Base-Url': creds.baseUrl || '',
        'X-Velum-Model': creds.model || '',
      },
    } : {}),
  }),
  agentRun: (payload) => request('/agent/run', body(payload)),
  agentTraces: () => request('/agent/traces'),
  followupHistory: (id) => request(`/sessions/${id}/followup`),
  followupAsk: (id, question) => request(`/sessions/${id}/followup`, body({ question })),
  followupClear: (id) => request(`/sessions/${id}/followup`, { method: 'DELETE' }),
  cardLibrary: () => request('/card-library'),
  cardDetail: (id) => request(`/card-library/${id}`),
  drawModes: () => request('/draw/modes'),
  onlineDraw: (payload) => request('/draw', body(payload)),
  authMe: () => request('/auth/me'),
  authLogin: (username, password) => request('/auth/login', body({ username, password })),
  authRegister: (username, password, display) => request('/auth/register', body({ username, password, display })),
  authLogout: () => request('/auth/logout', { method: 'POST' }),
}
