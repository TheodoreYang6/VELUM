import React from 'react'

/**
 * VELUM 徽记的「可动变体」。
 * 构件全部取自 public/velum-mark.svg：华盖横杆、双层垂弧帷檐、三层菱形框、
 * 八芒星与虚线光环、对角四枚刻点、牌桌双线。去掉静态底色与外框，
 * 拆成可分层描绘／旋转／呼吸的仪式印，用于「正在生成最终评定」的揭幕动画。
 */
export default function VelumSigil() {
  return (
    <svg className="vs-sigil" viewBox="0 0 240 240" role="img" aria-label="VELUM 帷间徽记 · 正在揭幕">
      <defs>
        <radialGradient id="vsGlow" cx="50%" cy="44%" r="54%">
          <stop offset="0%" stopColor="#c8a45c" stopOpacity="0.22" />
          <stop offset="58%" stopColor="#c8a45c" stopOpacity="0.055" />
          <stop offset="100%" stopColor="#c8a45c" stopOpacity="0" />
        </radialGradient>
      </defs>

      <circle className="vs-glow" cx="120" cy="112" r="106" fill="url(#vsGlow)" />

      {/* 双环：顺时针慢转 + 一道逆时针游走的亮弧 */}
      <g className="vs-rings">
        <circle className="vs-draw vs-ring-outer" cx="120" cy="120" r="104" style={{ '--len': 660 }} />
        <circle className="vs-draw vs-ring-inner" cx="120" cy="120" r="97" style={{ '--len': 615 }} />
      </g>
      <circle className="vs-arc" cx="120" cy="120" r="104" />
      <circle className="vs-orbit" cx="120" cy="120" r="88" />

      {/* 对角四枚刻点，依次点亮 */}
      <g className="vs-corners">
        <path className="vs-corner" style={{ '--i': 0 }} d="M190.7 43.3 l4 6 -4 6 -4 -6 z" />
        <path className="vs-corner" style={{ '--i': 1 }} d="M49.3 43.3 l4 6 -4 6 -4 -6 z" />
        <path className="vs-corner" style={{ '--i': 2 }} d="M190.7 184.7 l4 6 -4 6 -4 -6 z" />
        <path className="vs-corner" style={{ '--i': 3 }} d="M49.3 184.7 l4 6 -4 6 -4 -6 z" />
      </g>

      {/* 三层同心菱形框 */}
      <g className="vs-frames">
        <path className="vs-draw" style={{ '--len': 510, '--d': '0s' }} d="M120 30 L210 120 L120 210 L30 120 Z" />
        <path className="vs-draw" style={{ '--len': 430, '--d': '.14s' }} d="M120 44 L196 120 L120 196 L44 120 Z" />
        <path className="vs-draw" style={{ '--len': 375, '--d': '.28s' }} d="M120 54 L186 120 L120 186 L54 120 Z" />
      </g>

      {/* 华盖横杆与束带 */}
      <g className="vs-canopy">
        <path className="vs-draw" style={{ '--len': 120 }} d="M64 50 H176" />
        <path className="vs-draw" style={{ '--len': 120, '--d': '.1s' }} d="M64 54 H176" />
        <path className="vs-draw" style={{ '--len': 14 }} d="M64 50 V60" />
        <path className="vs-draw" style={{ '--len': 14 }} d="M176 50 V60" />
        <circle cx="64" cy="50" r="3.4" />
        <circle cx="176" cy="50" r="3.4" />
        <path className="vs-canopy-gem" d="M120 45 l4 5 -4 5 -4 -5 z" />
      </g>
      <path className="vs-sweep" d="M64 50 H176" />

      {/* 双层垂弧帷檐与左右褶皱 */}
      <g className="vs-drapes">
        <path className="vs-draw" style={{ '--len': 70, '--d': '.3s' }} d="M64 57 Q 92 80, 120 62" />
        <path className="vs-draw" style={{ '--len': 70, '--d': '.3s' }} d="M176 57 Q 148 80, 120 62" />
        <path className="vs-draw" style={{ '--len': 165, '--d': '.42s' }} d="M62 58 C 68 102, 88 146, 120 182" />
        <path className="vs-draw" style={{ '--len': 165, '--d': '.42s' }} d="M178 58 C 172 102, 152 146, 120 182" />
        <path className="vs-draw" style={{ '--len': 150, '--d': '.54s' }} d="M72 58 C 77 98, 94 140, 120 172" />
        <path className="vs-draw" style={{ '--len': 150, '--d': '.54s' }} d="M168 58 C 163 98, 146 140, 120 172" />
      </g>

      {/* 中央八芒星：虚线光环 + 八点光尘 + 星体呼吸 */}
      <circle className="vs-halo" cx="120" cy="104" r="26" />
      <g className="vs-sparks">
        <circle className="vs-spark" style={{ '--i': 0 }} cx="120" cy="76" r="1.3" />
        <circle className="vs-spark" style={{ '--i': 1 }} cx="140" cy="84" r="1.3" />
        <circle className="vs-spark" style={{ '--i': 2 }} cx="148" cy="104" r="1.3" />
        <circle className="vs-spark" style={{ '--i': 3 }} cx="140" cy="124" r="1.3" />
        <circle className="vs-spark" style={{ '--i': 4 }} cx="120" cy="132" r="1.3" />
        <circle className="vs-spark" style={{ '--i': 5 }} cx="100" cy="124" r="1.3" />
        <circle className="vs-spark" style={{ '--i': 6 }} cx="92" cy="104" r="1.3" />
        <circle className="vs-spark" style={{ '--i': 7 }} cx="100" cy="84" r="1.3" />
      </g>
      <g className="vs-star">
        <path className="vs-star-body" d="M120 84 L125 99 L140 104 L125 109 L120 124 L115 109 L100 104 L115 99 Z" />
        <path className="vs-star-core" d="M120 96 L128 104 L120 112 L112 104 Z" />
      </g>

      {/* 牌桌双线与垂饰 */}
      <g className="vs-base">
        <path className="vs-draw" style={{ '--len': 60, '--d': '.7s' }} d="M92 192 H148" />
        <path className="vs-draw" style={{ '--len': 46, '--d': '.76s' }} d="M98 197 H142" />
        <path className="vs-base-gem" d="M120 186 l5 6 -5 6 -5 -6 z" />
        <circle cx="120" cy="203" r="1.6" />
      </g>
    </svg>
  )
}
