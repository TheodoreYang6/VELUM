import React, { useEffect, useState } from 'react'
import { api } from './api.js'
import {
  readModelSettings, saveModelSettings, clearModelSettings,
  hasPersonalKey, maskedKey, DEFAULT_BASE_URL,
} from './modelSettings.js'
import VelumSigil from './VelumSigil.jsx'

export default function ModelSettingsModal({ open, onClose, onChanged }) {
  const [form, setForm] = useState({ apiKey: '', baseUrl: '', model: '' })
  const [showKey, setShowKey] = useState(false)
  const [busy, setBusy] = useState(false)
  const [probeMsg, setProbeMsg] = useState('')
  const [status, setStatus] = useState(null)
  const [saved, setSaved] = useState({ apiKey: '', baseUrl: '', model: '' })

  useEffect(() => {
    if (!open) return
    const s = readModelSettings()
    setSaved(s)
    setForm({ apiKey: '', baseUrl: s.baseUrl || '', model: s.model || '' })
    setShowKey(false)
    setProbeMsg('')
    setStatus(null)
    api.agentStatus().then(setStatus).catch(() => setStatus(null))
  }, [open])

  if (!open) return null

  const keyToUse = form.apiKey.trim() || saved.apiKey
  const hasKey = !!keyToUse

  const persist = (next) => {
    const stored = saveModelSettings(next)
    setSaved(stored)
    setForm((p) => ({ ...p, apiKey: '' }))
    onChanged?.(stored)
  }

  const save = (e) => {
    e.preventDefault()
    persist({ apiKey: keyToUse, baseUrl: form.baseUrl, model: form.model })
    setProbeMsg('已保存到本浏览器')
  }

  const clear = () => {
    clearModelSettings()
    const empty = { apiKey: '', baseUrl: '', model: '' }
    setSaved(empty)
    setForm(empty)
    onChanged?.(empty)
    setProbeMsg('已清除本浏览器保存的凭据')
  }

  const probe = async () => {
    if (!keyToUse) { setProbeMsg('请先填写 API Key'); return }
    setBusy(true)
    setProbeMsg('')
    try {
      // 直接用表单值发一次探测，不写 localStorage；失败也不会残留凭据
      const res = await api.agentProbe({
        apiKey: keyToUse, baseUrl: form.baseUrl, model: form.model,
      })
      if (res.ok) setProbeMsg(`连接正常 · ${res.active_model || res.configured_model || '模型可用'}`)
      else setProbeMsg('连接未成功，请检查 Key 与接口地址')
    } catch (e) {
      setProbeMsg('暂时无法检测，请稍后重试')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-overlay" onClick={onClose}>
      <div className="auth-modal model-modal" onClick={(e) => e.stopPropagation()}>
        <button className="auth-close" onClick={onClose} aria-label="关闭">×</button>
        <div className="auth-head">
          <span className="auth-seal">✦</span>
          <span>帷间 · 模型连接</span>
        </div>

        <div className="model-sigil"><VelumSigil /></div>

        <p className="model-lead">
          填入<strong>你自己的</strong> API Key。每位使用者各用各的额度，互不相干。
        </p>

        <div className={`model-state ${hasKey ? 'on' : ''}`}>
          <span className="model-state-dot" />
          {hasKey
            ? `本浏览器已配置 · ${maskedKey(keyToUse)}`
            : '本浏览器尚未配置 · 智能润色将回退为规则稿'}
        </div>

        <form className="auth-form" onSubmit={save}>
          <label className="model-label" htmlFor="ms-key">API Key</label>
          <div className="model-keyrow">
            <input
              id="ms-key"
              className="auth-input"
              type={showKey ? 'text' : 'password'}
              autoComplete="off"
              spellCheck="false"
              placeholder={saved.apiKey ? `已保存 ${maskedKey(saved.apiKey)}，留空表示不修改` : 'sk-…'}
              value={form.apiKey}
              onChange={(e) => setForm((p) => ({ ...p, apiKey: e.target.value }))}
            />
            <button type="button" className="model-eye" onClick={() => setShowKey((v) => !v)}>
              {showKey ? '隐藏' : '显示'}
            </button>
          </div>

          <label className="model-label" htmlFor="ms-base">接口地址 <span>可选</span></label>
          <input
            id="ms-base"
            className="auth-input"
            placeholder={DEFAULT_BASE_URL}
            autoComplete="off"
            value={form.baseUrl}
            onChange={(e) => setForm((p) => ({ ...p, baseUrl: e.target.value }))}
          />

          <label className="model-label" htmlFor="ms-model">模型名称 <span>可选</span></label>
          <input
            id="ms-model"
            className="auth-input"
            placeholder="留空则使用服务端默认模型"
            autoComplete="off"
            value={form.model}
            onChange={(e) => setForm((p) => ({ ...p, model: e.target.value }))}
          />

          <div className="model-actions">
            <button type="button" className="btn" onClick={probe} disabled={busy}>
              {busy ? '检测中…' : '测试连接'}
            </button>
            <button type="submit" className="btn btn-primary">保存</button>
          </div>
        </form>

        {probeMsg && <div className="auth-msg model-msg">{probeMsg}</div>}

        <div className="model-note">
          <div className="model-note-title">关于安全</div>
          <p>
            Key 只保存在<strong>当前浏览器</strong>，不会写入服务器数据库或日志。
            它会在每次请求时临时传给本站后端用于调用模型，请求结束即丢弃；
            其他访客无法取用你的 Key，你也不会用到别人的。
          </p>
          <p>
            若你把站点部署到公网，请保持服务端的 <code>ALLOW_SERVER_KEY=false</code>（默认），
            这样服务器自己的 Key 不会被匿名访客消耗。
          </p>
        </div>

        <div className="model-foot">
          {status?.server_key_shared && (
            <span className="model-warn">当前服务端已开启共享 Key</span>
          )}
          <button className="model-clear" onClick={clear} disabled={!hasPersonalKey(saved)}>清除凭据</button>
        </div>
      </div>
    </div>
  )
}
