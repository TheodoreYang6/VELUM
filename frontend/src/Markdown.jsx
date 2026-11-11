import React from 'react'
import { ruleLabel } from './labels.js'

function display(text) {
  return String(text)
    .replace(/RULE-\d+/g, (m) => ruleLabel(m))
    .replace(/`?draw_source:\s*online`?/g, '线上抽卡')
    .replace(/`?stage:\s*\[all\]`?/g, '全环节适用')
}

function inline(text) {
  const parts = display(text).split(/(\*\*[^*]+\*\*|`[^`]+`)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={i}>{part.slice(1, -1)}</code>
    }
    return <React.Fragment key={i}>{part}</React.Fragment>
  })
}

export default function Markdown({ text }) {
  if (!text) return null
  const lines = String(text).split('\n')
  const out = []
  let list = []
  let table = []

  const flushList = () => {
    if (list.length) {
      out.push(<ul key={`ul-${out.length}`}>{list.map((li, i) => <li key={i}>{inline(li)}</li>)}</ul>)
      list = []
    }
  }
  const flushTable = () => {
    if (!table.length) return
    const rows = table.filter((r) => !/^\|[\s|:-]+\|$/.test(r))
    const cells = rows.map((r) => r.trim().replace(/^\||\|$/g, '').split('|').map((c) => c.trim()))
    if (cells.length) {
      const head = cells[0]
      out.push(
        <table key={`tb-${out.length}`}>
          <thead><tr>{head.map((c, i) => <th key={i}>{inline(c)}</th>)}</tr></thead>
          <tbody>
            {cells.slice(1).map((row, ri) => (
              <tr key={ri}>{row.map((c, ci) => <td key={ci}>{inline(c)}</td>)}</tr>
            ))}
          </tbody>
        </table>,
      )
    }
    table = []
  }

  lines.forEach((raw, idx) => {
    const line = raw.trim()
    if (line.startsWith('|') && line.endsWith('|')) {
      flushList()
      table.push(line)
      return
    }
    flushTable()
    if (line.startsWith('- ') || /^\d+\.\s/.test(line)) {
      list.push(line.replace(/^(- |\d+\.\s)/, ''))
      return
    }
    flushList()
    if (!line) return
    if (line.startsWith('#### ')) out.push(<h4 key={idx}>{inline(line.slice(5))}</h4>)
    else if (line.startsWith('### ')) out.push(<h4 key={idx}>{inline(line.slice(4))}</h4>)
    else if (line.startsWith('## ')) out.push(<h3 key={idx}>{inline(line.slice(3))}</h3>)
    else if (line.startsWith('# ')) out.push(<h3 key={idx}>{inline(line.slice(2))}</h3>)
    else if (line.startsWith('> ')) out.push(<blockquote key={idx}>{inline(line.slice(2))}</blockquote>)
    else out.push(<p key={idx} style={{ margin: '6px 0' }}>{inline(line)}</p>)
  })
  flushList()
  flushTable()
  return <div className="step-body">{out}</div>
}
