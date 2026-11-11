import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from './api.js'
import VelumSigil from './VelumSigil.jsx'

const LAYOUT_FULL = {
  halo: [{ x: 50, y: 48 }],
  timeline: [{ x: 20, y: 48 }, { x: 50, y: 48 }, { x: 80, y: 48 }],
  cross: [
    { x: 50, y: 50 }, { x: 50, y: 22 }, { x: 50, y: 76 },
    { x: 20, y: 50 }, { x: 80, y: 50 },
  ],
  celtic: [
    { x: 17, y: 22 }, { x: 34, y: 22 },
    { x: 17, y: 47 }, { x: 34, y: 47 },
    { x: 17, y: 72 }, { x: 34, y: 72 },
    { x: 76, y: 18 }, { x: 76, y: 37 }, { x: 76, y: 56 }, { x: 76, y: 74 },
  ],
}

function drawSlotLayout(i, total) {
  const cols = Math.min(total, 6)
  const rows = Math.ceil(total / cols)
  return {
    x: 12 + (i % cols) * (76 / Math.max(cols - 1, 1)),
    y: rows === 1 ? 30 : (i < cols ? 24 : 44),
  }
}

function gridLayoutFull(i, total) {
  const cols = Math.ceil(Math.sqrt(total))
  const rows = Math.ceil(total / cols)
  return {
    x: 14 + (i % cols) * (72 / Math.max(cols - 1, 1)),
    y: 22 + Math.floor(i / cols) * (52 / Math.max(rows - 1, 1)),
  }
}

const STEPS = [
  { id: 'shuffle', label: '洗牌' },
  { id: 'cut', label: '切牌' },
  { id: 'draw', label: '扇形选牌' },
  { id: 'complete', label: '牌阵完成' },
]

const FAN = { X: 36, Y0: 70, YARC: 12, DEG: 38 }

export default function DrawRitualModal({
  open, onClose, mode, spread, spreadId, useReversed, sessionId, onConfirm,
}) {
  const [phase, setPhase] = useState('intro')
  const [energy, setEnergy] = useState(0)
  const [dragging, setDragging] = useState(false)
  const [cutCount, setCutCount] = useState(0)
  const [result, setResult] = useState(null)
  const [picks, setPicks] = useState([])
  const [taken, setTaken] = useState([])
  const [flipped, setFlipped] = useState([])
  const [focusIndex, setFocusIndex] = useState(39)
  const [hoverIndex, setHoverIndex] = useState(null)
  const [kbActive, setKbActive] = useState(false)
  const [selected, setSelected] = useState(null)
  const [confirming, setConfirming] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const stageRef = useRef(null)
  const lastPos = useRef({ x: 0, y: 0 })
  const energyTick = useRef(0)

  const total = result?.positions?.length || 0
  const deckSize = result?.deck?.length || 0
  // 洗牌能量满格：进入收拢 / 自动推进状态，此间不再接受洗牌输入。
  const shuffleDone = phase === 'shuffle' && energy >= 100

  const layoutFull = useMemo(() => {
    if (!result) return []
    const preset = LAYOUT_FULL[result.animation] || []
    return result.positions.map((_, i) => preset[i] || gridLayoutFull(i, result.positions.length))
  }, [result])

  const layoutDraw = useMemo(
    () => (result ? result.positions.map((_, i) => drawSlotLayout(i, result.positions.length)) : []),
    [result],
  )

  const fanGeom = useMemo(() => {
    if (!deckSize) return []
    return Array.from({ length: deckSize }, (_, i) => {
      const u = deckSize > 1 ? (i / (deckSize - 1) - 0.5) * 2 : 0
      return {
        xPct: 50 + u * FAN.X,
        yPct: FAN.Y0 + u * u * FAN.YARC,
        deg: u * FAN.DEG,
      }
    })
  }, [deckSize])

  const deckMap = useMemo(
    () => Object.fromEntries((result?.deck_details || []).map((d) => [d.card_id, d])),
    [result],
  )

  useEffect(() => {
    if (!open) return undefined
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const onUp = () => setDragging(false)
    window.addEventListener('mouseup', onUp)
    return () => {
      document.body.style.overflow = previous
      window.removeEventListener('mouseup', onUp)
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    setPhase('intro'); setEnergy(0); setDragging(false); setCutCount(0)
    setResult(null); setPicks([]); setTaken([])
    setFlipped([]); setFocusIndex(39); setHoverIndex(null); setKbActive(false); setSelected(null)
    setConfirming(false); setError('')
    setLoading(true)
    api.onlineDraw({
      spread_id: spreadId, mode: mode?.id || '', use_reversed: useReversed, session_id: sessionId,
    }).then((r) => {
      setResult(r)
      setFocusIndex(Math.floor((r.deck?.length || 78) / 2))
      setHoverIndex(null)
      setKbActive(false)
      setLoading(false)
    }).catch(() => { setError('暂时无法准备牌叠，请退出后重试'); setLoading(false) })
  }, [open, spreadId, mode?.id, useReversed, sessionId, attempt])

  // 洗牌达到 100% 后停留片刻，让牌叠收拢，再自动推进到「切牌」。
  // 关闭 / 重试 / 用户提前手动推进都会触发 cleanup，不会留下悬挂的定时器。
  useEffect(() => {
    if (!open || phase !== 'shuffle' || energy < 100) return undefined
    const t = window.setTimeout(() => {
      setDragging(false)
      setPhase('cut')
    }, 900)
    return () => window.clearTimeout(t)
  }, [open, phase, energy])

  const nextUntaken = (from) => {
    for (let k = 1; k <= deckSize; k += 1) {
      const j = (from + k) % deckSize
      if (!taken.includes(j)) return j
    }
    return from
  }

  const pickCard = useCallback((j) => {
    if (!result || taken.includes(j) || picks.length >= total) return
    const g = fanGeom[j]
    const pos = layoutDraw[picks.length]
    if (!g || !pos) return
    const rect = stageRef.current?.getBoundingClientRect()
    let dx = 0
    let dy = 0
    if (rect) {
      const fanX = (g.xPct / 100) * rect.width
      const fanY = (g.yPct / 100) * rect.height
      dx = fanX - (pos.x / 100) * rect.width
      dy = fanY - (pos.y / 100) * rect.height
    }
    const pick = {
      seq: picks.length + 1,
      card_id: result.deck[j].card_id,
      reversed: result.deck[j].reversed,
      note: '',
      fromIndex: j,
      dx: dx.toFixed(1),
      dy: dy.toFixed(1),
      deg: g.deg.toFixed(1),
    }
    setPicks((prev) => [...prev, pick])
    setTaken((prev) => [...prev, j])
    setFocusIndex(nextUntaken(j))
  }, [result, taken, picks.length, total, fanGeom, layoutDraw, deckSize])

  // 翻牌完全由用户决定：可在抽牌过程中随时点任意已抽出的牌背翻开，
  // 也可以全部抽完再逐张或一次翻开。抽牌本身不再被翻牌打断。
  const flipCard = useCallback((index) => {
    if (index < 0 || index >= picks.length || flipped.includes(index)) return
    const next = [...flipped, index].sort((a, b) => a - b)
    setFlipped(next)
    setSelected(index)
    if (picks.length >= total && next.length >= total) setPhase('complete')
  }, [flipped, picks.length, total])

  const flipNext = useCallback(() => {
    const i = picks.findIndex((_, k) => !flipped.includes(k))
    if (i >= 0) flipCard(i)
  }, [picks, flipped, flipCard])

  const flipAll = useCallback(() => {
    if (!picks.length) return
    setFlipped(picks.map((_, i) => i))
    setSelected(picks.length - 1)
    setPhase('complete')
  }, [picks.length])

  const stepDraw = useCallback(() => {
    if (picks.length < total) pickCard(focusIndex)
  }, [picks.length, total, pickCard, focusIndex])

  const doCut = useCallback(() => {
    if (cutCount >= 2) {
      setCutCount(3)
      window.setTimeout(() => setPhase('draw'), 720)
    } else {
      setCutCount((c) => c + 1)
    }
  }, [cutCount])

  const doConfirm = useCallback(async () => {
    if (confirming || !picks.length) return
    setConfirming(true)
    setError('')
    try {
      const payload = picks.map((p) => ({ seq: p.seq, card_id: p.card_id, reversed: p.reversed, note: '' }))
      const res = await onConfirm(payload)
      if (res !== true) {
        setConfirming(false)
        setError('生成未成功，请稍后重试')
      }
    } catch (e) {
      setConfirming(false)
      setError('生成未成功，请稍后重试')
    }
  }, [confirming, picks, onConfirm])

  const advance = useCallback(() => {
    if (loading || confirming || !result || error) return
    if (phase === 'intro') { setPhase('shuffle'); return }
    if (phase === 'shuffle') { if (!shuffleDone) setPhase('cut'); return }
    if (phase === 'cut') { doCut(); return }
    if (phase === 'draw') { if (picks.length >= total) flipAll(); else stepDraw(); return }
    if (phase === 'complete') { doConfirm(); return }
  }, [loading, confirming, result, error, phase, shuffleDone, doCut, stepDraw, flipAll, doConfirm, picks.length, total])

  const moveFocus = useCallback((dir) => {
    if (!deckSize) return
    let j = focusIndex
    for (let k = 0; k < deckSize; k += 1) {
      j = (j + dir + deckSize) % deckSize
      if (!taken.includes(j)) { setFocusIndex(j); setKbActive(true); return }
    }
  }, [focusIndex, taken, deckSize])

  useEffect(() => {
    if (!open) return undefined
    const handler = (e) => {
      if (e.key === 'Escape') {
        if (!confirming) { e.preventDefault(); onClose() }
        return
      }
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
        e.preventDefault()
        if (phase === 'draw') moveFocus(e.key === 'ArrowRight' ? 1 : -1)
        else if (phase === 'complete' && picks.length) {
          setSelected((s) => {
            const base = s ?? 0
            return e.key === 'ArrowRight' ? (base + 1) % picks.length : (base - 1 + picks.length) % picks.length
          })
        }
        return
      }
      if (e.key === ' ' || e.code === 'Space' || e.key === 'Enter') {
        e.preventDefault()
        if (phase === 'shuffle') setEnergy((v) => (v >= 100 ? v : Math.min(100, v + 9)))
        else advance()
        return
      }
      if ((e.key === 'c' || e.key === 'C') && phase === 'cut') { e.preventDefault(); doCut() }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, advance, phase, picks.length, confirming, onClose, doCut, moveFocus])

  const onStageMove = (e) => {
    const el = stageRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const x = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width))
    const y = Math.min(1, Math.max(0, (e.clientY - rect.top) / rect.height))
    el.style.setProperty('--mx', x.toFixed(3))
    el.style.setProperty('--my', y.toFixed(3))
    if (phase !== 'shuffle' || shuffleDone) return
    const dx = e.clientX - lastPos.current.x
    const dy = e.clientY - lastPos.current.y
    const dist = Math.hypot(dx, dy)
    lastPos.current = { x: e.clientX, y: e.clientY }
    if (dist <= 0 || dist > 260) return
    const now = performance.now()
    if (now - energyTick.current < 55) return
    energyTick.current = now
    setEnergy((v) => Math.min(100, v + dist * (dragging ? 0.1 : 0.05)))
  }

  if (!open) return null

  const activeLayout = phase === 'complete' ? layoutFull : layoutDraw
  const currentStep = STEPS.findIndex((s) => s.id === phase)
  const detail = selected !== null && picks[selected] ? deckMap[picks[selected].card_id] : null
  const selectedPick = selected !== null ? picks[selected] : null
  const unflippedCount = picks.length - flipped.length
  const allDrawn = total > 0 && picks.length >= total
  const actionLabel = {
    intro: '开始洗牌',
    shuffle: shuffleDone ? '正在进入切牌…' : '完成洗牌 · 切牌',
    cut: `切牌 ${cutCount}/3`,
    draw: allDrawn ? '翻开全部牌面 · 完成牌阵' : `抽出选中牌 · 第 ${focusIndex + 1} 张`,
    complete: '确认录入 · 生成最终评定',
  }[phase] || '继续'

  const renderSlot = (pick, i, state, withFlipClass) => {
    const pos = activeLayout[i]
    const card = deckMap[pick.card_id]
    return (
      <div
        key={pick.seq}
        className={`ritual-slot state-${state} ${selected === i ? 'selected' : ''}`}
        style={{
          left: `${pos.x}%`, top: `${pos.y}%`, '--i': i,
          '--dx': `${pick.dx}px`, '--dy': `${pick.dy}px`, '--fa': `${pick.deg}deg`,
        }}
        onClick={() => { if (state === 'dealt') flipCard(i); else if (state === 'flipped') setSelected(i) }}
        onMouseEnter={() => { if (state === 'flipped') setSelected(i) }}
        onMouseLeave={() => { if (state === 'flipped') setSelected(null) }}
      >
        <div className={`ritual-card ${withFlipClass ? 'flipped' : ''}`}>
          <div className="ritual-face ritual-back" />
          <div
            className={`ritual-face ritual-front ${pick.reversed ? 'is-reversed' : ''}`}
            style={{ backgroundImage: `url(/cards/${pick.card_id}.jpg)` }}
          >
            <div className="rf-index">{String(pick.seq).padStart(2, '0')}</div>
            <div className="rf-name">{card?.label || '—'}</div>
            <div className="rf-key">{(card?.upright || '').slice(0, 14)}</div>
            <div className="rf-orient">{pick.reversed ? '逆 位' : '正 位'}</div>
          </div>
        </div>
        <div className="ritual-slot-label">
          {state === 'flipped'
            ? (phase === 'complete' ? result.positions[i]?.name : `第 ${i + 1} 张`)
            : state === 'dealt' ? '点按翻开' : ''}
        </div>
      </div>
    )
  }

  return (
    <div className="ritual-overlay" role="dialog" aria-modal="true" aria-label="线上抽卡仪式">
      <div className="ritual-frame" data-count={total >= 10 ? 'many' : 'few'} data-phase={phase}>
        <header className="ritual-header">
          <div className="ritual-header-brand">
            <img className="ritual-seal" src="/velum-mark.svg" alt="VELUM 帷间" />
            <div>
              <div className="eyebrow" style={{ marginBottom: 4 }}>线 上 抽 卡 仪 式</div>
              <div className="ritual-title">{mode?.name} · {spread?.name || spreadId}</div>
            </div>
          </div>
          <div className="ritual-steps">
            {STEPS.map((s, i) => (
              <div key={s.id} className={`ritual-step ${i === currentStep ? 'active' : ''} ${i < currentStep ? 'done' : ''}`}>
                <span className="ritual-step-dot" />{s.label}
              </div>
            ))}
          </div>
          <button className="ritual-close" onClick={onClose} disabled={confirming} aria-label="关闭抽卡仪式">×</button>
        </header>

        <div
          className={`ritual-body ${dragging ? 'is-dragging' : ''}`}
          ref={stageRef}
          onMouseMove={onStageMove}
          onMouseDown={() => { if (phase === 'shuffle' && !shuffleDone) setDragging(true) }}
          tabIndex={0}
        >
          <div className="ritual-table-orbit" />
          <div className="ritual-corner ritual-corner-a" />
          <div className="ritual-corner ritual-corner-b" />
          {dragging && phase === 'shuffle' && <div className="ritual-drag-glow" />}

          {loading && <div className="ritual-center-note">正在洗好整副牌…</div>}
          {error && !confirming && <div className="ritual-center-note warn">{error}</div>}

          {phase === 'intro' && !loading && !error && (
            <div className="ritual-intro">
              <div className="ritual-intro-deck" />
              <div className="ritual-intro-title">请 在 此 完 成 一 次 抽 卡</div>
              <p>洗牌 · 切牌 · 把整副牌摊成扇面，由你亲手一张一张选出并翻开。</p>
              <button className="btn btn-primary" onClick={() => setPhase('shuffle')}>进入仪式 →</button>
            </div>
          )}

          {phase === 'shuffle' && (
            <div className="ritual-shuffle">
              <div className={`ritual-shuffle-deck ${dragging && !shuffleDone ? 'active' : ''} ${shuffleDone ? 'settling' : ''}`}>
                {Array.from({ length: 9 }).map((_, i) => {
                  // 洗牌完成后把扇开的牌叠收回原位，作为进入切牌前的过渡。
                  const visual = shuffleDone ? 0 : energy
                  const sway = dragging && !shuffleDone ? (i % 2 ? -9 : 9) : 0
                  return (
                    <div
                      className="shuffle-card"
                      key={i}
                      style={{
                        transform: `translateX(${(i - 4) * (4 + visual * 0.34)}px) rotate(${(i - 4) * (1.4 + visual * 0.12)}deg) translateY(${Math.abs(i - 4) * -2 + sway}px)`,
                      }}
                    />
                  )
                })}
              </div>
              <div className="ritual-shuffle-caption">
                {shuffleDone ? '洗牌已完成 · 牌叠正在收拢' : '按住鼠标在牌桌上拖动洗牌，或连续按空格'}
              </div>
              <div className="ritual-energy"><div className="ritual-energy-fill" style={{ width: `${energy}%` }} /></div>
              <div className="ritual-energy-text">
                洗牌充分度 {Math.round(energy)}% {energy >= 100 ? '· 已完成，即将进入切牌' : ''}
              </div>
            </div>
          )}

          {phase === 'cut' && (
            <div className="ritual-cut">
              <div className="ritual-cut-caption">拿起上半叠、放到一旁，再依次合起 · 点击任意一叠或按 C / 空格</div>
              <div className="ritual-cut-piles">
                {[0, 1, 2].map((i) => (
                  <button
                    key={i}
                    className={`ritual-cut-pile ${cutCount > i ? 'merged' : ''}`}
                    style={{ '--dir': `${(1 - i) * 150}px` }}
                    onClick={doCut}
                    disabled={cutCount >= 3}
                  >
                    <span className="ritual-cut-glyph">◇</span>
                    <span className="ritual-cut-num">第 {i + 1} 叠</span>
                  </button>
                ))}
              </div>
              <div className="ritual-cut-progress">已合牌 {Math.min(cutCount, 3)} / 3</div>
            </div>
          )}

          {phase === 'draw' && result && (
            <div className="ritual-draw">
              <div className="ritual-draw-caption">
                {allDrawn
                  ? <>{total} / {total} 张 · 牌已全部就位</>
                  : <>第 {picks.length + 1} / {total} 张<span> · {result.positions[picks.length]?.name}</span></>}
                <div className="ritual-draw-hint">
                  {allDrawn
                    ? '点任意牌背逐张翻开，或用下方按钮一次全部翻开'
                    : '凭直觉连续抽牌 · 点击牌面 / ← → 移动 / 空格抽出；已抽出的牌可随时点开'}
                </div>
              </div>

              <div className="ritual-fan">
                {result.deck.map((d, i) => {
                  const g = fanGeom[i]
                  return (
                    <button
                      key={i}
                      className={`fan-card ${taken.includes(i) ? 'taken' : ''} ${kbActive && focusIndex === i ? 'focused' : ''} ${hoverIndex === i ? 'hovered' : ''}`}
                      style={{
                        left: `${g.xPct.toFixed(2)}%`,
                        top: `${g.yPct.toFixed(2)}%`,
                        '--deg': `${g.deg.toFixed(2)}deg`,
                        '--i': i,
                        zIndex: i,
                      }}
                      onMouseEnter={() => { setFocusIndex(i); setHoverIndex(i) }}
                      onMouseLeave={() => setHoverIndex(null)}
                      onClick={() => pickCard(i)}
                      aria-label={`扇面第 ${i + 1} 张牌`}
                    >
                      <div className="fan-card-inner" />
                    </button>
                  )
                })}
              </div>

              {picks.map((p, i) => renderSlot(
                p, i,
                flipped.includes(i) ? 'flipped' : 'dealt',
                false,
              ))}
            </div>
          )}

          {phase === 'complete' && result && (
            <div className="ritual-complete">
              <div className="ritual-complete-caption">牌 阵 已 成 · 悬停或按 ← → 查看每张牌</div>
              {picks.map((p, i) => renderSlot(p, i, 'flipped', true))}
              {detail && (
                <div className="ritual-detail">
                  <div className="field-label">第 {selected + 1} 张 · {result.positions[selected]?.name}</div>
                  <div className="ritual-detail-name">{detail.label}</div>
                  <div className="hint">{selectedPick?.reversed ? '逆位 · 能量存在但表达不充分' : '正位'}</div>
                  <p>{detail.upright}</p>
                </div>
              )}
            </div>
          )}

          {confirming && (
            <div className="ritual-submitting">
              <div className="ritual-submit-sigil"><VelumSigil /></div>
              <div className="ritual-submit-eyebrow">ARCANUM SUB VELO</div>
              <div className="ritual-submit-title">正 在 生 成 最 终 评 定</div>
              <div className="ritual-submit-rule"><span /></div>
              <p className="ritual-submit-note">约需 5–10 秒，请勿重复点击或关闭窗口</p>
              <div className="ritual-submit-steps">
                {['核对牌面', '整理牌面脉络', '生成最终评定'].map((t, i) => (
                  <div className="ritual-submit-step" key={t} style={{ '--i': i }}>
                    <span className="ritual-submit-check" />{t}
                  </div>
                ))}
              </div>
              <div className="ritual-loading-bar"><span /></div>
            </div>
          )}
        </div>

        <footer className="ritual-footer">
          <div className="ritual-keyhint">空格 洗牌 / 抽出 / 全部翻开 · 点击牌背逐张翻开 · ← → 选牌 · C 切牌 · Esc 退出</div>
          <div className="ritual-actions">
            {phase === 'draw' && (
              <span className="ritual-progress">已抽 {picks.length} / {total} · 已翻 {flipped.length} · 牌叠 {deckSize - taken.length} 张</span>
            )}
            {phase === 'draw' && unflippedCount > 0 && (
              <button className="btn" onClick={flipNext} disabled={loading || confirming}>翻开一张</button>
            )}
            <button className="btn" onClick={onClose} disabled={confirming}>退出仪式</button>
            <button
              className="btn btn-primary"
              onClick={error ? () => setAttempt((a) => a + 1) : advance}
              disabled={loading || confirming || shuffleDone || (phase === 'cut' && cutCount >= 3)}
            >
              {confirming ? '生成中…' : error ? '重试' : actionLabel}
            </button>
          </div>
        </footer>
      </div>
    </div>
  )
}
