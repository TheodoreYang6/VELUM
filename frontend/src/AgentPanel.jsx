import React, { useState } from 'react'
import { api } from './api.js'
import { ruleLabel, friendlyStep, FRIENDLY_RETRY } from './labels.js'

const BUTTON = {
  refine_question: '润色问题措辞',
  ritual_script: '生成仪式引导语',
  narrative: '生成解读叙述',
  followups: '生成后续追问',
}

function Output({ node, output, onApply }) {
  if (node === 'refine_question') {
    return (
      <div className="agent-output">
        <div className="field-label">改写建议</div>
        <div className="agent-refined">{output.refined}</div>
        {onApply && <button className="btn" style={{ marginTop: 12 }} onClick={() => onApply(output.refined)}>采用这条问题</button>}
        <div className="field-label" style={{ marginTop: 20 }}>改写理由</div>
        <ul className="plain-list">{(output.reasons || []).map((r, i) => <li key={i}>{r}</li>)}</ul>
        {(output.alternatives || []).length > 0 && (
          <>
            <div className="field-label" style={{ marginTop: 16 }}>其他表述</div>
            <div className="chip-row">
              {(output.alternatives || []).map((a, i) => (
                <button key={i} className="chip" onClick={() => onApply?.(a)}>{a}</button>
              ))}
            </div>
          </>
        )}
      </div>
    )
  }
  if (node === 'ritual_script') {
    return (
      <div className="agent-output agent-script">
        {[['开场', output.opening], ['洗牌前', output.shuffle], ['抽牌前', output.draw], ['收尾', output.closing]].map(([k, v]) => (
          <div className="agent-script-row" key={k}>
            <div className="agent-script-key">{k}</div>
            <div>{v}</div>
          </div>
        ))}
      </div>
    )
  }
  if (node === 'narrative') {
    return (
      <div className="agent-output">
        <div className="agent-refined">{output.summary}</div>
        {(output.paragraphs || []).map((p, i) => <p key={i} className="agent-para">{p}</p>)}
        {output.tone_note && <div className="hint" style={{ marginTop: 12 }}>{output.tone_note}</div>}
      </div>
    )
  }
  return (
    <div className="agent-output">
      <ol className="plain-list">{(output.questions || []).map((q, i) => <li key={i}>{q}</li>)}</ol>
      {output.note && <div className="hint" style={{ marginTop: 12 }}>{output.note}</div>}
    </div>
  )
}

export default function AgentPanel({ node, title, payload, onApply, hint }) {
  const [state, setState] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [showTrace, setShowTrace] = useState(false)

  const run = async () => {
    setBusy(true)
    setError('')
    try {
      const result = await api.agentRun({ node, ...payload })
      setState(result)
    } catch (e) {
      setError(FRIENDLY_RETRY)
    } finally {
      setBusy(false)
    }
  }

  const sourceNames = state
    ? [...new Set((state.sources || []).map((s) => ruleLabel(s.doc_id)))].join(' · ') || '内置占卜规范'
    : ''

  return (
    <div className="panel agent-panel">
      <div className="agent-head">
        <div>
          <div className="field-label" style={{ marginBottom: 4 }}>智 能 辅 助</div>
          <div className="panel-title" style={{ margin: 0 }}>{title || BUTTON[node]}</div>
          {hint && <div className="hint" style={{ marginTop: 6 }}>{hint}</div>}
        </div>
        <button className="btn" disabled={busy} onClick={run}>{busy ? '生成中…' : (BUTTON[node] || '生成')}</button>
      </div>

      {error && <div className="notice warn" style={{ marginTop: 14 }}>{error}</div>}

      {state && (
        <>
          <div className={`agent-state ${state.degraded ? 'degraded' : ''}`}>
            <span className="agent-dot" />
            {state.degraded ? '已按内置规范生成' : '解读已生成'} · 依据本次牌面与占卜规范
          </div>
          <Output node={node} output={state.output} onApply={onApply} />
          <div className="agent-trace-toggle">
            <button className="btn btn-ghost" onClick={() => setShowTrace(!showTrace)}>{showTrace ? '收起生成过程' : '查看生成过程'}</button>
          </div>
          {showTrace && (
            <div className="agent-trace">
              {(state.trace || []).map((t, i) => (
                <div className="agent-trace-row" key={i}>
                  <span className="agent-trace-step">{friendlyStep(t.step)}</span>
                  <span className="hint">{t.result === 'passed' ? '已通过' : '已完成'}</span>
                </div>
              ))}
              <div className="hint" style={{ marginTop: 8 }}>依据：{sourceNames}</div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
