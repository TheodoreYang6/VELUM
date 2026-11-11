import React, { useState } from 'react'
import { api } from './api.js'
import RetrievalPanel from './RetrievalPanel.jsx'
import AgentPanel from './AgentPanel.jsx'

export default function QuestionPage({ scene, question, onQuestion, onBack, onNext, busy, error }) {
  const [check, setCheck] = useState(null)
  const [checking, setChecking] = useState(false)

  const runCheck = async () => {
    setChecking(true)
    try {
      const result = await api.checkQuestion({ scene_id: scene?.scene_id || 'general', question })
      setCheck(result)
    } catch (e) {
      setCheck({ valid: true, issues: [], suggestions: [] })
    } finally {
      setChecking(false)
    }
  }

  return (
    <>
      <div className="eyebrow">STEP II · 立题</div>
      <h1 className="page-title">把问题写在牌叠之前</h1>
      <p className="page-desc">
        好的问题应当：由你承担选择的责任、保持开放、详略适中、聚焦自身、中立且正向。写下的问题会贯穿本次占卜。
      </p>

      <div className="panel">
        <label className="field-label">当前场景 · {scene?.name || '通用指引'}</label>
        <div className="chip-row" style={{ marginBottom: 20 }}>
          {(scene?.templates || []).slice(0, 5).map((t, i) => (
            <button key={i} className="chip" onClick={() => { onQuestion(t); setCheck(null) }}>{t}</button>
          ))}
        </div>
        <label className="field-label" htmlFor="question-input">书面问题</label>
        <textarea
          id="question-input"
          className="textarea"
          value={question}
          onChange={(e) => { onQuestion(e.target.value); setCheck(null) }}
          placeholder="例如：关于目前这段关系，我最需要看清的是什么？"
        />
        <div className="btn-row" style={{ marginTop: 16 }}>
          <button className="btn" onClick={runCheck} disabled={checking || question.trim().length < 4}>
            {checking ? '检查中…' : '查看参考问法'}
          </button>
          <span className="hint">任何问法都可提出，此处只提供参考</span>
        </div>

        {check && (
          <div className="notice">
            <h4>可以直接使用</h4>
            {check.issues?.length > 0 && <p style={{ margin: '0 0 4px' }}>{check.issues.join('；')}</p>}
            <p style={{ margin: 0 }}>寻物、时间、吉凶、他人动向等问题均可占问，系统会按牌面与对应表作答。</p>
            {check.suggestions?.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <div className="field-label" style={{ marginBottom: 6 }}>本场景参考问法</div>
                <div className="chip-row">
                  {check.suggestions.map((t, i) => <button key={i} className="chip" onClick={() => { onQuestion(t); setCheck(null) }}>{t}</button>)}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <AgentPanel
        node="refine_question"
        title="帮你把问题说得更合适"
        payload={{ scene_id: scene?.scene_id || 'general', scene_name: scene?.name, question }}
        onApply={(q) => { onQuestion(q); setCheck(null) }}
        hint="只调整措辞，不改变你的本意；改写后由你确认再使用。"
      />

      <RetrievalPanel stage="question" sceneId={scene?.scene_id} question={question} title="本环节参考的规范" />

      {error && <div className="notice warn" style={{ marginTop: 16 }}>暂时无法继续，请稍后重试</div>}
      <div className="btn-row">
        <button className="btn btn-ghost" onClick={onBack}>← 返回场景</button>
        <button className="btn btn-primary" disabled={busy || question.trim().length < 8} onClick={onNext}>
          {busy ? '正在准备…' : '确立问题 · 进入仪式 →'}
        </button>
      </div>
    </>
  )
}
