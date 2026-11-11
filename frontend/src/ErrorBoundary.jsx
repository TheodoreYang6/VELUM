import React from 'react'

/* 渲染期异常兜底：React 18 遇到未捕获异常会卸载整棵 root，表现为「整页黑屏」。
   此边界把故障限制在单个页面，给出可恢复的提示，而不是让站点消失。 */
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { failed: false, message: '' }
  }

  static getDerivedStateFromError(err) {
    return { failed: true, message: String(err?.message || err || '') }
  }

  componentDidCatch(err, info) {
    // 仅本地记录，不上报、不暴露内部堆栈给用户
    console.error('[VELUM] 页面渲染失败', err, info?.componentStack)
  }

  render() {
    if (!this.state.failed) return this.props.children
    return (
      <div className="error-box" style={{ maxWidth: 620, margin: '64px auto' }}>
        <h2>这一页暂时无法显示</h2>
        <p>本次记录仍在，可以返回上一步重试，或开始新一次占卜。</p>
        <button className="btn" onClick={() => this.setState({ failed: false, message: '' })}>重新显示</button>
        {this.props.onRestart && (
          <button className="btn" style={{ marginLeft: 10 }} onClick={this.props.onRestart}>开始新一次占卜</button>
        )}
      </div>
    )
  }
}
