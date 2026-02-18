# Qwen3 TTS Studio API

Qwen3 TTS Studio의 백엔드 API 서비스입니다. FastAPI를 기반으로 구축되었으며, Qwen-TTS 모델을 활용하여 음성 합성 및 목소리 복제(Voice Cloning) 기능을 제공합니다.

## 기술 스택 (Tech Stack)

- **Language**: Python 3.10+
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Deep Learning**: [PyTorch](https://pytorch.org/) (CUDA 12.4), Qwen-TTS
- **Audio Processing**: Pydub, Soundfile
- **Package Manager**: [uv](https://github.com/astral-sh/uv)

## 기능 (Features)

- **음성 목록 조회**: 사용 가능한 음성 프로필 목록을 제공합니다.
- **음성 합성 (TTS)**: 텍스트를 입력받아 음성을 생성합니다.
- **목소리 복제 (Voice Cloning)**: 짧은 녹음 파일을 기반으로 새로운 목소리 프로필을 생성합니다.

## 설치 및 실행 (Installation & Running)

이 프로젝트는 `uv` 패키지 매니저를 사용합니다.

### 1. 사전 요구사항 (Prerequisites)

- Python 3.10 이상
- CUDA 지원 GPU (권장)
- ffmpeg (시스템에 설치되어 있어야 함)

### 2. 의존성 설치 (Install Dependencies)

```bash
uv sync
```

### 3. 서버 실행 (Run Server)

```bash
# 개발 모드 실행
uv run fastapi dev app/main.py --port 8000

# 프로덕션 모드 실행
uv run fastapi run app/main.py --port 8000
```

서버가 실행되면 `http://localhost:8000/docs`에서 Swagger UI를 통해 API 문서를 확인할 수 있습니다.

## 폴더 구조 (Folder Structure)

```
app/
├── main.py            # 애플리케이션 진입점 (FastAPI 앱 설정)
├── routers/           # API 라우트 핸들러 (endpoints)
├── services/          # 비즈니스 로직 (Voice Generate, Clone 등)
├── schemas/           # Pydantic 데이터 모델
├── tts/               # TTS 모델 로딩 및 추론 로직
└── utils/             # 유틸리티 함수
voice_profiles/        # 복제된 음성 프로필 저장소
```

## 환경 변수 (Environment Variables)

필요에 따라 `.env` 파일을 생성하거나 환경 변수를 설정하여 ffmpeg 경로 등을 구성할 수 있습니다. (현재 `main.py`는 Windows 환경의 `LOCALAPPDATA` 경로를 탐색하는 로직이 포함되어 있으나, Linux 환경에서는 시스템 PATH의 ffmpeg를 사용합니다.)