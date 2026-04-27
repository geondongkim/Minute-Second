import { useCallback, useState } from 'react'

interface Props {
  onFile: (file: File) => void
}

const ACCEPTED = ['video/mp4', 'video/x-matroska', 'video/avi', 'video/quicktime']

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export default function UploadZone({ onFile }: Props) {
  const [dragging, setDragging] = useState(false)
  const [selected, setSelected] = useState<File | null>(null)

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

  return (
    <div
      className={`upload-zone${dragging ? ' dragging' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
      <input
        id="file-input"
        type="file"
        accept={ACCEPTED.join(',')}
        style={{ display: 'none' }}
        onChange={(e) => pick(e.target.files?.[0])}
      />

      {selected ? (
        <div className="file-selected">
          <span className="file-icon">🎬</span>
          <span className="file-name">{selected.name}</span>
          <span className="file-size">{formatBytes(selected.size)}</span>
          <div className="upload-actions">
            <button className="btn-primary" onClick={() => onFile(selected)}>
              분석 시작 →
            </button>
            <button className="btn-ghost" onClick={() => setSelected(null)}>
              다시 선택
            </button>
          </div>
        </div>
      ) : (
        <label htmlFor="file-input" className="drop-label">
          <span className="drop-icon">📁</span>
          <p>동영상 파일을 드래그하거나 클릭하여 선택</p>
          <p className="drop-hint">MP4, MKV, AVI, MOV 지원 · 최대 2 GB</p>
        </label>
      )}
    </div>
  )
}
