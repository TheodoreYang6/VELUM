export const RULE_LABELS = {
  'RULE-00': '体系总纲',
  'RULE-01': '大阿卡纳牌义',
  'RULE-02': '小阿卡纳牌义',
  'RULE-03': '牌阵与位置',
  'RULE-04': '仪式流程',
  'RULE-05': '提问规范',
  'RULE-06': '解读方法',
  'RULE-07': '占卜伦理',
  'RULE-08': '场景配置',
  'RULE-09': '牌面详解',
}

export const ruleLabel = (id) => RULE_LABELS[id] || '占卜规范'

export const friendlyStep = (step = '') => {
  const s = String(step)
  if (s.includes('build_feed') || s.includes('per_card')) return '整理问题、牌面与解读资料'
  if (s.includes('retrieve')) return '查阅占卜规范'
  if (s.includes('llm_call')) return '组织解读文字'
  if (s.includes('repair')) return '整理表述'
  if (s.includes('guardrail')) return '检查措辞与边界'
  if (s.includes('fallback')) return '改用内置规范'
  return '生成中'
}

export const FRIENDLY_RETRY = '暂时无法完成，请稍后重试'
