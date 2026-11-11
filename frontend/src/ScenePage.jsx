import React from 'react'

const GLYPH = {
  love: '缘', career: '业', study: '学', general: '常', choice: '择',
  cycle: '轮', self: '己', relation: '伦', create: '造', place: '居', wellbeing: '息',
}

export default function ScenePage({ scenes, spreads, sceneId, spreadId, useReversed, onScene, onSpread, onReversed, onNext }) {
  const scene = scenes.find((s) => s.scene_id === sceneId)
  const recommended = scene?.recommended_ids || []
  const suggested = spreads.filter((s) => recommended.includes(s.spread_id))
  const others = spreads.filter((s) => !recommended.includes(s.spread_id))

  return (
    <>
      <div className="eyebrow">STEP I · 择定场景</div>
      <h1 className="page-title">今夜所问，属于哪一支脉络</h1>
      <p className="page-desc">
        场景会决定推荐的问题、适合的牌阵，以及解读时的关注方向；牌义本身不会改变，也不会预设结论。
      </p>

      <div className="grid grid-3">
        {scenes.map((s) => (
          <button
            key={s.scene_id}
            className={`scene-card ${sceneId === s.scene_id ? 'selected' : ''}`}
            onClick={() => onScene(s.scene_id)}
          >
            <div className="scene-glyph">{GLYPH[s.scene_id] || '〇'}</div>
            <div className="scene-name">{s.name}</div>
            <div className="scene-topics">{s.topics}</div>
            <div className="scene-focus">侧重 · {s.focus}</div>
          </button>
        ))}
      </div>

      {scene && (
        <>
          <h2 className="section-title">为后续占卜做准备</h2>
          <div className="panel">
            <div className="field-label">推荐牌阵</div>
            <div className="chip-row">
              {suggested.map((s) => (
                <button key={s.spread_id} className={`chip ${spreadId === s.spread_id ? 'active' : ''}`} onClick={() => onSpread(s.spread_id)}>
                  {s.name}（{s.card_count} 张）
                </button>
              ))}
            </div>
            <div className="field-label" style={{ marginTop: 22 }}>其余牌阵</div>
            <div className="chip-row">
              {others.map((s) => (
                <button key={s.spread_id} className={`chip ${spreadId === s.spread_id ? 'active' : ''}`} onClick={() => onSpread(s.spread_id)}>
                  {s.name}（{s.card_count} 张）
                </button>
              ))}
            </div>
            <div style={{ marginTop: 26, paddingTop: 22, borderTop: '1px solid var(--line-soft)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 20, flexWrap: 'wrap' }}>
              <label className="toggle">
                <input type="checkbox" checked={useReversed} onChange={(e) => onReversed(e.target.checked)} />
                本次启用逆位解读
              </label>
              <span className="hint">请在洗牌前确定，仪式开始后不再更改</span>
            </div>
          </div>
          <div className="notice">
            <strong>本次已确定：</strong> 场景「{scene.name}」 · 牌阵「{spreads.find((s) => s.spread_id === spreadId)?.name || '未选'}」 · 逆位{useReversed ? '启用' : '停用'}。
            确定后，后续每一步都会依照这次的选择进行。
          </div>
        </>
      )}

      <div className="btn-row">
        <button className="btn btn-primary" disabled={!sceneId || !spreadId} onClick={onNext}>进入立题 →</button>
        <span className="hint">场景与牌阵均可在此后返回修改</span>
      </div>
    </>
  )
}
