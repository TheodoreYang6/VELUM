import React, { useEffect, useState } from 'react'
import { api } from './api.js'
import ScenePage from './ScenePage.jsx'
import QuestionPage from './QuestionPage.jsx'
import RitualPage from './RitualPage.jsx'
import RecordPage from './RecordPage.jsx'
import DrawPage from './DrawPage.jsx'
import ResultPage from './ResultPage.jsx'
import RulesPage from './RulesPage.jsx'
import CardLibraryPage from './CardLibraryPage.jsx'
import CardDetailModal from './CardDetailModal.jsx'
import IntroVeil from './IntroVeil.jsx'
import AuthModal from './AuthModal.jsx'
import ErrorBoundary from './ErrorBoundary.jsx'
import ModelSettingsModal from './ModelSettingsModal.jsx'
import { readModelSettings, hasPersonalKey } from './modelSettings.js'

const STEPS = [
  { id: 'scene', num: 'I', label: '择定场景' },
  { id: 'question', num: 'II', label: '确立问题' },
  { id: 'ritual', num: 'III', label: '仪式指导' },
  { id: 'draw', num: 'IV', label: '线上抽卡' },
  { id: 'record', num: 'V', label: '录入牌面' },
  { id: 'result', num: 'VI', label: '最终评定' },
  { id: 'library', num: 'VII', label: '牌库' },
  { id: 'rules', num: 'VIII', label: '规范维护' },
]

export default function App() {
  const [step, setStep] = useState('scene')
  const [data, setData] = useState({ scenes: [], spreads: [], cards: [], ritual: [], library: [], health: null })
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [sceneId, setSceneId] = useState('')
  const [spreadId, setSpreadId] = useState('')
  const [useReversed, setUseReversed] = useState(false)
  const [question, setQuestion] = useState('')
  const [sessionId, setSessionId] = useState('')
  const [completed, setCompleted] = useState([])
  const [reading, setReading] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [libraryCard, setLibraryCard] = useState(null)
  const [showIntro, setShowIntro] = useState(() => {
    try { return localStorage.getItem('velum.intro') !== 'done' } catch (e) { return true }
  })
  const [viewed, setViewed] = useState(() => {
    try { return JSON.parse(localStorage.getItem('velum.viewed') || '[]') } catch (e) { return [] }
  })
  const [me, setMe] = useState(null)
  const [showAuth, setShowAuth] = useState(false)
  const [showModelSettings, setShowModelSettings] = useState(false)
  const [modelConfigured, setModelConfigured] = useState(() => hasPersonalKey(readModelSettings()))

  const markViewed = (id) => setViewed((prev) => {
    if (prev.includes(id)) return prev
    const next = [...prev, id]
    try { localStorage.setItem('velum.viewed', JSON.stringify(next)) } catch (e) { /* ignore */ }
    return next
  })
  const openCard = (id) => setLibraryCard(id)
  const closeCard = () => setLibraryCard(null)
  const shiftCard = (delta) => {
    const list = data.library
    if (!list.length || !libraryCard) return
    const i = list.findIndex((c) => c.card_id === libraryCard)
    if (i < 0) return
    setLibraryCard(list[(i + delta + list.length) % list.length].card_id)
  }
  const activeCard = data.library.find((c) => c.card_id === libraryCard) || null

  const load = () => {
    setLoading(true)
    Promise.all([api.scenes(), api.spreads(), api.cards(), api.ritual(), api.health(), api.cardLibrary()])
      .then(([scenes, spreads, cards, ritual, health, library]) => {
        setData({ scenes, spreads, cards, ritual, health, library })
        setLoadError('')
      })
      .catch((e) => setLoadError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  useEffect(() => {
    api.authMe().then((r) => setMe(r.user)).catch(() => setMe(null))
  }, [])

  // 每次切换环节都从页面开头开始，避免沿用上一页的滚动位置
  // （尤其生成最终评定后，页面应停在标题而不是被拖到底部）。
  useEffect(() => {
    try { window.scrollTo({ top: 0, left: 0, behavior: 'instant' }) } catch (e) {
      try { window.scrollTo(0, 0) } catch (_) { /* ignore */ }
    }
  }, [step])

  const openAuth = () => setShowAuth(true)
  const handleAuth = (user) => { setMe(user); setShowAuth(false) }
  const handleLogout = () => {
    api.authLogout().then(() => setMe(null)).catch(() => setMe(null))
  }

  const scene = data.scenes.find((s) => s.scene_id === sceneId)
  const spread = data.spreads.find((s) => s.spread_id === spreadId)
  const spreadWithFlag = spread ? { ...spread, use_reversed: useReversed } : null

  const canEnter = (id) => {
    if (id === 'scene' || id === 'rules' || id === 'library') return true
    if (!sceneId) return false
    if (id === 'question') return true
    if (!sessionId) return false
    if (id === 'ritual' || id === 'record' || id === 'draw') return true
    if (id === 'result') return !!reading
    return false
  }

  const go = (id) => { setError(''); setStep(id) }

  const chooseScene = (id) => {
    setSceneId(id)
    const s = data.scenes.find((x) => x.scene_id === id)
    const rec = (s?.recommended_ids || [])[0]
    if (rec) setSpreadId(rec)
  }

  const createSession = async () => {
    setBusy(true)
    setError('')
    try {
      const res = await api.createSession({
        scene_id: sceneId, spread_id: spreadId, question: question.trim(), use_reversed: useReversed,
      })
      setSessionId(res.session_id)
      setCompleted([])
      setStep('ritual')
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const submitCards = async (list) => {
    setBusy(true)
    setError('')
    try {
      await api.saveCards(sessionId, list)
      const result = await api.reading(sessionId)
      setReading(result)
      setStep('result')
      return true
    } catch (e) {
      setError(e.message)
      return e.message || '提交失败'
    } finally {
      setBusy(false)
    }
  }

  const restart = () => {
    setSceneId(''); setSpreadId(''); setUseReversed(false); setQuestion('')
    setSessionId(''); setCompleted([]); setReading(null); setError(''); setStep('scene')
  }

  const toggleStep = (seq) => {
    setCompleted((prev) => prev.includes(seq) ? prev.filter((x) => x !== seq) : [...prev, seq])
  }

  return (
    <>
      <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <img className="brand-seal" src="/velum-mark.svg" alt="VELUM 帷间徽记" />
          <div>
            <div className="brand-name">VELUM<span className="brand-name-zh">｜帷间</span></div>
            <div className="brand-sub">塔罗仪式辅助</div>
          </div>
        </div>
        <div className="brand-motto">
          <span className="brand-motto-latin">ARCANUM SUB VELO</span>
          <span className="brand-motto-zh">帷幕之下的秘仪</span>
        </div>
        <div className="sidebar-rule" />
        <div className="nav-label">占 卜 仪 轨</div>
        <ul className="nav-list">
          {STEPS.map((s) => (
            <li key={s.id}>
              <button
                className={`nav-item ${step === s.id ? 'active' : ''}`}
                disabled={!canEnter(s.id) || loading}
                onClick={() => go(s.id)}
              >
                <span className="nav-num">{s.num}</span>
                <span>{s.label}</span>
              </button>
            </li>
          ))}
        </ul>
        <div className="sidebar-foot">
          <strong>VELUM｜帷间</strong><br />
          韦特体系 · 78 张牌<br />
          {data.health ? '规范库已就绪' : '规范库载入中'}
          <div className="sidebar-account">
            <span className="sidebar-avatar">✦</span>
            {me ? (
              <div className="sidebar-account-info">
                <span className="sidebar-account-name">{me.display}</span>
                <button className="sidebar-account-link" onClick={handleLogout}>退出</button>
              </div>
            ) : (
              <button className="sidebar-account-login" onClick={openAuth}>登录 / 注册</button>
            )}
          </div>
          <button className="sidebar-model" onClick={() => setShowModelSettings(true)}>
            <span className={`sidebar-model-dot ${modelConfigured ? 'on' : ''}`} />
            模型连接 · {modelConfigured ? '已配置' : '未配置'}
          </button>
          <button className="sidebar-replay" onClick={() => setShowIntro(true)}>重温开场</button>
        </div>
      </aside>

      <main className="main">
        <div className="main-inner">
          {loading && <div className="loading"><div className="spinner">· · ·</div><p>正在准备…</p></div>}
          {!loading && loadError && (
            <div className="error-box">
              <h2>暂时无法打开</h2>
              <p>请确认服务已启动，然后重试。</p>
              <button className="btn" onClick={load}>重新连接</button>
            </div>
          )}
          {!loading && !loadError && (
            <>
              {step === 'scene' && (
                <ScenePage
                  scenes={data.scenes} spreads={data.spreads} sceneId={sceneId} spreadId={spreadId}
                  useReversed={useReversed} onScene={chooseScene} onSpread={setSpreadId}
                  onReversed={setUseReversed} onNext={() => go('question')}
                />
              )}
              {step === 'question' && (
                <QuestionPage
                  scene={scene} question={question} onQuestion={setQuestion}
                  onBack={() => go('scene')} onNext={createSession} busy={busy} error={error}
                />
              )}
              {step === 'ritual' && (
                <RitualPage
                  steps={data.ritual} spread={spreadWithFlag} sceneId={sceneId} question={question}
                  completed={completed} onToggle={toggleStep} onBack={() => go('question')}
                  onNext={() => go('record')} onDraw={() => go('draw')}
                />
              )}
              {step === 'draw' && (
                <DrawPage
                  spreads={data.spreads} spreadId={spreadId}
                  sceneId={scene?.name || sceneId} sessionId={sessionId}
                  useReversed={useReversed} onSpread={setSpreadId}
                  onBack={() => go('ritual')} onConfirm={submitCards}
                />
              )}
              {step === 'record' && (
                <RecordPage
                  spread={spreadWithFlag} cards={data.cards} useReversed={useReversed}
                  sceneId={sceneId} question={question} busy={busy} error={error}
                  onBack={() => go('ritual')} onSubmit={submitCards}
                />
              )}
              {step === 'result' && (
                <ErrorBoundary onRestart={restart}>
                  <ResultPage reading={reading} sessionId={sessionId} onRestart={restart} onRules={() => go('rules')} onOpenCard={openCard} />
                </ErrorBoundary>
              )}
              {step === 'library' && (
                <CardLibraryPage library={data.library} viewed={viewed} onOpenCard={openCard} />
              )}
              {step === 'rules' && (
                <RulesPage me={me} onShowLogin={openAuth} onLogout={handleLogout} />
              )}
            </>
          )}
        </div>
      </main>
      <CardDetailModal
        card={activeCard}
        library={data.library}
        onClose={closeCard}
        onShift={shiftCard}
        onViewed={markViewed}
      />
      {showIntro && (
        <IntroVeil
          onDone={() => {
            try { localStorage.setItem('velum.intro', 'done') } catch (e) { /* ignore */ }
            setShowIntro(false)
          }}
        />
      )}
      <AuthModal open={showAuth} onClose={() => setShowAuth(false)} onLogin={handleAuth} />
      <ModelSettingsModal
        open={showModelSettings}
        onClose={() => setShowModelSettings(false)}
        onChanged={(s) => setModelConfigured(hasPersonalKey(s))}
      />
      </div>
    </>
  )
}
