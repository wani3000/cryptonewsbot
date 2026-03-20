# cryptonewsbot

## 프로젝트 개요

`cryptonewsbot`은 지난 24시간 내의 암호화폐 산업 관련 뉴스를 수집하고, 중복을 제거한 뒤 핵심 내용을 정리/요약하고, 사용자가 미리 정의한 관점과 포맷에 따라 X(구 Twitter)용 게시글로 재가공하여 매일 텔레그램으로 전달하는 자동화 봇을 만드는 프로젝트다.

## 현재 작업 컨텍스트

현재는 Python 3.9 중심 MVP가 구현된 상태이며, 운영용 기본 피드 세트와 로컬 `.env` 기반 텔레그램 설정까지 반영되어 있다. 하나의 실행 엔트리포인트에서 RSS/Atom 기반 뉴스 수집, 정규화/중복 제거, 스타일 프로필 기반 relevance filtering, X용 포스트 생성, 선택적 LLM 재작성, 텔레그램 전달, SQLite 저장, 피드별 수집 상태 기록까지 연결되어 있다. 텔레그램 토큰과 `chat_id` 연결, 테스트 메시지 전송, 실제 운영 모드 전환까지 완료됐고, OpenAI `gpt-4.1-mini` 실호출이 성공해 LLM 재작성 경로도 활성화된 상태다. 최근에는 사용자 제공 `ChainBounty Writing Style Guide`를 기준으로 프롬프트와 프로필을 재조정했고, 텔레그램은 `뉴스 1개 -> ChainBounty 게시글 1개` 순서로 연속 전송하도록 바뀌었다. 추가로 영구 dedupe 때문에 재실행 시 생성이 비는 문제를 제거했고, 대신 최근 실제 전송된 기사만 일정 시간 동안 다시 보내지 않도록 delivery-aware dedupe를 넣었다. ChainBounty용 보안 키워드 relevance도 강화했다. 현재는 일반 시장 뉴스보다 해킹, 사기, 스캠, 자금세탁, 수사 관련 기사만 더 강하게 통과시키고, 생성문 끝에는 ChainBounty 커뮤니티 유입 CTA를 붙인다. Incident 템플릿도 이제 `drainer / phishing / bridge_hack / sanction_seizure / pyramid_scam` 세부 유형별로 갈라진다. 최근 품질 튜닝으로 X용 본문은 길이 제한 없이 생성하고 필요하면 이후 스레드로 분할할 수 있게 했으며, Telegram용 긴 분석 본문은 별도로 생성한다. 이제 LLM 프롬프트에도 subtype별 문체 규칙, ChainBounty 분석 포인트, Telegram 확장 깊이 지시가 함께 들어가며, LLM fallback 경로도 같은 subtype 가이드를 재사용해 Telegram 본문을 더 깊게 만든다. 핵심 문장과 제목에는 기사 유형에 맞는 이모지를 붙여 가독성을 높이되, 과장된 감정형 이모지는 피한다. 최종 전송 본문에서는 Markdown bold 표기인 `**`를 제거해 Telegram에서 그대로 노출되지 않도록 정리했다. 2026-03-19 재검증에서는 기본 `unittest discover` 경로로는 `src` 레이아웃 import가 재현되지 않았고, 고정 날짜 RSS 픽스처가 24시간 윈도우 밖으로 밀려 파이프라인 테스트가 실패함을 확인했다. 현재는 [run_tests.sh](/Users/chulwan/Documents/GitHub/cryptonewsbot/scripts/run_tests.sh)로 표준 테스트 진입점을 추가하고 파이프라인 테스트 픽스처를 현재 시점 기준으로 갱신해 재현 가능한 검증 상태를 복구했다. 2026-03-20 기준으로는 선택적 X 자동 게시 채널까지 연결되어, `cryptonewsbot`가 생성한 ChainBounty 포스트를 regular tweet 또는 thread로 게시하고 X 게시 이력도 별도 저장할 수 있다. 이 X 채널은 `.env` 설정과 자격 증명이 있을 때만 활성화된다. 같은 날 뉴스 수집 소스도 16개 기본 피드로 확장해 미국, 한국, 유럽, 캐나다, 일본, 중국 권역의 매체/규제기관/Google News 검색 RSS를 함께 수집하고, 한국어/일본어/중국어 보안 키워드도 relevance 필터에 반영했다. 이어서 소스 카테고리별 우선순위도 넣어 `regulator > media > search-aggregated` 순으로 직접 소스가 검색 집계 소스보다 먼저 선택되도록 정렬했다. 추가로 유사 사건을 하나의 story cluster로 접어 대표 기사만 남기고, LLM 프롬프트에는 ChainBounty 회사/조사팀 관점을 더 강하게 주입하도록 바뀌었다. 그리고 생성 스타일도 단일 톤에서 4개 회전형 writing style로 확장해, `incident_briefing / operator_alert / casefile_note / community_watch`가 배치 안에서 겹치지 않게 순환하고 날짜 기준으로 시작 위치도 바뀌게 했다. 이번 단계에서는 스타일 이름뿐 아니라 opening pattern과 analyst phrasing도 스타일별로 달라지게 했고, 마지막에 실제 사용된 스타일을 DB에 저장해 다음 실행이 그 다음 스타일에서 이어지도록 만들었다. 추가로 소스에는 `core / extended` tier를 붙여 priority에 반영했고, search-aggregated 경로에서는 프로모션성·SEO성 제목과 약한 보안 신호를 더 강하게 제거하도록 false-positive suppression을 강화했다.

## 핵심 디렉토리 구조

- `/Users/chulwan/Documents/GitHub/cryptonewsbot`
  - 프로젝트 루트
- [README.md](/Users/chulwan/Documents/GitHub/cryptonewsbot/README.md)
  - 온보딩용 현재 상태 문서
- [research.md](/Users/chulwan/Documents/GitHub/cryptonewsbot/research.md)
  - 현재 시스템 상태와 조사 결과 기록
- [plan.md](/Users/chulwan/Documents/GitHub/cryptonewsbot/plan.md)
  - 구현 전략, 변경 대상, Todo, 인수인계 기록
- [config](/Users/chulwan/Documents/GitHub/cryptonewsbot/config)
  - 스타일 프로필과 운영용 피드 설정 JSON 위치
- [.env](/Users/chulwan/Documents/GitHub/cryptonewsbot/.env)
  - 로컬 비밀 설정 파일
- [style-guide.html](/Users/chulwan/Documents/GitHub/cryptonewsbot/style-guide.html)
  - ChainBounty 글쓰기 가이드 HTML 보관본
- [src/cryptonewsbot](/Users/chulwan/Documents/GitHub/cryptonewsbot/src/cryptonewsbot)
  - 애플리케이션 코드
- [tests](/Users/chulwan/Documents/GitHub/cryptonewsbot/tests)
  - 기본 단위/통합 테스트
- [scripts/run_tests.sh](/Users/chulwan/Documents/GitHub/cryptonewsbot/scripts/run_tests.sh)
  - `PYTHONPATH=src`를 포함한 표준 테스트 실행 스크립트
- [chainbounty_x_integration.md](/Users/chulwan/Documents/GitHub/cryptonewsbot/chainbounty_x_integration.md)
  - ChainBounty X 자동 게시 통합 설계 메모

## 기술 스택 요약

- 현재 구현 기준 스택
  - 언어: Python 3.9
  - 저장소: SQLite (`sqlite3`)
  - 뉴스 수집: RSS/Atom XML 파싱 (`urllib`, `xml.etree.ElementTree`)
  - 설정 관리: 환경 변수 + `.env` + JSON 스타일 프로필
  - 선택적 재작성: OpenAI-compatible Chat Completions 또는 Gemini 2.0 Flash HTTP 호출
  - 전달 채널: Telegram Bot API (`urllib`)
  - 선택적 X 게시: Tweepy 기반 X API v2 클라이언트
  - 테스트: `unittest`
  - 게시글 타깃 포맷: X용 짧은 포스트 묶음
  - 전달 포맷: 텔레그램에서 뉴스 요약과 생성 게시글을 1:1 쌍으로 순차 전송

초기 MVP는 외부 의존성을 최소화해 로컬에서 바로 실행 가능한 구조로 구현한다.

## 에이전트 간 역할 분담

- 현재 참여 에이전트
  - Codex: 저장소 상태 조사, 문서 작성/유지, MVP 구현, 테스트, 실행 검증 담당
  - Codex (2026-03-19 재투입): 문서/Git/Jira 정합성 재검증, 테스트 재현성 복구 담당
- 아직 합류하지 않은 에이전트
  - 미정

새 에이전트가 합류하면 이 섹션을 즉시 업데이트해야 한다.

## 작업 진행 상태

- 현재 단계: ChainBounty X 자동 게시 1차 통합 완료, 지역별 뉴스 수집 확장 1차 완료
- 세부 상태
  - 저장소 조사: 진행 완료
  - 기존 코드 분석: 실제 구현물 기준으로 재분석 완료
  - 구현 계획 수립: 실행 반영 완료
  - 실제 코드 구현: MVP 완료
  - 템플릿 자동 선택: 1차 완료
  - 테스트/로컬 검증: `zsh scripts/run_tests.sh` 기준 재현 가능 상태 유지, 현재 38개 테스트 통과
  - 로컬 배포: macOS `launchd` 기준 구성 완료
  - GitHub 동기화: `main` 확인, 워킹트리 깨끗함 확인 후 시작했으나 `git fetch origin` / `git pull --ff-only`는 `Could not resolve host: github.com`로 실패
  - Jira 대조: ChainBounty X 연동용 태스크 `CHAIN-1`, `CHAIN-2`, `CHAIN-3`와 후속 품질 작업 `CHAIN-4`, `CHAIN-5`, `CHAIN-6`, `CHAIN-7`, `CHAIN-8` 생성 완료

## UI 승인 대기 목록

- 접근 가능한 문서와 Jira 조회 범위 기준 신규 `[UI]` 승인 대기 이슈는 확인되지 않았다.

## 인계 요약

- 이전 인계 히스토리
  - 2026-03-10까지 MVP 구현, OpenAI 재작성 경로 활성화, `launchd` 런타임 분리, 반복 전송 suppression, 텔레그램 쌍 전송이 반영되어 있었다.
- 현재 에이전트 인계 수락
  - 2026-03-19에 `README.md -> research.md -> plan.md` 순서로 재검토하고, Git 최신 상태 확인을 시도했으며, 테스트 재현성 복구를 우선 비UI 작업으로 이어받았다.
  - `subtype별 LLM 문체 차이와 분석 깊이 추가 튜닝`을 완료했다. subtype 가이드를 X/Telegram 프롬프트와 fallback Telegram 본문에 공통 반영했다.
  - 다음 우선 비UI 작업은 운영 배포 방식 확정과 Gemini quota 검증이다. Gemini quota 검증은 외부 네트워크/API 상태 확인이 필요해 별도 검증 조건이 남아 있다.

## 참고 파일 안내

- [research.md](/Users/chulwan/Documents/GitHub/cryptonewsbot/research.md)
  - 현재 저장소에 무엇이 있고 무엇이 없는지, 기존 시스템 동작 여부, 조사 범위를 확인할 수 있다.
- [plan.md](/Users/chulwan/Documents/GitHub/cryptonewsbot/plan.md)
  - 무엇을 어떤 순서로 구현할지, 어떤 파일이 추가/변경될지, 기술 선택과 트레이드오프를 확인할 수 있다.

## 현재 시점 핵심 사실

- 이 저장소는 2026-03-10 기준 Python MVP가 구현되어 있다.
- 현재 GitHub 원격 `wani3000/cryptonewsbot`을 기준으로 clone된 Git 저장소다.
- 첫 구현은 외부 의존성을 최소화한 단일 Python 애플리케이션 형태다.
- 실제 운영을 위해서는 RSS 피드 URL, 텔레그램 토큰/채팅 ID, 스타일 프로필을 사용자 환경에 맞게 넣어야 한다.
- 기본 운영 피드 세트는 [config/feeds/crypto_sources.json](/Users/chulwan/Documents/GitHub/cryptonewsbot/config/feeds/crypto_sources.json)에 들어 있으며, 현재 기본값은 글로벌 매체 RSS, 규제기관 RSS, 국가별 Google News 검색 RSS를 합쳐 총 16개 소스다.
- 같은 기사 재전송 방지는 `CRYPTO_NEWSBOT_REPEAT_SUPPRESSION_HOURS`로 제어하며, 기본값은 `24`시간이다.
- 현재 배포 방식은 macOS `launchd`이며, 개발용 저장소와 분리된 로컬 런타임 복사본을 `~/bots/cryptonewsbot`에 배치해 그 경로를 기준으로 실행한다.
- 기본 스케줄은 매일 08:00 로컬 시간이다.
- [deploy_local_runtime.sh](/Users/chulwan/Documents/GitHub/cryptonewsbot/scripts/deploy_local_runtime.sh)가 현재 작업본을 `~/bots/cryptonewsbot`으로 동기화한 뒤, 그 위치에서 [install_launchd.sh](/Users/chulwan/Documents/GitHub/cryptonewsbot/scripts/install_launchd.sh)를 실행한다.
- 이 구조의 목적은 `Documents` 보호 폴더를 피해서 `launchd`가 안정적으로 스크립트와 DB에 접근하게 만드는 것이다.
- 현재 운영 런타임은 `~/bots/cryptonewsbot`, LaunchAgent는 매일 08:00에 해당 런타임에서 실행되도록 재설치된 상태다.
- 최신 테스트 명령은 `zsh scripts/run_tests.sh`다.
- X 자동 게시 채널은 `CRYPTO_NEWSBOT_ENABLE_X_POSTING=true`와 Twitter API 자격 증명이 있을 때만 동작한다.
- X 게시 이력은 Telegram 이력과 별도로 저장되며, root tweet id도 함께 기록한다.
