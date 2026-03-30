# 잠든 서고 (Sleeping Archive)

로컬에서 실행하는 루프형 글쓰기 보조 도구다. 사용자가 플롯을 입력하면 `룬`이 초안을 쓰고, `카논`이 설정과 구조를 검토하고, `에코`가 독자 반응을 남긴 뒤, `룬`이 이를 반영한 최종본을 다시 만든다. 상태, 히스토리, 비용, 로그는 모두 로컬에 저장된다.

## 목적

- 한 번에 완성본을 뽑는 도구가 아니라, `초안 -> 검토 -> 반영 -> 다음 루프 판단` 흐름을 안정적으로 돌리는 글쓰기 작업실을 만든다.
- 검토 결과를 단순 텍스트로 흘려보내지 않고, 다음 루프 판단과 히스토리 비교에 다시 쓸 수 있는 구조 데이터로 남긴다.
- API 키가 없어도 mock 모드로 전체 흐름을 검증할 수 있게 해, 개발과 사용 환경의 간극을 줄인다.

## 현재 상태

- 로컬에서 바로 실행 가능한 MVP를 넘어서, 실제 사용성을 계속 다듬는 단계다.
- 메인 화면은 채팅형 UI이고, 자주 안 보는 정보는 `Workroom`과 `Archive`로 분리되어 있다.
- `카논` 피드백은 `판정 / 설정 / 구조 / 미래 리스크 / 다음 액션` 구조로 저장되고 표시된다.
- `에코` 코멘트는 `반응 / 몰입 / 이탈감` 축으로 구조화되어 저장되고 표시된다.
- 각 루프에는 usage, prompt version, quality 판단, history 파일명이 함께 저장된다.
- 히스토리 검색, 필터, 상세 보기, `.md` / `.json` export가 가능하다.
- 서버 재시작 시 `running` 상태를 복구 정책에 따라 정리한다.
- 실행 중 루프 취소 API와 UI가 있다.
- 시작 타이틀 화면, 입장 연출, 첫 실행/복귀/장기 부재 인사 분기가 있다.
- Gemini API 키가 없으면 mock 모드, 있으면 live 모드로 동작한다.
- Windows용 `.exe` 실행 파일과 바로가기가 있다.

## 핵심 흐름

1. 시작 화면에서 `서고 열기`로 진입한다.
2. 메인 화면에서 플롯과 설정을 정리하고 필요하면 비용을 먼저 추정한다.
3. `룬 초안 -> 카논 피드백 / 에코 코멘트 -> 룬 최종본` 루프를 돈다.
4. 루프마다 조기 종료 여부를 품질 판단으로 계산한다.
5. 결과는 `Workroom`에서 현재 루프 중심으로 보고, `Archive`에서 누적 히스토리를 검색/비교한다.

## 실행 방법

### 1. 가장 쉬운 실행

- 바로가기: `잠든 서고 실행 바로가기.lnk`
- 실행 파일: `dist/SleepingArchive.exe`

실행 파일 버전은 브라우저를 자동으로 열고, 데이터는 `dist/SleepingArchiveData/storage` 아래에 저장된다.

### 2. 로컬 런처 실행

```bash
python launcher.py
```

브라우저 자동 실행을 끄려면 다음처럼 실행하면 된다.

```bash
python launcher.py --no-browser --port 8000
```

### 3. 개발 모드 실행

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

브라우저에서 `http://127.0.0.1:8000` 을 열면 된다.

### 4. 실행 파일 다시 빌드

```powershell
powershell -ExecutionPolicy Bypass -File .\build_launcher.ps1
```

## 환경 변수

```bash
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-2.5-pro
GEMINI_TIMEOUT_SECONDS=120
GEMINI_MAX_RETRIES=2
GEMINI_RETRY_BASE_DELAY_SECONDS=1.5
GEMINI_RETRY_MAX_DELAY_SECONDS=8
GEMINI_INPUT_COST_PER_1M=1.25
GEMINI_INPUT_COST_PER_1M_LARGE=2.50
GEMINI_OUTPUT_COST_PER_1M=10.00
GEMINI_OUTPUT_COST_PER_1M_LARGE=15.00
GEMINI_PRICING_THRESHOLD_TOKENS=200000
```

## 주요 기능

- FastAPI 백엔드 + 정적 프론트엔드
- 룬 / 카논 / 에코 / Sil 페르소나 구조
- 설정 문서 3종 편집
- 비용 추정 UI
- prompt version 메타 저장
- usage / 비용 집계와 루프별 summary 저장
- 구조화된 카논 / 에코 피드백 저장 및 렌더링
- 조기 종료 판단 로직
- 실행 중 루프 취소
- 재시작 시 interrupted run 정리
- 채팅형 메인 화면 + Workroom + Archive
- 히스토리 검색 / 필터 / 상세 보기 / export
- 타이틀 화면과 방문 상태별 인사 분기
- mock / live 모드 전환
- Windows `.exe` 실행 파일

## 저장 위치

소스 실행 기준:

- `storage/settings.json`: 설정 문서
- `storage/loop_state.json`: 현재 루프 상태
- `storage/sil_log.json`: Sil 로그
- `storage/app_meta.json`: 방문 / 누적 루프 메타 정보
- `storage/history/*.json`: 루프별 결과물

실행 파일 기준:

- `dist/SleepingArchiveData/storage/*`

## 프롬프트와 구조 데이터

- 프롬프트 정의는 `backend/personas/prompts.py` 에 모여 있다.
- 각 iteration과 history JSON에는 `prompts` 필드로 사용된 프롬프트 버전이 저장된다.
- 카논 피드백은 `feedback_structured`, 에코 코멘트는 `comment_structured` 필드로 함께 저장된다.
- 프롬프트 문구나 응답 구조를 바꿀 때는 해당 템플릿의 `version`도 함께 올리는 것을 기준으로 한다.

## 테스트 / 검증

```bash
python -m unittest discover -s tests -v
node --check "C:\Users\82104\Desktop\코딩\Sleeping Archive\frontend\app.js"
```

현재 테스트 스위트는 29개이며, 다음 범위를 포함한다.

- prompt version 저장
- Gemini 재시도 / 응답 검증
- mock 모드 전체 흐름
- 루프 취소
- 재시작 복구 정책
- pricing 계산
- 카논 구조화
- 에코 구조화
- 조기 종료 품질 판단
- 방문 인사 분기
- 프론트 최소 상호작용 smoke test

## 프로젝트 구조

```text
backend/
  main.py
  config.py
  models.py
  loop/
  personas/
  pricing.py
  storage/
frontend/
  index.html
  style.css
  app.js
storage/
dist/
  SleepingArchive.exe
  SleepingArchiveData/
tests/
launcher.py
build_launcher.ps1
SleepingArchive.spec
```

## 중간 점검

현재까지의 업데이트는 최초 목적에서 크게 벗어나지 않았다. 채팅형 메인 화면, Workroom/Archive 분리, 구조화된 카논/에코 피드백, 조기 종료 판단 고도화는 모두 `루프를 더 읽기 쉽고, 더 비교하기 쉽고, 다음 행동을 결정하기 쉽게 만든다`는 본래 목적과 맞닿아 있다.

다만 이제부터는 연출이나 화면 장식보다 아래 세 가지를 더 우선하는 편이 좋다.

- 루프 품질을 더 명확히 보여주기: 지금은 score와 reason이 저장되지만, 개선 추세와 비교가 더 잘 보여야 한다.
- 반복 지적을 다음 루프에 다시 연결하기: 같은 약점이 계속 나오면 프롬프트 보정이나 요약 메모에 자동 반영되는 쪽이 효율적이다.
- 작품 단위 문맥 관리 강화: 최근 원문, 요약, 고정 메모를 작품 기준으로 쌓아야 장기 사용성이 살아난다.

## 다음에 집중할 것

- 루프별 품질 점수와 개선 여부를 UI에서 더 명확히 노출
- 반복되는 카논/에코 지적을 다음 프롬프트 보정에 연결
- 작품별 문맥 저장 구조와 자동 요약 기초 추가
- 실행 파일 기동 검증 자동화
