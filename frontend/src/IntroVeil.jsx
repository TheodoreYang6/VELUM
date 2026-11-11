import React, { useEffect, useRef, useState } from 'react'

// 首次进入的开场帷幕：复用卡背视觉（velum-cardback.svg）与 3D 翻牌互动。
// 第一拍：轻触 → 卡背翻为愚者（major-00），「赞美愚者」浮现并停留；
// 第二拍：读完轻触任意处步入主页面（或数秒后自动进入）。
export default function IntroVeil({ onDone }) {
  const [phase, setPhase] = useState('idle') // idle | revealing | exiting
  const rootRef = useRef(null)
  const timers = useRef([])
  const doneRef = useRef(false)

  const clearTimers = () => { timers.current.forEach(clearTimeout); timers.current = [] }
  useEffect(() => () => clearTimers(), [])

  useEffect(() => {
    const t = setTimeout(() => rootRef.current?.focus(), 60)
    return () => clearTimeout(t)
  }, [])

  const finish = () => {
    if (doneRef.current) return
    doneRef.current = true
    onDone()
  }
  const enterNow = () => {
    clearTimers()
    setPhase('exiting')
    timers.current.push(setTimeout(finish, 650))
  }

  const reveal = () => {
    if (phase === 'idle') {
      setPhase('revealing')
      // 翻开愚者并展示赞美后，自动步入主页面；读得快也可再次轻触立即进入
      timers.current.push(setTimeout(() => setPhase('exiting'), 2800))
      timers.current.push(setTimeout(finish, 3500))
    } else if (phase === 'revealing') {
      enterNow()
    }
  }
  const skip = () => {
    if (phase === 'idle' || phase === 'revealing') enterNow()
  }
  const onKey = (e) => {
    if (e.key === 'Escape') skip()
    else if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') { e.preventDefault(); reveal() }
  }

  const cls = ['veil']
  if (phase === 'revealing') cls.push('revealing')
  if (phase === 'exiting') cls.push('exiting')
  const hint = phase === 'idle' ? '轻触帷幕 · 翻开愚者' : '愚者已现 · 轻触步入仪式'

  return (
    <div
      ref={rootRef}
      className={cls.join(' ')}
      onClick={reveal}
      onKeyDown={onKey}
      role="button"
      tabIndex={0}
      aria-label="开场：轻触帷幕，翻开愚者并步入 VELUM 帷间"
    >
      <img className="veil-watermark" src="/velum-mark.svg" alt="" aria-hidden="true" />
      <div className="veil-content">
        <div className="veil-head">
          <div className="veil-title">VELUM｜帷间</div>
          <div className="veil-motto">ARCANUM SUB VELO</div>
        </div>
        <div className="veil-card" aria-hidden="true">
          <div className="veil-card-inner">
            <div className="veil-face back" />
            <div className="veil-face front" />
          </div>
        </div>
        <div className="veil-praise">
          <span className="veil-praise-name">愚者 · 旅程之始</span>
          <p className="veil-praise-text">赞美愚者——不问归途，纵身一跃；未知自会在脚下铺成道路。</p>
        </div>
        <div className="veil-hint">{hint}</div>
      </div>
      <button className="veil-skip" onClick={(e) => { e.stopPropagation(); skip() }}>跳过</button>
    </div>
  )
}
