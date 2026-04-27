const BASE = '/api'

// ─── Progress event type ──────────────────────────────────────────────────────

export interface ProgressEvent {
  overall: number        // 0-100 전체 진행률
  stage_label: string   // 현재 단계 이름
  stage_pct: number     // 0-100 현재 단계 내 진행률
  elapsed_s: number     // 경과 시간 (초)
  eta_s: number | null  // 예상 남은 시간 (초), null이면 미정
}

// ─── 파일 업로드 (XMLHttpRequest — upload progress 이벤트 지원) ────────────────

export async function createJob(
  file: File,
  onProgress: (pct: number) => void,
): Promise<string> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const form = new FormData()
    form.append('file', file)

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) onProgress((e.loaded / e.total) * 100)
    })

    xhr.addEventListener('load', () => {
      if (xhr.status === 200) {
        resolve((JSON.parse(xhr.responseText) as { job_id: string }).job_id)
      } else {
        reject(new Error(`업로드 실패 (${xhr.status}): ${xhr.responseText}`))
      }
    })

    xhr.addEventListener('error', () => reject(new Error('네트워크 오류')))
    xhr.open('POST', `${BASE}/jobs`)
    xhr.send(form)
  })
}

// ─── SSE 구독 ─────────────────────────────────────────────────────────────────

export function subscribeJobEvents(
  jobId: string,
  onLog: (msg: string) => void,
  onDone: () => void,
  onError: (msg: string) => void,
  onProgress?: (p: ProgressEvent) => void,
): () => void {
  const es = new EventSource(`${BASE}/jobs/${jobId}/events`)

  es.onmessage = (e) => {
    const data = e.data as string
    if (data === '__DONE__') {
      onDone()
      es.close()
    } else if (data.startsWith('__ERROR__:')) {
      onError(data.slice('__ERROR__:'.length))
      es.close()
    } else if (data.startsWith('__PROGRESS__:')) {
      try {
        onProgress?.(JSON.parse(data.slice('__PROGRESS__:'.length)) as ProgressEvent)
      } catch {/* 파싱 실패 시 무시 */}
    } else {
      onLog(data)
    }
  }

  es.onerror = () => {
    onError('서버 연결이 끊겼습니다.')
    es.close()
  }

  return () => es.close()
}

// ─── 결과 조회 ────────────────────────────────────────────────────────────────

export interface JobResult {
  summary: string
  speaker_text: string
  combined_text: string
}

export async function fetchJobResult(jobId: string): Promise<JobResult> {
  const res = await fetch(`${BASE}/jobs/${jobId}/result`)
  if (!res.ok) throw new Error(`결과 조회 실패: ${res.status}`)
  return res.json() as Promise<JobResult>
}
