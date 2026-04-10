import { useEffect, useRef } from 'react'

interface Props {
  logs: string[]
}

export default function ProgressLog({ logs }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  return (
    <div className="progress-log">
      <div className="progress-header">
        <span className="spinner" />
        <span>처리 중 — 완료까지 수 분 소요될 수 있습니다</span>
      </div>
      <div className="log-container">
        {logs.map((msg, i) => (
          <div key={i} className="log-line">
            <span className="log-check">✔</span>
            {msg}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
