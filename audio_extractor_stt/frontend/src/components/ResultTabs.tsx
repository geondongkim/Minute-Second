import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { JobResult } from '../api'

interface Props {
  result: JobResult
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <button className="copy-btn" onClick={handleCopy}>
      {copied ? '✔ 복사됨' : '📋 복사'}
    </button>
  )
}

const TABS = ['📌 회의 요약', '🗣️ 화자별 스크립트', '📄 전체 원문'] as const

export default function ResultTabs({ result }: Props) {
  const [active, setActive] = useState(0)

  const contents = [result.summary, result.speaker_text, result.combined_text]

  return (
    <div className="tabs">
      <div className="tab-bar">
        {TABS.map((name, i) => (
          <button
            key={i}
            className={`tab-btn${active === i ? ' active' : ''}`}
            onClick={() => setActive(i)}
          >
            {name}
          </button>
        ))}
      </div>

      <div className="tab-content">
        <CopyButton text={contents[active]} />

        {active === 0 ? (
          <div className="markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {result.summary}
            </ReactMarkdown>
          </div>
        ) : (
          <textarea
            className="result-area"
            readOnly
            value={contents[active]}
          />
        )}
      </div>
    </div>
  )
}
