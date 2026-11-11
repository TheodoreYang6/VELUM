import React, { useEffect } from 'react'
import { SUIT_META, groupOf } from './CardLibraryPage.jsx'

export default function CardDetailModal({ card, library, onClose, onShift, onViewed }) {
  useEffect(() => {
    if (card) onViewed(card.card_id)
  }, [card?.card_id])

  useEffect(() => {
    if (!card) return undefined
    const handler = (e) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowRight') onShift(1)
      if (e.key === 'ArrowLeft') onShift(-1)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [card, onClose, onShift])

  if (!card) return null
  const meta = SUIT_META[groupOf(card.card_id)] || SUIT_META.major
  const index = library.findIndex((c) => c.card_id === card.card_id)
  const keywords = (card.keywords || '').split(/\s*\/\s*/).filter(Boolean)

  return (
    <div className="card-detail-overlay" role="dialog" aria-modal="true" aria-label={`${card.name} 牌义详解`} onClick={onClose}>
      <div className={`card-detail-frame tone-${groupOf(card.card_id)}`} onClick={(e) => e.stopPropagation()}>
        <button className="cd-close" onClick={onClose} aria-label="关闭">×</button>

        <div className="cd-left">
          <div className="cd-big-card">
            <div className="cd-big-frame">
              <div className="cd-big-corner cd-big-corner-a" />
              <div className="cd-big-corner cd-big-corner-b" />
              <div className="cd-big-top">
                <span>{card.number}</span><span>{meta.label}</span>
              </div>
              <div className="cd-big-art">
                <img
                  className="cd-big-art-img"
                  src={`/cards/${card.card_id}.jpg`}
                  alt=""
                  onError={(e) => {
                    e.currentTarget.style.display = 'none'
                    e.currentTarget.parentElement.classList.add('no-img')
                  }}
                />
                <div className="cd-big-ring" />
                <div className="cd-big-ring inner" />
                <span className="cd-big-glyph">{meta.glyph}</span>
              </div>
              <div className="cd-big-name">{card.name}</div>
              <div className="cd-big-english">{card.english}</div>
            </div>
          </div>
          <div className="cd-nav">
            <button className="btn btn-ghost" onClick={() => onShift(-1)}>← 上一张</button>
            <span className="hint">{index + 1} / {library.length || 78}</span>
            <button className="btn btn-ghost" onClick={() => onShift(1)}>下一张 →</button>
          </div>
          <div className="hint" style={{ textAlign: 'center', marginTop: 8 }}>← → 切换 · Esc 关闭</div>
        </div>

        <div className="cd-right">
          <div className="eyebrow">牌 义 图 鉴</div>
          <h2 className="cd-title">{card.name}</h2>
          <div className="cd-english">{card.english}</div>
          <div className="cd-meta-line">
            <span>{meta.label}</span><span>编号 {card.number}</span><span>{card.correspondence}</span>
          </div>
          <div className="cd-chips">
            {keywords.map((k, i) => <span className="cd-chip" key={i}>{k}</span>)}
          </div>

          <section className="cd-section">
            <h3>牌 面 图 像</h3>
            <p>{card.imagery}</p>
          </section>

          <div className="cd-two">
            <section className="cd-section">
              <h3>正 位</h3>
              <p>{card.upright}</p>
            </section>
            <section className="cd-section">
              <h3>逆 位</h3>
              <p>{card.reversed}</p>
            </section>
          </div>

          <section className="cd-section">
            <h3>象 征</h3>
            <p>{card.symbolism}</p>
          </section>

          <section className="cd-section">
            <h3>场 景 提 示</h3>
            <div className="cd-scenes">
              <div><span>姻缘</span><p>{card.love}</p></div>
              <div><span>工作</span><p>{card.career}</p></div>
              <div><span>升学</span><p>{card.study}</p></div>
            </div>
          </section>

          <div className="cd-source">依据韦特体系原典与 RWS 通行解读整理</div>
        </div>
      </div>
    </div>
  )
}
