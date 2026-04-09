import streamlit as st
from dotenv import load_dotenv
load_dotenv() # .env 파일의 환경 변수(HF_TOKEN, API KEY)를 불러옵니다.
import os
import tempfile
import time
from audio_extractor import extract_audio_from_video
from stt_processor import process_audio
from summarizer import summarize_text

# HTML for a custom copy button
def copy_button_html(text_to_copy):
    escaped_text = text_to_copy.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
    return f"""
    <button onclick="navigator.clipboard.writeText('{escaped_text}').then(() => alert('Copied!'))" style="background-color: #4CAF50; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; float: right;">
        📋 결괏값 복사하기
    </button>
    <div style="clear: both;"></div>
    """

st.set_page_config(page_title="Minute Second (스마트 회의록)", layout="wide")

st.title("📹 동영상 자동 회의록 생성 서비스")
st.markdown("동영상을 업로드하면 내부에서 오디오만 추출하여 STT로 변환하고 **주요 회의록**을 생성해드립니다.")

# Check for API Key
if not os.environ.get("MINUTE_SECOND_API_KEY"):
    st.warning("⚠️ `.env` 파일에 `MINUTE_SECOND_API_KEY`가 설정되어 있지 않을 수 있습니다.")

uploaded_file = st.file_uploader("동영상 파일 업로드 (.mp4 등)", type=["mp4", "mkv", "avi", "mov"])

if uploaded_file is not None:
    if st.button("분석 시작"):
        # UI Elements for progress
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        
        try:
            # 1. 파일 임시 저장
            status_text.write("⏳ 업로드된 비디오 파일을 임시 저장 중입니다...")
            progress_bar.progress(0.1)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
                tmp_video.write(uploaded_file.read())
                video_file_path = tmp_video.name
            
            # 2. 오디오 추출
            status_text.write("🎵 비디오에서 오디오를 추출하는 중입니다...")
            progress_bar.progress(0.2)
            
            with extract_audio_from_video(video_file_path) as audio_path:
                status_text.write("🎙️ 오디오 추출 완료. STT 처리 중 (이는 시간이 소요될 수 있습니다)...")
                progress_bar.progress(0.4)
                
                # 3. STT 빛 화자 분리
                def update_stt_progress(msg):
                    status_text.write(f"✍️ {msg}")
                    
                combined_text, speaker_text = process_audio(audio_path, progress_callback=update_stt_progress)
                
                progress_bar.progress(0.7)
                status_text.write("🤖 텍스트 변환 완료. 요약본 작성 중...")
                
                # 4. 요약
                summary_markdown = summarize_text(combined_text)
                progress_bar.progress(1.0)
                status_text.write("✅ 모든 작업이 완료되었습니다!")
                
                st.success("데이터 처리 완료!")
                
                tab1, tab2, tab3 = st.tabs(["회의 요약", "화자별 스크립트", "전체 원문"])
                
                with tab1:
                    st.components.v1.html(copy_button_html(summary_markdown), height=45)
                    st.markdown(summary_markdown)
                
                with tab2:
                    st.components.v1.html(copy_button_html(speaker_text), height=45)
                    st.text_area("화자 구분 스크립트", speaker_text, height=400)
                    
                with tab3:
                    st.components.v1.html(copy_button_html(combined_text), height=45)
                    st.text_area("전체 텍스트 원문", combined_text, height=400)
                
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
        finally:
            if 'video_file_path' in locals() and os.path.exists(video_file_path):
                os.remove(video_file_path)
