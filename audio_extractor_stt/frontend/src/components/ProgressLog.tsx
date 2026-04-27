import { useEffect, useRef } from 'react'
import type { ProgressEvent } from '../api'

interface Props {
  logs: string[]
  progress: ProgressEvent | null
}

function formatTime(s: number): string {
  if (s < 60) return `${s}초`
  const m = Math.floor(s / 60)
  const r = s % 60
  return r > 0 ? `${m}분 ${r}초` : `${m}분`
}

export default function ProgressLog({ logs, progress }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const overall = progress?.overall ?? 0
  const stagePct = progress?.stage_pct ?? 0

  return (
    <div className="progress-log">

      {/* ── 전체 게이지 ─────────────────────────────────────── */}
      <div className="gauge-section overall-gauge-section">
        <div className="gauge-header">
          <span className="gauge-title">전체 진행률</span>
          <span className="gauge-value">{overall}%</span>
        </div>
        <div className="gauge-track overall-track">
          <div className="gauge-fill overall-fill" style={{ width: `${overall}%` }} />
        </div>
        {progress && (
          <div className="gauge-meta">
            <span>경과 {formatTime(progress.elapsed_s)}</span>
            {progress.eta_s !== null && progress.eta_s > 0 && (
              <span>예상 완료까지 약 {formatTime(progress.eta_s)}</span>
            )}
          </div>
        )}
      </div>

      {/* ── 현재 단계 게이지 ────────────────────────────────── */}
      {progress && (
        <div className="gauge-section stage-gauge-section">
          <div className="gauge-header">
            <span className="gauge-title">
              <span className="spinner" />
              {progress.stage_label}
            </span>
            <span className="gauge-value">{stagePct}%</span>
          </div>
          <div className="gauge-track stage-track">
            <div className="gauge-fill stage-fill" style={{ width: `${stagePct}%` }} />
          </div>
        </div>
      )}

      {/* ── 로그 ────────────────────────────────────────────── */}
      <div className="log-container">
        {logs.map((msg, i) => (
          <div key={i} className="log-line">✔ {msg}</div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
