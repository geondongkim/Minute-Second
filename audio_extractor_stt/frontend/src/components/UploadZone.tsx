import { useCallback, useRef, useState } from 'react'

export interface UploadParams {
  file: File
  meetingType: string
  refText: string
}

interface Props {
  onFile: (params: UploadParams) => void
}

const ACCEPTED_VIDEO = ['video/mp4', 'video/x-matroska', 'video/avi', 'video/quicktime']
const ACCEPTED_REF   = ['.md', '.txt', '.pdf']

const MEETING_TYPES = [
  { value: 'general',    label: '일반 회의' },
  { value: 'standup',    label: '스탠드업 / 데일리' },
  { value: 'retro',      label: '회고 (Retrospective)' },
  { value: 'planning',   label: '플래닝' },
  { value: 'executive',  label: '경영진 회의' },
  { value: 'interview',  label: '인터뷰' },
  { value: 'brainstorm', label: '브레인스토밍' },
  { value: 'review',     label: '리뷰 (코드/디자인)' },
  { value: '1on1',       label: '1:1 미팅' },
  { value: 'lecture',    label: '라이브 강의' },
]

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

async function readFileAsText(file: File): Promise<string> {
  if (file.type === 'application/pdf' || file.name.endsWith('.pdf')) {
    return `[PDF 파일: ${file.name} — 텍스트 추출 미지원, 파일명만 참고로 전달됩니다]`
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = () => reject(new Error('파일 읽기 실패'))
    reader.readAsText(file, 'utf-8')
  })
}

export default function UploadZone({ onFile }: Props) {
  const [dragging, setDragging]       = useState(false)
  const [selected, setSelected]       = useState<File | null>(null)
  const [meetingType, setMeetingType] = useState('general')
  const [refFile, setRefFile]         = useState<File | null>(null)
  const refInputRef = useRef<HTMLInputElement>(null)

  const pick = useCallback((file: File | undefined) => {
    if (file) setSelected(file)
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragging(false)
      pick(e.dataTransfer.files[0])
    },
    [pick],
  )

  const handleStart = async () => {
    if (!selected) return
    let refText = ''
    if (refFile) {
      try { refText = await readFileAsText(refFile) } catch { /* 무시 */ }
    }
    onFile({ file: selected, meetingType, refText })
  }

  return (
    <div className="upload-zone-wrapper">
      {/* ── 동영상 드롭존 ── */}
      <div
        className={`upload-zone${dragging ? ' dragging' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        <input
          id="file-input"
          type="file"
          accept={ACCEPTED_VIDEO.join(',')}
          className="visually-hidden"
          onChange={(e) => pick(e.target.files?.[0])}
        />

        {selected ? (
          <div className="file-selected">
            <span className="file-icon">🎬</span>
            <span className="file-name">{selected.name}</span>
            <span className="file-size">{formatBytes(selected.size)}</span>
          </div>
        ) : (
          <label htmlFor="file-input" className="drop-label">
            <span className="drop-icon">📁</span>
            <p>동영상 파일을 드래그하거나 클릭하여 선택</p>
            <p className="drop-hint">MP4, MKV, AVI, MOV 지원 · 최대 2 GB</p>
          </label>
        )}
      </div>

      {/* ── 설정 패널 ── */}
      <div className="upload-settings">
        <div className="setting-row">
          <label htmlFor="meeting-type-select">🗂️ 회의 유형</label>
          <select
            id="meeting-type-select"
            value={meetingType}
            onChange={(e) => setMeetingType(e.target.value)}
          >
            {MEETING_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>

        <div className="setting-row">
          <label>📎 참고자료 첨부 (선택)</label>
          <div className="ref-file-row">
            <span className="ref-file-name">
              {refFile ? refFile.name : '파일 없음 (MD / TXT)'}
            </span>
            <button
              className="btn-ghost btn-sm"
              onClick={() => refInputRef.current?.click()}
            >
              {refFile ? '변경' : '선택'}
            </button>
            {refFile && (
              <button
                className="btn-ghost btn-sm btn-remove"
                onClick={() => setRefFile(null)}
              >
                ✕
              </button>
            )}
            <input
              ref={refInputRef}
              type="file"
              accept={ACCEPTED_REF.join(',')}
              aria-label="참고자료 파일 선택"
              title="참고자료 파일 선택 (MD, TXT)"
              className="visually-hidden"
              onChange={(e) => setRefFile(e.target.files?.[0] ?? null)}
            />
          </div>
        </div>
      </div>

      {/* ── 시작 버튼 ── */}
      {selected && (
        <div className="upload-actions">
          <button className="btn-primary" onClick={handleStart}>
            분석 시작 →
          </button>
          <button className="btn-ghost" onClick={() => { setSelected(null); setRefFile(null) }}>
            다시 선택
          </button>
        </div>
      )}
    </div>
  )
}

