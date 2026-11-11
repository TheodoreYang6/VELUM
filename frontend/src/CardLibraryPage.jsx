import React, { useMemo, useState } from 'react'

export const SUIT_META = {
  major: { label: '大阿卡纳', glyph: '✧' },
  wands: { label: '权杖', glyph: '│' },
  cups: { label: '圣杯', glyph: '◡' },
  swords: { label: '宝剑', glyph: '△' },
  pentacles: { label: '星币', glyph: '◇' },
}

export const groupOf = (cardId = '') => (cardId.startsWith('major') ? 'major' : cardId.split('-')[0])

const FILTERS = [
  { id: 'all', label: '全部' },
  { id: 'major', label: '大阿卡纳' },
  { id: 'wands', label: '权杖' },
  { id: 'cups', label: '圣杯' },
  { id: 'swords', label: '宝剑' },
  { id: 'pentacles', label: '星币' },
]

export default function CardLibraryPage({ library, viewed, onOpenCard }) {
  const [filter, setFilter] = useState('all')
  const [q, setQ] = useState('')

  const list = useMemo(() => library.filter((c) => {
    if (filter !== 'all' && groupOf(c.card_id) !== filter) return false
    if (!q.trim()) return true
    const text = `${c.name} ${c.english} ${c.keywords} ${c.upright}`.toLowerCase()
    return text.includes(q.trim().toLowerCase())
  }), [library, filter, q])

  const total = library.length || 78
  const progress = Math.round((viewed.length / total) * 100)

  return (
    <>
      <div className="eyebrow">STEP VII · 牌库</div>
      <h1 className="page-title">七十八张牌的图鉴</h1>
      <p className="page-desc">
        每一张牌的图像、象征、正逆位与场景提示都收录于此。点开任意一张，可查阅完整解读；也可在解读结果中点击牌名直接回到这里。
      </p>

      <div className="library-progress">
        <div className="library-progress-head">
          <span className="field-label" style={{ margin: 0 }}>已 阅 {viewed.length} / {total}</span>
          <span className="hint">翻开过的牌会留下金色印记</span>
        </div>
        <div className="library-progress-track"><span style={{ width: `${progress}%` }} /></div>
      </div>

      <div className="library-toolbar">
        <div className="chip-row">
          {FILTERS.map((f) => (
            <button key={f.id} className={`chip ${filter === f.id ? 'active' : ''}`} onClick={() => setFilter(f.id)}>{f.label}</button>
          ))}
        </div>
        <input
          className="input library-search"
          placeholder="搜索牌名、英文或关键词…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </div>

      <div className="hint" style={{ margin: '14px 0 18px' }}>当前显示 {list.length} 张</div>

      <div className="library-grid">
        {list.map((c) => {
          const meta = SUIT_META[groupOf(c.card_id)] || SUIT_META.major
          const seen = viewed.includes(c.card_id)
          return (
            <button
              key={c.card_id}
              className={`library-card tone-${groupOf(c.card_id)} ${seen ? 'viewed' : ''}`}
              onClick={() => onOpenCard(c.card_id)}
            >
              <div className="lc-frame">
                <div className="lc-corner lc-corner-a" />
                <div className="lc-corner lc-corner-b" />
                <div className="lc-top">
                  <span className="lc-num">{c.number}</span>
                  <span className="lc-suit">{meta.label}</span>
                </div>
                <div className="lc-art">
                  <img
                    className="lc-art-img"
                    src={`/cards/${c.card_id}.jpg`}
                    alt=""
                    loading="lazy"
                    onError={(e) => {
                      e.currentTarget.style.display = 'none'
                      e.currentTarget.parentElement.classList.add('no-img')
                    }}
                  />
                  <div className="lc-art-ring" />
                  <span className="lc-art-glyph">{meta.glyph}</span>
                </div>
                <div className="lc-name">{c.name}</div>
                <div className="lc-english">{c.english}</div>
                <div className="lc-keywords">{c.keywords}</div>
              </div>
              {seen && <span className="lc-seen">已阅</span>}
            </button>
          )
        })}
      </div>
    </>
  )
}
