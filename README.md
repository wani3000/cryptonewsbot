# cryptonewsbot

## 프로젝트 개요

`cryptonewsbot`은 지난 24시간 내의 암호화폐 산업 관련 뉴스를 수집하고, 중복을 제거한 뒤 핵심 내용을 정리/요약하고, 사용자가 미리 정의한 관점과 포맷에 따라 X(구 Twitter)용 게시글로 재가공하여 매일 텔레그램으로 전달하는 자동화 봇을 만드는 프로젝트다.

## 현재 작업 컨텍스트

현재는 Python 3.9 표준 라이브러리 중심 MVP가 구현된 상태이며, 운영용 기본 피드 세트와 로컬 `.env` 기반 텔레그램 설정까지 반영되어 있다. 하나의 실행 엔트리포인트에서 RSS/Atom 기반 뉴스 수집, 정규화/중복 제거, 스타일 프로필 기반 relevance filtering, X용 포스트 생성, 선택적 LLM 재작성, 텔레그램 전달, SQLite 저장, 피드별 수집 상태 기록까지 연결되어 있다. 텔레그램 토큰과 `chat_id` 연결, 테스트 메시지 전송, 실제 운영 모드 전환까지 완료됐고, OpenAI `gpt-4.1-mini` 재작성 경로도 코드상 연결되어 있다. 현재 콘텐츠는 ChainBounty 보안 리포팅 기준에 맞춰 `해킹/사기/스캠/자금세탁/수사` 성격의 기사만 더 강하게 통과시키고, 텔레그램은 `뉴스 1개 -> ChainBounty 게시글 1개` 순서로 연속 전송한다. 2026-03-18부터는 수집 단계에서도 `exploit`, `hack`, `scam`, `phishing`, `drain`, `vulnerability`, `breach`, `compromise` 키워드가 없는 뉴스는 아예 제외하도록 강화했다.

2026-03-18 기준으로 새로 확인된 사실은 두 가지다. 첫째, 문서 일부가 오래된 상태였고 현재 Git/Jira/테스트 상태를 정확히 반영하지 못하고 있었다. 둘째, 실제 코드에서는 파이프라인 테스트 3건이 깨져 있었는데 원인은 로직 회귀가 아니라 `tests/test_pipeline.py`의 RSS fixture 날짜가 현재 시점 기준 24시간 창 밖으로 밀려난 것이었다. 이 문제는 동적 fixture 날짜 생성으로 복구했고 현재 `unittest` 전체 18건이 다시 통과한다.

## 핵심 디렉토리 구조

- `/Users/hanwha/Documents/GitHub/cryptonewsbot`
  - 프로젝트 루트
- [README.md](/Users/hanwha/Documents/GitHub/cryptonewsbot/README.md)
  - 온보딩용 현재 상태 문서
- [research.md](/Users/hanwha/Documents/GitHub/cryptonewsbot/research.md)
  - 현재 시스템 상태와 조사 결과 기록
- [plan.md](/Users/hanwha/Documents/GitHub/cryptonewsbot/plan.md)
  - 구현 전략, 변경 대상, Todo, 인수인계 기록
- [config](/Users/hanwha/Documents/GitHub/cryptonewsbot/config)
  - 스타일 프로필과 운영용 피드 설정 JSON 위치
- [.env](/Users/hanwha/Documents/GitHub/cryptonewsbot/.env)
  - 로컬 비밀 설정 파일
- [style-guide.html](/Users/hanwha/Documents/GitHub/cryptonewsbot/style-guide.html)
  - ChainBounty 글쓰기 가이드 HTML 보관본
- [src/cryptonewsbot](/Users/hanwha/Documents/GitHub/cryptonewsbot/src/cryptonewsbot)
  - 애플리케이션 코드
- [tests](/Users/hanwha/Documents/GitHub/cryptonewsbot/tests)
  - 기본 단위/통합 테스트

## 기술 스택 요약

- 현재 구현 기준 스택
  - 언어: Python 3.9
  - 저장소: SQLite (`sqlite3`)
  - 뉴스 수집: RSS/Atom XML 파싱 (`urllib`, `xml.etree.ElementTree`)
  - 설정 관리: 환경 변수 + `.env` + JSON 스타일 프로필
  - 선택적 재작성: OpenAI-compatible Chat Completions 또는 Gemini 2.0 Flash HTTP 호출
  - 전달 채널: Telegram Bot API (`urllib`)
  - 테스트: `unittest`
  - 게시글 타깃 포맷: X용 짧은 포스트 묶음
  - 전달 포맷: 텔레그램에서 뉴스 요약과 생성 게시글을 1:1 쌍으로 순차 전송

초기 MVP는 외부 의존성을 최소화해 로컬에서 바로 실행 가능한 구조로 구현한다.

## 에이전트 간 역할 분담

- 현재 참여 에이전트
  - Codex: 저장소 상태 조사, 문서 작성/유지, MVP 구현, 테스트, 실행 검증, 2026-03-18 재투입 후 테스트 안정화 및 문서/Jira 대조 담당
- 아직 합류하지 않은 에이전트
  - 미정

새 에이전트가 합류하면 이 섹션을 즉시 업데이트해야 한다.

## 작업 진행 상태

- 현재 단계: 재투입 점검 및 비UI 유지보수 진행 중
- 세부 상태
  - 저장소 조사: 진행 완료
  - 기존 코드 분석: 2026-03-18 기준으로 재검증 중
  - 구현 계획 수립: 기존 계획 존재, 최신 상태 반영 필요
  - 실제 코드 구현: MVP 완료
  - 템플릿 자동 선택: 1차 완료
  - 테스트/로컬 검증: 파이프라인 테스트 fixture 날짜 이슈 복구 후 `18`건 통과
  - 로컬 배포: macOS `launchd` 기준 구성 완료
  - 현재 처리 중 대표 태스크
    - 비UI 유지보수: 테스트 안정화, 문서 최신화, Jira 매핑 재확인
  - 다음 하위 태스크
    - accessible Jira 안에서 `cryptonewsbot` 전용 이슈 구조가 실제로 존재하는지 추가 확인하고, 확인 불가 시 문서에 증거 기반으로 명시

## UI 승인 대기 목록

- 현재 확인된 UI 승인 대기 이슈 없음
- UI 컴포넌트, 레이아웃, 스타일 작업은 개발자 승인 전까지 진행하지 않음

## 인계 요약

- 직전 에이전트까지의 구현 결과
  - ChainBounty 보안 기사 필터링, subtype별 템플릿, 텔레그램 순차 전송, 포맷팅 가이드, 로컬 `launchd` 배포 구성이 반영된 상태였다.
- 2026-03-18 재투입 에이전트 확인 결과
  - GitHub 원격 `origin/main`과 로컬 `main`은 동일하다.
  - accessible Jira 프로젝트 목록에서는 `cryptonewsbot` 또는 `ChainBounty`로 직접 식별되는 이슈 구조를 아직 찾지 못했다.
  - 코드 기준 실제 회귀는 파이프라인 테스트 fixture 날짜 경직성뿐이었고, 해당 문제는 수정 완료했다.

## 참고 파일 안내

- [research.md](/Users/hanwha/Documents/GitHub/cryptonewsbot/research.md)
  - 현재 저장소에 무엇이 있고 무엇이 없는지, 기존 시스템 동작 여부, 조사 범위를 확인할 수 있다.
- [plan.md](/Users/hanwha/Documents/GitHub/cryptonewsbot/plan.md)
  - 무엇을 어떤 순서로 구현할지, 어떤 파일이 추가/변경될지, 기술 선택과 트레이드오프를 확인할 수 있다.

## 현재 시점 핵심 사실

- 이 저장소는 현재 Python MVP가 구현되어 있고 GitHub 원격과 동기화되는 Git 저장소다.
- 첫 구현은 외부 의존성을 최소화한 단일 Python 애플리케이션 형태다.
- 실제 운영을 위해서는 RSS 피드 URL, 텔레그램 토큰/채팅 ID, 스타일 프로필을 사용자 환경에 맞게 넣어야 한다.
- 기본 운영 피드 세트는 [config/feeds/crypto_sources.json](/Users/hanwha/Documents/GitHub/cryptonewsbot/config/feeds/crypto_sources.json)에 들어 있다.
- 같은 기사 재전송 방지는 `CRYPTO_NEWSBOT_REPEAT_SUPPRESSION_HOURS`로 제어하며, 기본값은 `24`시간이다.
- 현재 배포 방식은 macOS `launchd`이며, 개발용 저장소와 분리된 로컬 런타임 복사본을 `~/bots/cryptonewsbot`에 배치해 그 경로를 기준으로 실행한다.
- 기본 스케줄은 매일 09:00 로컬 시간이다.
- [deploy_local_runtime.sh](/Users/hanwha/Documents/GitHub/cryptonewsbot/scripts/deploy_local_runtime.sh)가 현재 작업본을 `~/bots/cryptonewsbot`으로 동기화한 뒤, 그 위치에서 [install_launchd.sh](/Users/hanwha/Documents/GitHub/cryptonewsbot/scripts/install_launchd.sh)를 실행한다.
- 이 구조의 목적은 `Documents` 보호 폴더를 피해서 `launchd`가 안정적으로 스크립트와 DB에 접근하게 만드는 것이다.
