import React from 'react'
import Markdown from './Markdown.jsx'
import RetrievalPanel from './RetrievalPanel.jsx'
import AgentPanel from './AgentPanel.jsx'

export default function RitualPage({ steps, spread, sceneId, question, completed, onToggle, onBack, onNext, onDraw }) {
  const allDone = steps.length > 0 && completed.length === steps.length

  return (
    <>
      <div className="eyebrow">STEP III · 仪式指导</div>
      <h1 className="page-title">在现实中完成这套动作</h1>
      <p className="page-desc">
        系统只指导动作，不代抽牌、不随机生成牌。<strong style={{ color: 'var(--gold-bright)', fontWeight: 500 }}>洗牌、切牌与抽牌由问卜者本人完成</strong>，占卜师只做指引、记录与组织解读。每完成一步请勾选。
      </p>

      <div className="panel" style={{ marginBottom: 20 }}>
        <div className="panel-title">本次约定</div>
        <div className="kv">
          <dt>牌阵</dt><dd>{spread?.name}（{spread?.positions?.length} 张）</dd>
          <dt>问题</dt><dd>{question}</dd>
          <dt>逆位</dt><dd>{spread?.use_reversed ? '启用' : '不启用'}</dd>
        </div>
      </div>

      <h2 className="section-title">牌阵位置 · 翻牌前先确认含义</h2>
      <div className="pos-grid">
        {(spread?.positions || []).map((p) => (
          <div className="pos-box" key={p.seq}>
            <div className="pos-seq">{String(p.seq).padStart(2, '0')}</div>
            <div className="pos-name">{p.name}</div>
            <div className="pos-meaning">{p.meaning}</div>
          </div>
        ))}
      </div>

      <h2 className="section-title">仪式流程</h2>
      <div className="steps">
        {steps.map((s) => (
          <div className="panel step-card" key={s.seq}>
            <div className="step-num">{s.seq}</div>
            <div style={{ minWidth: 0 }}>
              <div className="step-name">{s.name}</div>
              <Markdown text={s.text} />
              <label className="toggle step-check">
                <input type="checkbox" checked={completed.includes(s.seq)} onChange={() => onToggle(s.seq)} />
                此步已在现实中完成
              </label>
            </div>
            <div className="hint">{completed.includes(s.seq) ? '已完成' : '待完成'}</div>
          </div>
        ))}
      </div>

      <RetrievalPanel stage="ritual-prep" sceneId={sceneId} question={question} title="本环节参考的规范" />

      <AgentPanel
        node="ritual_script"
        title="生成可由占卜师朗读的引导语"
        payload={{ scene_id: sceneId, question, spread_name: spread?.name, use_reversed: !!spread?.use_reversed }}
        hint="引导语依据既定仪式流程，不添加额外步骤。"
      />

      <div className="btn-row">
        <button className="btn btn-ghost" onClick={onBack}>← 返回立题</button>
        <button className="btn" onClick={onDraw}>改用线上抽卡 →</button>
        <button className="btn btn-primary" onClick={onNext}>
          {allDone ? '牌已抽出 · 前往录入 →' : '跳过未完成项 · 前往录入 →'}
        </button>
      </div>
    </>
  )
}
