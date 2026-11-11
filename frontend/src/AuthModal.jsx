import React, { useState, useEffect } from 'react'
import { api } from './api.js'

export default function AuthModal({ open, onClose, onLogin }) {
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ username: '', password: '', display: '' })
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (open) {
      setMsg('')
      setForm({ username: '', password: '', display: '' })
    }
  }, [open, mode])

  if (!open) return null

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setMsg('')
    try {
      const res = mode === 'login'
        ? await api.authLogin(form.username, form.password)
        : await api.authRegister(form.username, form.password, form.display)
      onLogin(res.user)
    } catch (err) {
      setMsg(err.message || '操作未成功，请稍后重试')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-overlay" onClick={onClose}>
      <div className="auth-modal" onClick={(e) => e.stopPropagation()}>
        <button className="auth-close" onClick={onClose} aria-label="关闭">×</button>
        <div className="auth-head">
          <span className="auth-seal">✦</span>
          <span>帷间 · 登录</span>
        </div>
        <div className="auth-tabs">
          <button className={`auth-tab ${mode === 'login' ? 'active' : ''}`} onClick={() => setMode('login')}>登录</button>
          <button className={`auth-tab ${mode === 'register' ? 'active' : ''}`} onClick={() => setMode('register')}>注册账号</button>
        </div>
        <form className="auth-form" onSubmit={submit}>
          <input
            className="auth-input" placeholder="用户名（至少 3 个字符）"
            value={form.username} autoComplete="username"
            onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
          />
          <input
            className="auth-input" type="password" placeholder="密码（至少 6 个字符）"
            value={form.password} autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
          />
          {mode === 'register' && (
            <input
              className="auth-input" placeholder="昵称（可选，留空同用户名）"
              value={form.display} autoComplete="nickname"
              onChange={(e) => setForm((f) => ({ ...f, display: e.target.value }))}
            />
          )}
          <button className="btn btn-primary auth-submit" type="submit" disabled={busy}>
            {busy ? '处理中…' : (mode === 'login' ? '登录' : '注册并登录')}
          </button>
          {msg && <div className="auth-msg">{msg}</div>}
        </form>
        <p className="auth-foot">规范文档即系统唯一事实源；登录后可维护占卜规范。</p>
      </div>
    </div>
  )
}
