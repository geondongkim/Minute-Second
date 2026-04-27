import { useCallback, useState } from 'react'
import UploadZone, { type UploadParams } from './components/UploadZone'
import ProgressLog from './components/ProgressLog'
import ResultTabs from './components/ResultTabs'
import { createJob, subscribeJobEvents, fetchJobResult, type JobResult, type ProgressEvent } from './api'
import './App.css'

type AppState =
  | { phase: 'idle' }
  | { phase: 'uploading'; progress: number }
  | { phase: 'processing'; jobId: string; logs: string[]; progress: ProgressEvent | null }
  | { phase: 'done'; result: JobResult }
  | { phase: 'error'; message: string }

const SESSION_KEY = 'minute_second_result'

function loadSavedResult(): AppState {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY)
    if (raw) {
      const result = JSON.parse(raw)
      return { phase: 'done', result }
    }
  } catch {
    // 파싱 실패 시 무시
  }
  return { phase: 'idle' }
}

export default function App() {
  const [state, setState] = useState<AppState>(loadSavedResult)

  const handleFile = useCallback(async (params: UploadParams) => {
    setState({ phase: 'uploading', progress: 0 })

    try {
      const jobId = await createJob(
        params.file,
        (pct) => setState({ phase: 'uploading', progress: pct }),
        params.meetingType,
        params.refText,
      )

      setState({ phase: 'processing', jobId, logs: [], progress: null })

      subscribeJobEvents(
        jobId,
        (msg) =>
          setState((prev) =>
            prev.phase === 'processing'
              ? { ...prev, logs: [...prev.logs, msg] }
              : prev,
          ),
        async () => {
          try {
            const result = await fetchJobResult(jobId)
            sessionStorage.setItem(SESSION_KEY, JSON.stringify(result))
            setState({ phase: 'done', result })
          } catch (e) {
            setState({ phase: 'error', message: String(e) })
          }
        },
        (msg) => setState({ phase: 'error', message: msg }),
        (p) =>
          setState((prev) =>
            prev.phase === 'processing' ? { ...prev, progress: p } : prev,
          ),
      )
    } catch (e) {
      setState({ phase: 'error', message: String(e) })
    }
  }, [])

  return (
    <div className="app">
      <header className="app-header">
        <h1>📹 동영상 자동 회의록</h1>
        <p>동영상을 업로드하면 STT + 화자 분리 + AI 요약으로 회의록을 자동 생성합니다.</p>
      </header>

      <main className="app-main">
        {(state.phase === 'idle' || state.phase === 'error') && (
          <>
            <UploadZone onFile={handleFile} />
            {state.phase === 'error' && (
              <div className="error-box">
                <strong>⚠️ 오류:</strong> {state.message}
              </div>
            )}
          </>
        )}

        {state.phase === 'uploading' && (
          <div className="uploading">
            <p>📤 업로드 중... {state.progress.toFixed(0)}%</p>
            <progress value={state.progress} max={100} />
          </div>
        )}

        {state.phase === 'processing' && (
          <ProgressLog logs={state.logs} progress={state.progress} />
        )}

        {state.phase === 'done' && (
          <>
            <ResultTabs result={state.result} />
            <button
              className="btn-ghost reset-btn"
              onClick={() => { sessionStorage.removeItem(SESSION_KEY); setState({ phase: 'idle' }) }}
            >
              ← 새 파일 분석
            </button>
          </>
        )}
      </main>
    </div>
  )
}
