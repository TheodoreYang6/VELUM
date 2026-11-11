import React, { useMemo, useState } from 'react'
import RetrievalPanel from './RetrievalPanel.jsx'

const TABS = [
  { id: 'all', name: '全部' },
  { id: 'major', name: '大阿卡纳' },
  { id: 'wands', name: '权杖' },
  { id: 'cups', name: '圣杯' },
  { id: 'swords', name: '宝剑' },
  { id: 'pentacles', name: '星币' },
]

export default function RecordPage({ spread, cards, useReversed, sceneId, question, busy, error, onBack, onSubmit }) {
  const [selections, setSelections] = useState({})
  const [activeSeq, setActiveSeq] = useState(null)
  const [tab, setTab] = useState('all')
  const [search, setSearch] = useState('')
  const [localError, setLocalError] = useState('')

  const used = useMemo(() => Object.values(selections).map((s) => s.card_id).filter(Boolean), [selections])
  const byId = useMemo(() => Object.fromEntries(cards.map((c) => [c.card_id, c])), [cards])
  const filtered = useMemo(() => cards.filter((c) => {
    const group = c.arcana === 'major' ? 'major' : c.suit
    if (tab !== 'all' && group !== tab) return false
    if (search.trim()) {
      const q = search.trim()
      return c.label.includes(q) || c.name.includes(q) || c.upright.includes(q)
    }
    return true
  }), [cards, tab, search])

  const pick = (seq, cardId) => {
    setSelections((prev) => ({ ...prev, [seq]: { card_id: cardId, reversed: false, note: '' } }))
    setActiveSeq(null)
    setLocalError('')
  }
  const setReversed = (seq, val) => {
    setSelections((prev) => ({ ...prev, [seq]: { ...(prev[seq] || {}), card_id: prev[seq]?.card_id, reversed: val, note: '' } }))
  }

  const submit = () => {
    const list = (spread?.positions || []).map((p) => ({
      seq: p.seq,
      card_id: selections[p.seq]?.card_id || '',
      reversed: useReversed ? !!selections[p.seq]?.reversed : false,
      note: '',
    }))
    if (list.some((x) => !x.card_id)) {
      setLocalError('仍有位置未录入牌面；请按现实中抽到的牌逐位填写。')
      return
    }
    setLocalError('')
    onSubmit(list)
  }

  const cardNames = Object.values(selections).filter((s) => s.card_id).flatMap((s) => {
    const c = byId[s.card_id]
    return c ? [c.name, c.label] : []
  })

  return (
    <>
      <div className="eyebrow">STEP IV · 录入牌面</div>
      <h1 className="page-title">把现实中的牌，如实记入系统</h1>
      <p className="page-desc">
        请按位置顺序，如实录入现实中抽到的牌。同一副牌不会重复；未启用逆位时按正位记录。系统不会替你抽牌。
      </p>

      <div className="panel">
        {(spread?.positions || []).map((p) => {
          const sel = selections[p.seq]
          const card = sel?.card_id ? byId[sel.card_id] : null
          return (
            <div key={p.seq}>
              <div className="record-row">
                <div>
                  <div className="pos-seq">{String(p.seq).padStart(2, '0')} · {p.name}</div>
                  <div className="pos-meaning">{p.meaning}</div>
                </div>
                <div>
                  <button className="btn" onClick={() => setActiveSeq(activeSeq === p.seq ? null : p.seq)}>
                    {card ? '更换牌面' : '选择牌面'}
                  </button>
                  {card && <div className="selected-card" style={{ marginTop: 8 }}>{card.label}{sel.reversed && useReversed ? ' · 逆位' : ''}</div>}
                </div>
                <div className="orientation">
                  <button className={`chip ${!sel?.reversed ? 'active' : ''}`} disabled={!sel?.card_id} onClick={() => setReversed(p.seq, false)}>正位</button>
                  <button className={`chip ${sel?.reversed ? 'active' : ''}`} disabled={!useReversed || !sel?.card_id} onClick={() => setReversed(p.seq, true)}>逆位</button>
                </div>
              </div>
              {activeSeq === p.seq && (
                <div className="card-picker">
                  <div className="picker-head">
                    <input className="input" placeholder="搜索牌名或关键词…" value={search} onChange={(e) => setSearch(e.target.value)} />
                    <button className="btn btn-ghost" onClick={() => setActiveSeq(null)}>收起</button>
                  </div>
                  <div className="picker-tabs">
                    {TABS.map((t) => (
                      <button key={t.id} className={`chip ${tab === t.id ? 'active' : ''}`} onClick={() => setTab(t.id)}>{t.name}</button>
                    ))}
                  </div>
                  <div className="picker-list">
                    {filtered.map((c) => (
                      <button
                        key={c.card_id}
                        className={`card-option ${sel?.card_id === c.card_id ? 'selected' : ''}`}
                        disabled={used.includes(c.card_id) && sel?.card_id !== c.card_id}
                        onClick={() => pick(p.seq, c.card_id)}
                        title={c.upright}
                      >
                        {c.label}
                      </button>
                    ))}
                  </div>
                  <div className="hint" style={{ marginTop: 10 }}>共 {filtered.length} 张可选 · 已录 {used.length} 张</div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      <RetrievalPanel stage="record" sceneId={sceneId} question={question} cardNames={cardNames} positionNames={(spread?.positions || []).map((p) => p.name)} title="本环节参考的规范" />

      {(localError || error) && <div className="notice warn" style={{ marginTop: 16 }}>{localError || '暂时无法提交，请稍后重试'}</div>}
      {busy && (
        <div className="notice" style={{ marginTop: 16 }}>
          <h4>正在生成最终评定</h4>
          正在整理牌面并生成最终评定，约需 5–10 秒。请勿重复点击或关闭页面。
        </div>
      )}
      <div className="btn-row">
        <button className="btn btn-ghost" onClick={onBack}>← 返回仪式</button>
        <button className="btn btn-primary" disabled={busy} onClick={submit}>{busy ? '正在生成评定…（约 5–10 秒）' : '录入完成 · 生成最终评定 →'}</button>
      </div>
    </>
  )
}
