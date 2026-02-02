# Qwen3 TTS Studio API 설치 가이드

Qwen3 TTS 모델을 활용한 음성 복제(Voice Cloning) API 서버입니다.

## 시스템 요구사항

- **Python**: 3.10 이상
- **OS**: Windows, macOS, Linux
- **RAM**: 최소 16GB 권장 (모델 로딩 시 필요)
- **Storage**: 약 10GB (모델 다운로드 용량)

## 사전 설치 항목

### 1. FFmpeg 설치

M4A, MP3 등 다양한 오디오 포맷 지원을 위해 FFmpeg가 필요합니다.

**Windows:**
```powershell
winget install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

### 2. uv 설치 (권장)

[uv](https://docs.astral.sh/uv/)는 빠른 Python 패키지 관리자입니다.

**Windows (PowerShell):**
```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 설치 방법

### 1. 저장소 클론

```bash
git clone https://github.com/your-repo/qwen3-tts-studio-api.git
cd qwen3-tts-studio-api
```

### 2. 의존성 설치

**uv 사용 (권장):**
```bash
uv sync
```

**pip 사용:**
```bash
pip install -e .
```

### 3. (선택) Flash Attention 설치

GPU 사용 시 메모리 효율을 위해 Flash Attention 설치를 권장합니다.

```bash
pip install flash-attn --no-build-isolation
```

> ⚠️ Flash Attention은 CUDA GPU가 필요합니다. CPU만 사용하는 경우 설치하지 않아도 됩니다.

## 서버 실행

### 개발 모드

```bash
uv run fastapi dev
```

서버가 `http://127.0.0.1:8000`에서 실행됩니다.

### 프로덕션 모드

```bash
uv run fastapi run --host 0.0.0.0 --port 8000
```

## API 엔드포인트

### 음성 프로필 저장

새로운 음성 프로필을 생성합니다.

```bash
curl -X POST "http://127.0.0.1:8000/api/voices/save" \
  -H "Content-Type: multipart/form-data" \
  -F "name=my-voice" \
  -F "audio_file=@reference.wav"
```

**지원 오디오 포맷:** WAV, MP3, M4A, FLAC, OGG, AAC, WebM

### 음성 프로필 목록 조회

```bash
curl "http://127.0.0.1:8000/api/voices/list"
```

### TTS 음성 생성

```bash
curl "http://127.0.0.1:8000/api/voices/generate?text=안녕하세요&voice_name=my-voice&language=Korean" \
  --output output.wav
```

**지원 언어:**
- Korean (한국어)
- English (영어)
- Chinese (중국어)
- Japanese (일본어)
- German (독일어)
- French (프랑스어)
- Russian (러시아어)
- Portuguese (포르투갈어)
- Spanish (스페인어)
- Italian (이탈리아어)

## API 문서

서버 실행 후 다음 주소에서 대화형 API 문서를 확인할 수 있습니다:

- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

## 모델 정보

이 프로젝트는 [Qwen3-TTS-12Hz-1.7B-Base](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base) 모델을 사용합니다.

- 최초 실행 시 모델이 자동으로 다운로드됩니다 (~3.8GB)
- 모델은 `~/.cache/huggingface/hub/` 경로에 캐시됩니다

## 문제 해결

### "SoX could not be found" 경고

이 경고는 무시해도 됩니다. SoX가 없어도 정상 작동합니다.

### "flash-attn is not installed" 경고

CPU 모드에서는 이 경고를 무시해도 됩니다. GPU 사용 시에만 Flash Attention이 필요합니다.

### M4A 파일 업로드 실패

FFmpeg가 설치되어 있는지 확인하세요:

```bash
ffmpeg -version
```

설치 후에는 터미널을 재시작해야 합니다.

### Windows에서 "Couldn't find ffmpeg" 오류

winget으로 FFmpeg를 설치해도 PATH에 자동으로 추가되지 않습니다.

**1. FFmpeg 설치 확인:**
```powershell
winget install --id Gyan.FFmpeg -e --source winget
```

**2. PATH에 FFmpeg 추가 (영구 설정):**
```powershell
[Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin", "User")
```

**3. 터미널 재시작 후 확인:**
```powershell
ffmpeg -version
```

> ⚠️ FFmpeg 버전이 다를 경우, 실제 설치 경로를 확인하세요:
> ```powershell
> Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gyan.FFmpeg*" -Recurse -Filter "ffmpeg.exe" | Select-Object FullName
> ```

### 메모리 부족 오류

모델 로딩에 약 8-16GB RAM이 필요합니다. 메모리가 부족한 경우:

1. 다른 프로그램을 종료하세요
2. 가상 메모리(스왑)를 늘리세요

## 라이선스

이 프로젝트는 Apache 2.0 라이선스를 따릅니다.
