import React, { useEffect, useMemo, useState } from 'react'
import { api } from './api.js'
import DrawRitualModal from './DrawRitualModal.jsx'

export default function DrawPage({ spreads, spreadId, sceneId, sessionId, useReversed, onSpread, onBack, onConfirm }) {
  const [modes, setModes] = useState([])
  const [mode, setMode] = useState('timeline')
  const [open, setOpen] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.drawModes().then((m) => {
      setModes(m)
      const matched = m.find((x) => x.spreads.includes(spreadId))
      if (matched) setMode(matched.id)
    }).catch((e) => setError(e.message))
  }, [])

  const activeMode = modes.find((m) => m.id === mode)
  const currentSpread = spreads.find((s) => s.spread_id === spreadId)
  const available = useMemo(
    () => spreads.filter((s) => (activeMode?.spreads || []).includes(s.spread_id)),
    [spreads, activeMode],
  )

  const chooseMode = (m) => {
    setMode(m.id)
    setOpen(false)
    if (!m.spreads.includes(spreadId) && m.spreads.length) onSpread(m.spreads[0])
  }

  return (
    <>
      <div className="eyebrow">STEP IV · 线上抽卡</div>
      <h1 className="page-title">在牌桌前，完成一次完整的抽卡</h1>
      <p className="page-desc">
        抽卡仪式在独立的全屏界面中进行：<strong style={{ color: 'var(--gold-bright)', fontWeight: 500 }}>洗牌 → 切牌 → 一张一张抽出 → 逐张翻开</strong>。
        可用鼠标在牌桌上搓洗牌面、感应倾斜，也可用空格与键盘推进每一步。线上抽卡仅用于练习与演示，不替代现实中的洗牌与抽牌仪式。
      </p>

      <h2 className="section-title">选择抽卡模式</h2>
      <div className="draw-mode-grid">
        {modes.map((m) => (
          <button key={m.id} className={`draw-mode ${mode === m.id ? 'active' : ''}`} onClick={() => chooseMode(m)}>
            <div className="draw-mode-sigil">{m.id === 'single' ? 'I' : m.id === 'timeline' ? 'III' : m.id === 'cross' ? 'V' : 'X'}</div>
            <div className="draw-mode-name">{m.name}</div>
            <div className="draw-mode-desc">{m.description}</div>
            <div className="draw-mode-meta">{m.card_range} · {m.caption}</div>
          </button>
        ))}
      </div>

      {available.length > 0 && (
        <div className="panel" style={{ marginTop: 18 }}>
          <div className="field-label">该模式可用牌阵</div>
          <div className="chip-row">
            {available.map((s) => (
              <button key={s.spread_id} className={`chip ${spreadId === s.spread_id ? 'active' : ''}`} onClick={() => { onSpread(s.spread_id); setOpen(false) }}>
                {s.spread_id} · {s.name}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="notice" style={{ marginTop: 18 }}>
        本次场景「{sceneId}」· 牌阵「{currentSpread?.name || spreadId}」· 逆位{useReversed ? '启用' : '不启用'}。仪式动效只影响呈现，不改变牌面结果。
      </div>

      <div className="draw-entry">
        <div className="draw-entry-ring"><span>◇</span></div>
        <div className="draw-entry-title">牌 桌 已 备 妥</div>
        <p>进入后将开始洗牌；每次进入仪式都会重新抽取一副牌。</p>
        <button className="btn btn-primary" disabled={!activeMode} onClick={() => setOpen(true)}>进入抽卡仪式 →</button>
      </div>

      {error && <div className="notice warn" style={{ marginTop: 16 }}>{error}</div>}

      <div className="btn-row">
        <button className="btn btn-ghost" onClick={onBack}>← 返回仪式</button>
        <span className="hint">键盘：空格推进 · C 切牌 · Esc 退出仪式</span>
      </div>

      <DrawRitualModal
        open={open}
        onClose={() => setOpen(false)}
        mode={activeMode}
        spread={currentSpread}
        spreadId={spreadId}
        useReversed={useReversed}
        sessionId={sessionId}
        onConfirm={onConfirm}
      />
    </>
  )
}
