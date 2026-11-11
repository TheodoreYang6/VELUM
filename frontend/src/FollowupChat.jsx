import React, { useEffect, useMemo, useRef, useState } from 'react'
import { api } from './api.js'
import { FRIENDLY_RETRY } from './labels.js'

function suggestionsFor(reading) {
  const raw = reading?.positions
  const pos = Array.isArray(raw) ? raw.filter((x) => x && typeof x === 'object') : []
  if (!pos.length) return []
  const a = pos[0]
  const b = pos[pos.length - 1]
  const label = (v) => (typeof v === 'string' ? v : '')
  return [
    `「${label(a.label)}」落在${label(a.position)}位，具体该怎么理解？`,
    '这几张牌连起来，最想提醒我留意什么？',
    `「${label(b.label)}」${b.reversed ? '逆位' : '正位'}的能量，在我现在的状态里可能怎么表现？`,
    '如果只做一件小事，我可以从哪里开始？',
  ]
}

export default function FollowupChat({ sessionId, reading }) {
  const [turns, setTurns] = useState([])
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [loaded, setLoaded] = useState(false)
  const threadRef = useRef(null)
  const hasSentRef = useRef(false)
  const suggestions = useMemo(() => suggestionsFor(reading), [reading])

  useEffect(() => {
    let alive = true
    setLoaded(false)
    setTurns([])
    hasSentRef.current = false
    if (!sessionId) return () => { alive = false }
    api.followupHistory(sessionId)
      .then((res) => {
        if (!alive) return
        const list = Array.isArray(res?.turns) ? res.turns : []
        setTurns(list.filter((t) => t && typeof t === 'object')
          .map((t) => ({ role: t.role || 'assistant', content: typeof t.content === 'string' ? t.content : '' })))
      })
      .catch(() => { /* 历史读不到时从空对话开始，不影响本次占卜 */ })
      .finally(() => { if (alive) setLoaded(true) })
    return () => { alive = false }
  }, [sessionId])

  // 只滚动追问框本身，绝不滚动整个页面。
  // 首次挂载、拉取历史、渲染结果页都不触发；只有问卜者真的发送一条追问后才跟随到末尾。
  useEffect(() => {
    const el = threadRef.current
    if (!el || !hasSentRef.current) return
    el.scrollTop = el.scrollHeight
  }, [turns, busy])

  const send = async (raw) => {
    const q = String(raw ?? text).trim()
    if (!q || busy || !sessionId) return
    hasSentRef.current = true
    setText('')
    setError('')
    setTurns((prev) => [...prev, { role: 'user', content: q }])
    setBusy(true)
    try {
      const res = await api.followupAsk(sessionId, q)
      setTurns((prev) => [...prev, {
        role: 'assistant', content: res.answer, degraded: !!res.degraded,
      }])
    } catch (e) {
      setTurns((prev) => prev.slice(0, -1))
      setText(q)
      setError(FRIENDLY_RETRY)
    } finally {
      setBusy(false)
    }
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  const clear = async () => {
    if (busy) return
    hasSentRef.current = false
    setTurns([])
    setError('')
    try { await api.followupClear(sessionId) } catch (e) { /* 清空失败时下一轮仍可继续 */ }
  }

  return (
    <section className="followup">
      <div className="followup-head">
        <div className="eyebrow">继 续 追 问</div>
        <h2 className="followup-title">就这次牌面，继续问下去</h2>
        <p className="followup-desc">
          背景始终是本次写下的问题、抽到的牌与同一套解读规范，不会重新抽牌，也不会另起一卦。
          想到什么都可以接着问，帷间会连着前面聊过的内容一起回答。
        </p>
      </div>

      {suggestions.length > 0 && (
        <div className="fu-chips">
          {suggestions.map((s, i) => (
            <button key={i} className="fu-chip" disabled={busy} onClick={() => send(s)}>{s}</button>
          ))}
        </div>
      )}

      <div className="fu-thread" ref={threadRef} aria-live="polite">
        {loaded && turns.length === 0 && (
          <div className="fu-empty">
            可以问某一张牌落在某个位置该怎么读、牌与牌之间的呼应，
            也可以把评定里某一句拿出来，问它落到你的处境里是什么意思。
          </div>
        )}
        {turns.map((t, i) => (
          <div className={`fu-msg ${t.role === 'user' ? 'from-querent' : 'from-velum'}`} key={i}>
            <div className="fu-who">{t.role === 'user' ? '你' : '帷间'}</div>
            <div className="fu-bubble">
              {(typeof t.content === 'string' ? t.content : '').split(/\n{2,}/).map((p, j) => <p key={j}>{p}</p>)}
              {t.degraded && <div className="fu-degraded">已按内置规范作答</div>}
            </div>
          </div>
        ))}
        {busy && (
          <div className="fu-msg from-velum">
            <div className="fu-who">帷间</div>
            <div className="fu-bubble fu-typing"><span>· · ·</span> 正在就本次牌面斟酌</div>
          </div>
        )}
      </div>

      {error && <div className="notice warn fu-error">{error}</div>}

      <div className="fu-compose">
        <textarea
          className="fu-input"
          rows={2}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="把想继续问的写在这里…"
          disabled={busy}
          maxLength={300}
        />
        <button className="btn btn-primary fu-send" disabled={busy || !text.trim()} onClick={() => send()}>
          {busy ? '斟酌中…' : '继续追问'}
        </button>
      </div>

      <div className="fu-foot">
        <span>Enter 发送 · Shift + Enter 换行 · 仅围绕本次占卜</span>
        {turns.length > 0 && <button className="fu-clear" onClick={clear} disabled={busy}>清空对话</button>}
      </div>
    </section>
  )
}
