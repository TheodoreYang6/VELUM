import React, { useEffect, useState } from 'react'
import { api } from './api.js'
import { ruleLabel, FRIENDLY_RETRY } from './labels.js'

export default function RulesPage({ me, onShowLogin, onLogout }) {
  const [rules, setRules] = useState([])
  const [active, setActive] = useState(null)
  const [content, setContent] = useState('')
  const [health, setHealth] = useState(null)
  const [status, setStatus] = useState('')
  const [busy, setBusy] = useState(false)
  const [agentInfo, setAgentInfo] = useState(null)
  const [probe, setProbe] = useState(null)
  const [probing, setProbing] = useState(false)

  const isAuthed = !!me

  const load = async () => {
    const [list, h, info] = await Promise.all([
      api.rules(), api.health(), api.agentStatus(),
    ])
    setRules(list)
    setHealth(h)
    setAgentInfo(info)
    if (list.length) {
      const id = active || list[0].doc_id
      const doc = await api.rule(id)
      setActive(id)
      setContent(doc.content)
    }
  }

  useEffect(() => {
    load().catch(() => setStatus(FRIENDLY_RETRY))
  }, [])

  const open = async (id) => {
    setStatus('')
    try {
      const doc = await api.rule(id)
      setActive(id)
      setContent(doc.content)
    } catch (e) {
      setStatus('暂时无法打开，请稍后重试')
    }
  }

  const runProbe = async () => {
    setProbing(true)
    try {
      setProbe(await api.agentProbe())
      setAgentInfo(await api.agentStatus())
    } catch (e) {
      setProbe({ ok: false })
    } finally {
      setProbing(false)
    }
  }

  const save = async () => {
    setBusy(true)
    setStatus('')
    try {
      await api.saveRule(active, content)
      setStatus('已保存，界面内容已更新')
      await load()
    } catch (e) {
      setStatus(e.message || '保存未成功，请稍后重试')
    } finally {
      setBusy(false)
    }
  }

  const rebuild = async () => {
    setBusy(true)
    try {
      await api.rebuild()
      setStatus('规范库已更新')
    } catch (e) {
      setStatus(e.message || '更新未成功，请稍后重试')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <div className="eyebrow">STEP VIII · 规范维护</div>
      <h1 className="page-title">维护占卜规范</h1>
      <p className="page-desc">
        牌义、牌阵、仪式与解读依据都收录于此。修改并保存后，界面中的场景、位置与选牌内容会自动更新。
      </p>

      {health && (
        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="field-label">规 范 库 状 态</div>
          <div className="kv">
            <dt>状态</dt><dd>{health.ok ? '已就绪' : '暂不可用'}</dd>
            <dt>牌组</dt><dd>韦特体系 · 78 张</dd>
          </div>
        </div>
      )}

      {agentInfo && (
        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="field-label">智 能 解 读</div>
          <div className="kv">
            <dt>状态</dt><dd>{agentInfo.enabled ? '已开启' : '已关闭'}</dd>
            <dt>连接</dt><dd>{probe ? (probe.ok ? '正常' : '未连接') : (agentInfo.key_configured ? '待检测' : '未配置')}</dd>
          </div>
          <div className="agent-status-row">
            <button className="btn" disabled={probing} onClick={runProbe}>{probing ? '检测中…' : '检测连接'}</button>
            <span className="hint">关闭时仍可按内置规范生成参考内容</span>
          </div>
          {probe && (
            <div className={probe.ok ? 'notice' : 'notice warn'} style={{ marginTop: 12 }}>
              {probe.ok ? '连接正常，智能解读可用' : '暂时无法连接，请稍后重试'}
            </div>
          )}
        </div>
      )}

      {!isAuthed && (
        <div className="auth-box auth-box-inline">
          <div className="auth-head">
            <span className="auth-seal">✦</span>
            <span>维护规范需先登录</span>
          </div>
          <p className="auth-foot">登录后即可在线编辑并保存占卜规范文档（规则即系统唯一事实源）。</p>
          <button className="btn btn-primary auth-submit" onClick={onShowLogin}>前往登录</button>
        </div>
      )}

      {isAuthed && (
        <div className="auth-bar">
          <span className="auth-bar-user">已登录 · {me.display}</span>
          <button className="sidebar-replay" onClick={onLogout}>退出登录</button>
        </div>
      )}

      <div className="rules-layout">
        <div>
          <div className="field-label">规范清单</div>
          <div className="rule-list">
            {rules.map((r) => (
              <button key={r.doc_id} className={`rule-btn ${active === r.doc_id ? 'active' : ''}`} onClick={() => open(r.doc_id)}>
                {r.title}
              </button>
            ))}
          </div>
          <div className="hint" style={{ marginTop: 16, lineHeight: 1.8 }}>
            编辑后点击「保存并生效」，界面内容会随之更新。<br />
            · 修改牌阵时请保持位置表格完整<br />
            · 伦理边界适用于所有环节
          </div>
        </div>
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10, gap: 12 }}>
            <div className="field-label" style={{ margin: 0 }}>{ruleLabel(active)} · 原文</div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn" disabled={busy || !isAuthed} onClick={rebuild}>刷新规范库</button>
              <button className="btn btn-primary" disabled={busy || !active || !isAuthed} onClick={save}>{busy ? '处理中…' : '保存并生效'}</button>
            </div>
          </div>
          <textarea
            className="textarea rule-editor" value={content} spellCheck={false}
            disabled={!isAuthed}
            onChange={(e) => setContent(e.target.value)}
          />
          {!isAuthed && <div className="auth-lock">登录后即可在此编辑并保存规范文档。</div>}
          {status && <div className={status.includes('未成功') || status.includes('需') ? 'notice warn' : 'notice'} style={{ marginTop: 12 }}>{status}</div>}
        </div>
      </div>
    </>
  )
}
