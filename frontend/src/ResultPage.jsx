import React, { useState } from 'react'
import FollowupChat from './FollowupChat.jsx'
import { ruleLabel, friendlyStep } from './labels.js'

function Block({ num, title, children }) {
  return (
    <div className="reading-block">
      <h3><span style={{ color: 'var(--gold-dim)', fontSize: 12 }}>{num}</span> {title}</h3>
      {children}
    </div>
  )
}

const BOUNDARY = '本系统依韦特牌义与古典占问对应表作出占断，属占卜性质的解释，不替代医疗、法律、财务等专业人士的判断；方位、时间与人物的对应存在流派差异，结论由你自行取舍。'

/* 防御式取值：模型偶发把数组字段写成字符串/对象，直接 .map 会抛异常并让 React
   卸载整棵树（整页黑屏）。统一收敛为「可渲染元素数组」，任何畸形数据都只降级不崩溃。 */
const asText = (v) => {
  if (v == null) return ''
  if (typeof v === 'string') return v
  if (typeof v === 'number' || typeof v === 'boolean') return String(v)
  if (typeof v === 'object') {
    for (const k of ['text', 'content', 'note', 'value', 'summary']) {
      if (typeof v[k] === 'string') return v[k]
    }
    return JSON.stringify(v)
  }
  return String(v)
}
const asList = (v) => {
  if (Array.isArray(v)) return v.filter((x) => x !== null && x !== undefined && x !== '')
  if (v === null || v === undefined || v === '') return []
  return [asText(v)]
}
const asItems = (v) => asList(v).map(asText)

/* 旧版字段（tone / core_theme / position_analysis …）仍要能读：历史会话沿用旧版式。 */
function LegacyVerdictBody({ o, onOpenCard, positionCards }) {
  const list = (items) => asItems(items).map((x, i) => <li key={i}>{x}</li>)
  return (
    <>
      <div className="verdict-main">
        <div className="verdict-quote">{o.verdict || '暂无评定'}</div>
        <div className="verdict-meta">
          <div><span>整 体 基 调</span><strong>{o.tone || '—'}</strong></div>
          <div><span>核 心 课 题</span><strong>{o.core_theme || '—'}</strong></div>
        </div>
      </div>
      <h3 className="verdict-section">逐位分析</h3>
      <div className="verdict-positions">
        {(o.position_analysis || []).map((p, i) => (
          <div className="verdict-pos" key={i}>
            <div className="verdict-pos-head">
              <span>{p.position}</span>
              <img className="verdict-pos-thumb" src={`/cards/${positionCards?.[i]?.card_id}.jpg`} alt=""
                onError={(e) => { e.currentTarget.style.display = 'none' }} />
              <button className="cd-inline-link"
                onClick={() => { const id = positionCards[i]?.card_id; if (id) onOpenCard?.(id) }}>{p.card}</button>
              <span className="entry-tag">{p.orientation}</span>
            </div>
            <p>{p.reading}</p>
          </div>
        ))}
      </div>
      <h3 className="verdict-section">动态脉络</h3>
      <p className="verdict-para">{o.dynamics || '—'}</p>
      <div className="verdict-cols">
        <div className="verdict-col"><h4>可依凭的优势</h4><ul>{list(o.strengths)}</ul></div>
        <div className="verdict-col"><h4>需要留意的阻力</h4><ul>{list(o.challenges)}</ul></div>
      </div>
      <div className="verdict-summary">
        <div className="field-label">最 终 评 定</div>
        <p>{o.summary || '—'}</p>
      </div>
      <div className="verdict-cols">
        <div className="verdict-col"><h4>行动方向</h4><ol>{list(o.guidance)}</ol></div>
        <div className="verdict-col"><h4>边界与留意</h4><ul>{list(o.cautions)}</ul></div>
      </div>
    </>
  )
}

/* 新版：以连续文字为主，结构化信息退居辅助，读起来是一封写给问卜者的信。 */
function ArticleVerdictBody({ o, onOpenCard, positionCards }) {
  const notes = asList(o.card_notes)
  const strengths = asItems(o.strengths)
  const challenges = asItems(o.challenges)
  const guidance = asItems(o.guidance)
  const cautions = asItems(o.cautions)
  const paragraphs = asItems(o.paragraphs)
  const text = (v) => asText(v)
  const opening = text(o.opening)
  const verdictLine = text(o.verdict)
  const theme = text(o.theme)
  const closing = text(o.closing)

  return (
    <div className="vd-article">
      {opening && <p className="vd-opening">{opening}</p>}
      {verdictLine && <div className="vd-quote">{verdictLine}</div>}
      {theme && (
        <div className="vd-theme">
          <span className="vd-kicker">核 心 课 题</span>
          <p>{theme}</p>
        </div>
      )}

      {paragraphs.length > 0 && (
        <div className="vd-prose">
          {paragraphs.map((p, i) => <p key={i}>{p}</p>)}
        </div>
      )}

      {notes.length > 0 && (
        <>
          <h3 className="verdict-section">逐牌札记</h3>
          <div className="verdict-positions verdict-notes">
            {notes.map((entry, i) => {
              // 札记项也可能是字符串（模型退化输出），统一按对象读取
              const p = typeof entry === 'object' && entry !== null ? entry : { card: asText(entry) }
              // 牌名里若已带「（逆位）」，就不再重复显示一个朝向标签。
              const cardText = asText(p.card)
              const tail = cardText.match(/[（(](正位|逆位)[）)]\s*$/)
              const orient = asText(p.orientation) || (tail ? tail[1] : '')
              const cardName = cardText.replace(/[（(](正位|逆位)[）)]\s*$/, '').trim()
              const noteText = asText(p.note || p.reading)
              const posName = asText(p.position)
              return (
                <div className="verdict-pos" key={i}>
                  <div className="verdict-pos-index">
                    <span className="verdict-pos-num">{String(i + 1).padStart(2, '0')}</span>
                    <span className="verdict-pos-name">{posName}</span>
                  </div>
                  <img className="verdict-pos-thumb" src={`/cards/${positionCards?.[i]?.card_id}.jpg`} alt=""
                    onError={(e) => { e.currentTarget.style.display = 'none' }} />
                  <div className="verdict-pos-body">
                    <div className="verdict-pos-title">
                      <button className="cd-inline-link"
                        onClick={() => { const id = positionCards[i]?.card_id; if (id) onOpenCard?.(id) }}>
                        {cardName}
                      </button>
                      {orient && <span className="entry-tag">{orient}</span>}
                    </div>
                    <p>{noteText}</p>
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}

      {(strengths.length > 0 || challenges.length > 0) && (
        <div className="verdict-cols">
          {strengths.length > 0 && (
            <div className="verdict-col"><h4>可以借上的力</h4><ul>{strengths.map((x, i) => <li key={i}>{x}</li>)}</ul></div>
          )}
          {challenges.length > 0 && (
            <div className="verdict-col"><h4>需要多留一步的地方</h4><ul>{challenges.map((x, i) => <li key={i}>{x}</li>)}</ul></div>
          )}
        </div>
      )}

      {guidance.length > 0 && (
        <>
          <h3 className="verdict-section">可以从哪里着手</h3>
          <ol className="vd-guidance-list">{guidance.map((x, i) => <li key={i}>{x}</li>)}</ol>
        </>
      )}

      {cautions.length > 0 && (
        <div className="vd-cautions">
          <span>此 外</span>
          {cautions.map((x, i) => <p key={i}>{x}</p>)}
        </div>
      )}

      {closing && <div className="vd-closing">{closing}</div>}
      <div className="vd-boundary">{BOUNDARY}</div>
    </div>
  )
}

function VerdictBlock({ verdict, onOpenCard, positionCards }) {
  const [showTrace, setShowTrace] = useState(false)
  if (!verdict) return null
  const o = (verdict.output && typeof verdict.output === 'object') ? verdict.output : {}
  // 旧版会话可能带空的 paragraphs=[]（历史归一化残留），须以「有实质内容」判定，
  // 否则旧版版式会被误判成文章式而显示空白。
  const hasModernContent = !!o.opening || (Array.isArray(o.paragraphs) && o.paragraphs.length > 0)
    || (Array.isArray(o.card_notes) && o.card_notes.length > 0)
  const modern = hasModernContent && !o.tone && !o.core_theme
  const sourceNames = [...new Set(asList(verdict.sources).map((s) => ruleLabel(asText(s?.doc_id))))].filter(Boolean).join(' · ') || '内置占卜规范'

  return (
    <div className="verdict-wrap">
      <div className="verdict-head">
        <div className="eyebrow">最 终 评 定</div>
        <div className="verdict-state">
          {verdict.degraded ? '已按内置规范生成' : '解读已生成'} · 依据本次牌面与占卜规范
        </div>
      </div>

      {modern
        ? <ArticleVerdictBody o={o} onOpenCard={onOpenCard} positionCards={positionCards} />
        : <LegacyVerdictBody o={o} onOpenCard={onOpenCard} positionCards={positionCards} />}

      {verdict.degraded && (
        <div className="notice warn" style={{ marginTop: 18 }}>
          智能润色暂不可用，已按内置规范生成参考内容。
        </div>
      )}

      <div className="agent-trace-toggle">
        <button className="btn btn-ghost" onClick={() => setShowTrace(!showTrace)}>
          {showTrace ? '收起生成依据' : '查看生成依据'}
        </button>
      </div>
      {showTrace && (
        <div className="agent-trace verdict-trace">
          {asList(verdict.trace).map((t, i) => (
            <div className="agent-trace-row" key={i}>
              <span className="agent-trace-step">{friendlyStep(asText(t?.step))}</span>
              <span className="hint">{t?.result === 'passed' ? '已通过' : '已完成'}</span>
            </div>
          ))}
          <div className="hint" style={{ marginTop: 8 }}>依据：{sourceNames}</div>
        </div>
      )}
    </div>
  )
}

export default function ResultPage({ reading, sessionId, onRestart, onRules, onOpenCard }) {
  const [showSources, setShowSources] = useState(false)
  if (!reading) return null
  const r = reading.record || {}
  const positions = asList(reading.positions)
  const observations = asItems((reading.structure || {}).observations)
  const synthesis = asItems(reading.synthesis)
  const actions = asItems(reading.actions)
  const sources = asList(reading.sources)

  return (
    <>
      <div className="eyebrow">STEP VI · 最终评定</div>
      <h1 className="page-title">写给此刻的你</h1>
      <p className="page-desc">
        这一段评定只围绕你写下的问题、亲手抽出的牌，以及它们落在各个位置上的含义。
        它是一面镜子，不是一份判决；读过之后，决定仍在你手里。
      </p>

      {r.draw_source === 'online' && (
        <div className="notice">本次牌面来自<strong style={{ color: 'var(--gold-bright)', fontWeight: 500 }}>线上抽卡</strong>，不替代现实中的洗牌与抽牌仪式。</div>
      )}

      <VerdictBlock verdict={reading.verdict} onOpenCard={onOpenCard} positionCards={positions} />

      <FollowupChat sessionId={sessionId} reading={reading} />

      <details className="detail-fold">
        <summary>展开解读依据 · 本次记录 / 逐位释义 / 结构观察 / 参考规范</summary>
        <div className="detail-fold-body">
          <Block num="一" title="本次记录">
            <div className="panel">
              <dl className="kv">
                <dt>场景</dt><dd>{asText(r.scene)}</dd>
                <dt>问题</dt><dd>{asText(r.question)}</dd>
                <dt>牌阵</dt><dd>{asText(r.spread)}</dd>
                <dt>逆位</dt><dd>{r.use_reversed ? '启用' : '不启用'}</dd>
                <dt>牌面来源</dt><dd>{r.draw_source === 'online' ? '线上抽卡' : '现实仪式录入'}</dd>
                <dt>时间</dt><dd>{asText(r.created_at || reading.created_at)}</dd>
              </dl>
            </div>
          </Block>

          <Block num="二" title="逐位释义">
            {positions.map((e, i) => {
              const item = (e && typeof e === 'object') ? e : {}
              return (
                <div className="entry" key={item.seq ?? i}>
                  <div className="entry-head">
                    <span className="entry-pos">{String(item.seq ?? i + 1).padStart(2, '0')} · {asText(item.position)}</span>
                    <img className="entry-thumb" src={`/cards/${item.card_id}.jpg`} alt=""
                      onError={(ev) => { ev.currentTarget.style.display = 'none' }} />
                    <button className="cd-inline-link entry-card" onClick={() => item.card_id && onOpenCard?.(item.card_id)}>{asText(item.label)}</button>
                    {item.reversed && <span className="entry-tag">逆位</span>}
                  </div>
                  <p className="entry-text">{asText(item.reading)}</p>
                </div>
              )
            })}
          </Block>

          <Block num="三" title="结构观察">
            <div className="panel">
              <ul className="obs-list">
                {observations.map((o, i) => <li key={i}>{o}</li>)}
              </ul>
            </div>
          </Block>

          <Block num="四" title="场景化综合">
            <div className="panel">
              <ul className="obs-list">
                {synthesis.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
          </Block>

          <Block num="五" title="行动参考">
            <div className="panel">
              <ol className="plain-list">
                {actions.map((a, i) => <li key={i}>{a}</li>)}
              </ol>
            </div>
          </Block>

          <Block num="六" title="边界提示">
            <div className="boundary">{asText(reading.boundary)}</div>
          </Block>

          <div className="panel" style={{ marginTop: 30 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
              <div>
                <div className="field-label" style={{ marginBottom: 4 }}>本 次 参 考 的 规 范</div>
                <div className="panel-title" style={{ margin: 0 }}>解读依据已按环节整理</div>
              </div>
              <button className="btn btn-ghost" onClick={() => setShowSources(!showSources)}>{showSources ? '收起' : '查看参考的规范'}</button>
            </div>
            {showSources && (
              <div style={{ marginTop: 16 }}>
                {sources.map((s, i) => {
                  const item = (s && typeof s === 'object') ? s : {}
                  return (
                    <div className="source-item" key={i}>
                      <div className="source-head">
                        <span className="source-id">{ruleLabel(asText(item.doc_id))}</span>
                        <span>{asText(item.section)}</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      </details>

      <div className="btn-row">
        <button className="btn btn-primary" onClick={onRestart}>开始新一次占卜</button>
        <button className="btn" onClick={onRules}>查看 / 维护规范文档</button>
      </div>
    </>
  )
}
