import React, { useEffect, useState } from 'react'
import { api } from './api.js'
import { ruleLabel, FRIENDLY_RETRY } from './labels.js'

export default function RetrievalPanel({ stage, sceneId, question = '', cardNames = [], positionNames = [], title }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [open, setOpen] = useState(false)

  useEffect(() => {
    let alive = true
    setError('')
    api.retrieve({
      stage,
      scene_id: sceneId || 'general',
      question,
      card_names: cardNames,
      position_names: positionNames,
      top_k: 5,
    }).then((r) => { if (alive) setData(r) })
      .catch(() => { if (alive) setError(FRIENDLY_RETRY) })
    return () => { alive = false }
  }, [stage, sceneId, question, JSON.stringify(cardNames), JSON.stringify(positionNames)])

  return (
    <div className="panel" style={{ marginTop: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
        <div>
          <div className="field-label" style={{ marginBottom: 4 }}>本 环 节 参 考</div>
          <div className="panel-title" style={{ margin: 0 }}>{title || '本次参考的规范'}</div>
        </div>
        <button className="btn btn-ghost" onClick={() => setOpen(!open)}>{open ? '收起' : '查看参考的规范'}</button>
      </div>
      {data && (
        <div className="hint" style={{ marginTop: 10 }}>
          已根据当前环节与场景，查阅相关规范。
        </div>
      )}
      {error && <div className="notice warn" style={{ marginTop: 10 }}>{error}</div>}
      {open && data && (
        <div style={{ marginTop: 16 }}>
          {data.results.map((r) => (
            <div className="source-item" key={`${r.doc_id}-${r.section}-${r.chunk_id}`}>
              <div className="source-head">
                <span className="source-id">{ruleLabel(r.doc_id)}</span>
                <span>{r.section}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
