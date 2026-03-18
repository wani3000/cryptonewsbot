# plan.md

## 문서 목적

이 문서는 `cryptonewsbot` 구현 전에 무엇을 어떤 방식으로 만들지 합의하기 위한 실행 계획서다. 실제 코드 수정보다 먼저 작성되며, 이후 피드백과 구현 결과를 계속 반영한다.

## 현재 전제

- 저장소는 문서 + Python MVP 코드가 존재하는 상태다.
- Git 저장소는 초기화되어 있으며 GitHub 원격과 연결되어 있다.
- 기존 코드, CLI 엔트리포인트, SQLite 스키마, 텔레그램/LLM/RSS 어댑터가 이미 존재한다.
- 로컬 환경에서는 `Python 3.9.6` 사용 가능, `pytest`와 `uv`는 기본 제공되지 않는다.
- 현재 시점의 계획은 "기존 MVP 유지보수 + 문서/Jira/테스트 상태 동기화 + 비UI 운영 안정화"다.

## 문제 해결 전략

핵심 문제는 세 가지다.

1. 지난 24시간의 암호화폐 산업 뉴스를 안정적으로 수집해야 한다.
2. 그 뉴스들을 단순 복붙이 아니라 사용자 맞춤형 X 포스트로 재가공해야 한다.
3. 이 전체 과정을 매일 자동 실행하여 텔레그램으로 전달해야 한다.

초기 MVP는 다음 원칙으로 접근한다.

- 복잡한 분산 구조보다 단일 애플리케이션으로 시작한다.
- 소스 수집, 정규화, 분석, 재작성, 전달을 명확한 계층으로 분리한다.
- 뉴스 원문과 생성 결과를 저장해 중복 처리와 재실행을 가능하게 한다.
- 텔레그램 전송 전에 사람이 검토 가능한 중간 산출물 구조를 남긴다.

현재 이 전략은 MVP 코드에 반영되었다.

## 제안 아키텍처

초기 MVP 제안:

- 런타임: Python 3.9
- 애플리케이션 형태: CLI + cron 친화적 단일 실행 엔트리포인트
- 데이터 저장: SQLite (`sqlite3`)
- DB 레이어: 직접 SQL 스키마 관리
- 스케줄링: 외부 cron 또는 스케줄러가 호출할 단일 명령 제공
- 텔레그램 연동: Telegram Bot API 직접 호출
- 뉴스 수집: RSS/Atom 어댑터 기반
- 재작성 계층: 규칙 기반 생성기 + 향후 LLM 확장 포인트

이 선택의 이유:

- Python은 RSS 파싱, 스케줄링, 텔레그램 연동에 적합하다.
- 표준 라이브러리 중심 구현은 현재 환경에서 바로 실행/검증이 가능하다.
- SQLite는 로컬 MVP에서 셋업 비용이 낮다.
- 어댑터 구조를 두면 향후 LLM 공급자와 수집 소스 교체가 쉽다.

## 예상 디렉토리 구조

```text
/Users/hanwha/Documents/GitHub/cryptonewsbot
├── README.md
├── research.md
├── plan.md
├── pyproject.toml
├── .env.example
├── .env
├── config/
│   ├── feeds/
│   │   └── crypto_sources.json
│   └── style_profile.example.json
├── src/cryptonewsbot/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   └── interfaces/
└── tests/
```

## 레이어별 설계 방향

### Domain

- `Article`
- `GeneratedPost`
- `UserPreference`

도메인에서 유지할 책임:

- 뉴스 엔티티 표준 필드 정의
- 중복 판정에 필요한 키 구성
- X 포스트 제약 조건 정의

### Application

- `collect_recent_articles`
- `deduplicate_articles`
- `summarize_articles`
- `generate_posts_for_x`
- `send_digest_to_telegram`

이 레이어는 유스케이스를 orchestration 한다.

### Infrastructure

- RSS/API 수집기
- DB 리포지토리
- Telegram 클라이언트
- 실행 로그 저장

### Interfaces

- CLI 엔트리포인트
- 수동 실행 커맨드
- 향후 관리용 admin interface 가능

## 데이터 모델 초안

```python
class Article:
    id: UUID
    source_name: str
    source_url: str
    canonical_url: str
    title: str
    published_at: datetime
    summary: str | None
    content: str | None
    fingerprint: str
    collected_at: datetime

class GeneratedPost:
    id: UUID
    article_id: UUID
    style_profile_id: UUID
    platform: Literal["x"]
    body: str
    headline: str
    created_at: datetime
```

## 유스케이스 흐름 초안

```text
run_daily_digest()
  -> load user preferences
  -> collect articles from enabled sources for last 24h
  -> normalize article fields
  -> deduplicate by canonical_url + fingerprint
  -> rank/filter relevant articles
  -> summarize each article or cluster
  -> generate X-ready posts using user profile
  -> bundle digest message
  -> send to Telegram
  -> persist execution result
```

## Pseudocode

```python
def run_daily_digest(now: datetime) -> None:
    window_start = now - timedelta(hours=24)
    prefs = preference_repo.get_active_profile()
    raw_articles = collector.collect_since(window_start)
    normalized = [normalizer.normalize(item) for item in raw_articles]
    unique_articles = deduplicator.filter_new(normalized)
    relevant_articles = relevance_filter.select(unique_articles, prefs)
    summaries = summarizer.summarize_batch(relevant_articles)
    posts = x_post_generator.generate(summaries, prefs)
    telegram_message = digest_formatter.format(posts, summaries)
    digest_repo.save_run(now, relevant_articles, posts)
    telegram_client.send_message(telegram_message)
```

## 변경이 필요한 파일 목록

초기 생성은 완료되었다. 후속 개선 시 주요 변경 지점은 아래와 같다.

- `/Users/hanwha/Documents/GitHub/cryptonewsbot/pyproject.toml`
- `/Users/hanwha/Documents/GitHub/cryptonewsbot/.env.example`
- `/Users/hanwha/Documents/GitHub/cryptonewsbot/config/style_profile.example.json`
- `/Users/hanwha/Documents/GitHub/cryptonewsbot/src/cryptonewsbot/main.py`
- `/Users/hanwha/Documents/GitHub/cryptonewsbot/src/cryptonewsbot/config.py`
- `/Users/hanwha/Documents/GitHub/cryptonewsbot/src/cryptonewsbot/database.py`
- `/Users/hanwha/Documents/GitHub/cryptonewsbot/src/cryptonewsbot/domain/*`
- `/Users/hanwha/Documents/GitHub/cryptonewsbot/src/cryptonewsbot/application/*`
- `/Users/hanwha/Documents/GitHub/cryptonewsbot/src/cryptonewsbot/infrastructure/*`
- `/Users/hanwha/Documents/GitHub/cryptonewsbot/src/cryptonewsbot/interfaces/*`
- `/Users/hanwha/Documents/GitHub/cryptonewsbot/tests/*`

## 구현 시 고려 사항

- 뉴스 소스 신뢰도와 라이선스 이슈를 검토해야 한다.
- 직접 크롤링보다 RSS/API 우선 접근이 초기 리스크를 줄인다.
- 중복 제거는 URL 기준만으로는 부족할 수 있어 제목/본문 fingerprint가 필요하다.
- X 포스트 생성은 톤 유지와 사실 보존 사이의 균형이 필요하다.
- 텔레그램 메시지는 너무 길어지면 가독성이 떨어지므로 digest 포맷 설계가 중요하다.

## 트레이드오프

- SQLite vs PostgreSQL
  - SQLite는 빠른 시작에 유리하다.
  - PostgreSQL은 동시성, 운영성, 검색 기능 확장에 유리하다.
- 배치 중심 vs 항상 켜진 봇
  - 배치 중심은 단순하다.
  - 항상 켜진 봇은 명령 처리와 관리 기능 확장에 유리하다.
- 기사별 개별 포스트 생성 vs 주제별 묶음 생성
  - 기사별은 단순하다.
  - 주제별 묶음 생성은 사용자 가치가 더 높지만 난도가 올라간다.

## 기술적 제약 및 요구사항

- 매일 실행 가능한 자동화 구조여야 한다.
- 최근 24시간 윈도우를 기준으로 동작해야 한다.
- 사용자가 미리 입력한 스타일/관점 정보를 반영해야 한다.
- X에 올릴 수 있는 길이와 톤을 고려해야 한다.
- 텔레그램 전송 실패 시 재시도 또는 로그 추적이 가능해야 한다.

## Iteration

### Iteration 1

- 상태: 승인 후 실행 중
- 가정
  - Python 3.9 표준 라이브러리 중심 MVP가 가장 빠르다.
  - 데이터 저장이 필요하다.
  - 초기 수집은 RSS 우선이 적절하다.
- 피드백 대기 항목
  - 사용자가 원하는 언어/런타임 선호
  - 텔레그램 봇이 단순 push-only인지, 명령 인터페이스도 필요한지
  - X 게시글 출력 형식이 단문 목록인지 스레드형인지

### Iteration 2

- 상태: 구현 완료
- 전략 변경
  - 외부 의존성 설치가 전제되지 않은 환경이므로 SQLAlchemy/Alembic/APScheduler는 초기 MVP에서 제외
  - SQLite + `sqlite3`, `unittest`, `urllib` 기반으로 구현
- 이유
  - 현재 환경에서 바로 실행 가능해야 한다.
  - 핵심 가치인 파이프라인 연결을 우선 검증해야 한다.

### Iteration 3

- 상태: 운영 준비 반영 완료
- 변경 사항
  - 기본 운영 피드 설정 JSON 추가
  - RSS뿐 아니라 Atom 피드 파싱 지원
  - 피드별 fetch 결과를 DB와 digest에 기록
  - `CRYPTO_NEWSBOT_FEED_URLS`가 비어 있을 때 설정 파일 fallback 사용
- 이유
  - 실제 운영에서는 소스 관리와 장애 가시성이 필요하다.

### Iteration 4

- 상태: 텔레그램 연결 완료
- 변경 사항
  - `.env` 자동 로딩 추가
  - `.gitignore`에 `.env`, DB 파일 추가
  - `telegram-get-updates`, `telegram-send-test` 커맨드 추가
- 이유
  - 실제 운영 연결에서 비밀값 관리와 진단 경로가 필요하다.

### Iteration 5

- 상태: 콘텐츠 품질 개선 진행 중
- 변경 사항
  - ChainBounty 보안 기사 중심 relevance filtering 강화
  - incident subtype별 세부 템플릿 분화
  - X용 장문 본문과 Telegram용 긴 분석 본문 분리
  - 텔레그램 뉴스 제목과 생성문 도입부에 기사 유형별 이모지 추가
- 이유
  - 해킹/사기/수사 성격을 더 명확히 드러내고 텔레그램 가독성을 높이기 위함

### Iteration 6

- 상태: 로컬 배포 반영 완료
- 변경 사항
  - `scripts/run_daily.sh` 추가
  - `deploy/com.chainbounty.cryptonewsbot.daily.plist.template` 추가
  - `scripts/install_launchd.sh` 추가
  - macOS `launchd` 기준 매일 09:00 실행 배포 경로 문서화
- 이유
  - 현재 사용자 환경이 macOS이고, 별도 서버 없이도 가장 단순하게 매일 자동 실행할 수 있기 때문

### Iteration 7

- 상태: 운영 제약 확인됨
- 변경 사항
  - `launchd` 실제 실행 로그 검증
  - 저장소가 `Documents` 아래에 있어 `Operation not permitted`가 발생함을 확인
- 이유
  - 배포 정의와 실제 운영 가능성은 다르며, 현재 제약은 코드가 아니라 macOS 보호 폴더 접근 정책이기 때문

### Iteration 8

- 상태: 반복 전송 방지 반영 완료
- 변경 사항
  - `delivered_articles` 테이블 추가
  - 최근 실제 전송된 기사 fingerprint/canonical URL 기준 suppression 추가
  - dry-run 반복 생성은 유지하고, 실제 전송된 기사만 다음 실행에서 차단하도록 테스트 추가
- 이유
  - 같은 기사나 사실상 같은 게시글이 텔레그램에 반복 전송되는 운영 이슈를 막기 위함

### Iteration 9

- 상태: 로컬 Mac 상시 운영 경로 전환 진행 중
- 변경 사항
  - 스크립트들의 저장소 경로 하드코딩 제거
  - `~/bots/cryptonewsbot` 런타임 복사본 동기화 스크립트 추가
  - LaunchAgent가 개발용 `Documents` 경로 대신 런타임 경로를 실행하도록 전환
- 이유
  - macOS 보호 폴더 제약 없이 `launchd`가 안정적으로 실행되게 만들기 위함

### Iteration 10

- 상태: ChainBounty 콘텐츠 가이드 반영 완료
- 변경 사항
  - 모호한 분석 표현 금지
  - `ChainBounty analysis`를 더 큰 맥락, 반복 패턴, 예상 변화 중심으로 강화
  - `Protection measures`를 뉴스 맥락 직접 연결 방식으로 강화
- 이유
  - 단순 요약이 아니라 보안 전문가 관점의 실질적 인사이트를 제공해야 하기 때문

### Iteration 11

- 상태: ChainBounty 포맷팅 가이드 반영 완료
- 변경 사항
  - 무볼드 헤드라인, 공백 라인, 섹션 헤더, 체크리스트 이모지 규칙 반영
  - 텔레그램 본문 생성 단계 trim 제거
  - fallback 템플릿을 A/B/C/D 스타일 구조에 더 가깝게 조정
- 이유
  - 텔레그램에서 스캔 가능한 포맷을 강제하고, 메시지 잘림 없이 구조화된 분석문을 보내기 위함

### Iteration 5

- 상태: 운영 베이스라인 완료
- 변경 사항
  - 스타일 프로필을 실사용 버전으로 교체
  - 선택적 LLM 재작성 계층 추가
  - `dry_run=false` 운영 모드 전환 및 실제 전송 검증
- 이유
  - 현재 단계에서 실제 배포 가능한 최소 운영 상태가 필요하다.

### Iteration 6

- 상태: Gemini 연결 완료, 실호출 제약 확인
- 변경 사항
  - Gemini provider 분기 추가
  - Gemini 2.0 Flash 키/모델 로컬 설정 반영
  - 실제 API 호출 검증 시도
- 결과
  - 현재 응답은 `429 Too Many Requests`
  - 서비스는 규칙 기반 fallback으로 계속 동작

### Iteration 7

- 상태: OpenAI 운영 활성화 완료
- 변경 사항
  - provider를 OpenAI로 전환
  - `gpt-4.1-mini` 실호출 검증
  - daily run에서 실제 LLM 재작성 결과 확인
- 이유
  - 현재 가장 안정적으로 운영 가능한 재작성 경로가 필요했다.

### Iteration 8

- 상태: ChainBounty 스타일 가이드 반영 완료
- 변경 사항
  - 사용자 제공 글쓰기 가이드를 HTML 문서로 보관
  - production 스타일 프로필을 ChainBounty 톤에 맞게 재작성
  - LLM system prompt와 fallback 포맷을 가이드 기준으로 조정
- 이유
  - 출력물이 브랜드 톤과 보안 리포팅 문법을 더 정확히 따르도록 하기 위해

### Iteration 9

- 상태: 템플릿 분기 및 텔레그램 쌍 전송 완료
- 변경 사항
  - 기사 유형을 incident/statistical/discussion으로 1차 분류
  - 유형별 fallback 포맷 차등 적용
  - 텔레그램을 `뉴스 1개 -> ChainBounty 게시글 1개` 순서로 전송하도록 변경
- 이유
  - 사용자가 원한 소비 방식에 맞게 원문 맥락과 최종 게시글을 함께 보여주기 위해

### Iteration 10

- 상태: 생성 누락 원인 수정 완료
- 변경 사항
  - 영구 dedupe 제거로 재실행 시 같은 24시간 기사 재생성 허용
  - ChainBounty용 보안 키워드 relevance 강화
  - fallback 포맷 압축 시 source 보존 로직 추가
- 이유
  - "현재 생성이 안 된다"는 증상의 실제 원인을 제거하고 운영 안정성을 높이기 위해

### Iteration 11

- 상태: ChainBounty 보안 사건 편향 강화 완료
- 변경 사항
  - 일반 시장 뉴스보다 해킹/사기/스캠/수사 기사를 우선 통과하도록 필터 조정
  - ChainBounty 관점 분석 문장 강화
  - 모든 생성문 마지막에 community CTA와 링크를 붙이도록 조정
- 이유
  - 사용자가 원하는 서비스 정체성이 보안 사건 분석과 커뮤니티 유입에 더 가깝기 때문

### Iteration 12

- 상태: 공격 유형별 세부 템플릿 분화 완료
- 변경 사항
  - incident를 `drainer`, `phishing`, `bridge_hack`, `sanction_seizure`, `pyramid_scam`으로 세분화
  - 유형별 ChainBounty view와 Protection measures 분기 추가
  - subtype 분류 테스트 추가
- 이유
  - 보안 사건마다 분석 초점과 사용자 보호조치가 달라야 결과물이 덜 단순해지기 때문

### Iteration 13

- 상태: 채널별 본문 품질 분리 완료
- 변경 사항
  - X용 짧은 본문과 Telegram용 긴 분석 본문을 별도 생성
  - LLM 출력 계약에 `telegram_body` 추가
  - 텔레그램에서 더 긴 ChainBounty 분석문이 올라가도록 조정
- 이유
  - Telegram에서 `...`로 잘리는 문제를 없애고 채널별 품질을 분리하기 위해

### Iteration 14

- 상태: X 글자 제한 제거 완료
- 변경 사항
  - X용 본문에서 280자 trim 제거
  - `split_x_thread` 유틸리티 추가
  - 텔레그램 장문 분석과 X용 본문을 분리 유지
- 이유
  - 사용자가 X는 스레드 분할로 올리면 된다고 요청했기 때문

### Iteration 15

- 상태: 2026-03-18 재투입 점검 완료
- 확인 사항
  - `README.md`, `research.md`, `plan.md`가 현재 Git/Jira/테스트 상태를 일부 반영하지 못하고 있었다.
  - 로컬 `main`과 `origin/main`은 동일하다.
  - accessible Jira 범위에서는 `cryptonewsbot` 또는 `ChainBounty` 전용 대표/하위 이슈 구조를 찾지 못했다.
  - UI 승인 대기 중으로 확인된 이슈는 없다.
- 인계 메모
  - 다음 비UI 하위 태스크는 실제 실패 중인 테스트 복구와 문서 최신화였다.
  - Jira 매핑은 추가 근거가 나오기 전까지 임의 생성/수정하지 않는다.

### Iteration 16

- 상태: 테스트 안정화 완료
- 문제
  - `tests/test_pipeline.py`의 RSS fixture가 `2026-03-11` 하드코딩 날짜를 사용해 조사 시점 기준 24시간 창 밖으로 밀려났다.
- 후보 및 반증
  1. fixture 날짜 stale
     - 유지
  2. 보안 relevance filter 과도 강화
     - fixture 키워드와 스타일 프로필 focus topic 기준 반증
  3. 포맷 검증 로직이 post를 폐기
     - `run_result.articles == 0` 단계에서 실패하므로 반증
- 최종 전략
  - fixture 날짜를 현재 시점 기준 상대값으로 생성하도록 수정해 테스트를 시간 경과에 강한 형태로 바꾼다.
- 실제 변경
  - `tests/test_pipeline.py`에 `_build_rss_fixture()` 헬퍼를 추가하고 pubDate를 동적으로 생성하도록 수정
- 검증
  - `PYTHONPATH=src python3 -m unittest discover -s tests -v`
  - 결과: `18` tests, `OK`

### Iteration 17

- 상태: 수집 단계 보안 키워드 필터 강화 완료
- 문제
  - 기존에는 RSS/Atom 수집 후 relevance filtering 단계에서만 보안 기사 선별이 이뤄져 일반 시장 뉴스도 일단 파이프라인에 들어왔다.
- 전략
  - 수집 단계에서 `exploit`, `hack`, `scam`, `phishing`, `drain`, `vulnerability`, `breach`, `compromise`가 title/summary/content에 없는 기사는 조기 제외한다.
- 실제 변경
  - `src/cryptonewsbot/infrastructure/rss.py`에 collection-stage keyword gate 추가
  - `tests/test_rss.py`에 비보안 Atom entry 조기 제외 테스트 추가
- 검증
  - `PYTHONPATH=src python3 -m unittest discover -s tests -v`
  - 결과: `19` tests, `OK`

향후 피드백이 들어오면 이 섹션 아래에 Iteration 2, 3 형태로 누적 기록한다.

## Todo List

- [x] `Codex` 저장소 현재 상태 조사
- [x] `Codex` 온보딩 문서 작성
- [x] `Codex` 조사 문서 작성
- [x] `Codex` 구현 계획 초안 작성
- [x] `Developer/User` 계획 승인 또는 수정 지시
- [x] `Codex` 승인된 기술 스택에 맞춰 프로젝트 부트스트랩
- [x] `Codex` 뉴스 수집 파이프라인 1차 구현
- [x] `Codex` 중복 제거 및 저장 계층 구현
- [x] `Codex` 요약/재작성 파이프라인 구현
- [x] `Codex` 텔레그램 전송 구현
- [x] `Codex` 스케줄 실행용 단일 커맨드와 테스트 추가
- [x] `Codex` 실제 운영 RSS 소스 기본 세트 반영
- [x] `Codex` 텔레그램 토큰 로컬 `.env` 반영
- [x] `User` 봇에 메시지 전송 후 `chat_id` 생성
- [x] `Codex` 생성된 `chat_id`를 `.env`에 반영하고 실전 전송 검증
- [x] `Codex` 실제 운영 스타일 프로필 반영
- [x] `Codex` 운영 모드 전환(`dry_run=false`) 및 전송 검증
- [x] `Codex` Gemini API 키 연결 및 provider 반영
- [ ] `Codex` Gemini quota/요금제 상태 확인 후 고급 재작성 실전 검증
- [x] `Codex` OpenAI API 키 연결 및 실전 재작성 검증
- [x] `Codex` 프롬프트/출력 품질을 실제 운영 톤에 맞게 1차 튜닝
- [x] `Codex` 사건 유형별 템플릿(A/B/C) 자동 선택 로직 1차 구현
- [x] `Codex` 재실행 시 생성 누락을 유발하던 영구 dedupe 제거
- [x] `Codex` ChainBounty용 보안 relevance 키워드 강화
- [x] `Codex` 사건 유형 분류 정확도와 템플릿 세부 포맷 2차 고도화
- [x] `Codex` 공격 유형별(드레이너, 피싱, 브리지 해킹, 제재/압수, 피라미드 스캠) 세부 템플릿 분화
- [x] `Codex` subtype별 LLM 출력 품질과 길이 제어 1차 튜닝
- [x] `Codex` X 글자 제한 제거 및 thread-splitting 준비
- [x] `Codex` 시간 경과에도 깨지지 않도록 파이프라인 테스트 RSS fixture를 동적 날짜 방식으로 안정화
- [x] `Codex` 수집 단계에서 지정 보안 키워드가 없는 뉴스를 조기 제외하도록 RSS 필터 강화
- [ ] `Codex` subtype별 LLM 문체 차이와 분석 깊이 추가 튜닝
- [ ] `Codex` accessible Jira 범위에서 이 저장소 전용 대표/하위 이슈 구조를 추가 확인하거나, 확인 불가 상태를 운영 규칙에 맞게 정리
- [ ] `Codex` 운영 배포 방식 확정

## 변경 이력

### 2026-03-09

- 초기 구현 계획서 작성
- 문서 선작성 규칙에 따라 코드 수정 전 계획 확정 단계로 진입
- 계획 초안 작성 완료, 현재 승인 대기 상태로 갱신
- 사용자 승인 후 Python 표준 라이브러리 중심 MVP 실행 계획으로 갱신
- Python 표준 라이브러리 기반 MVP 구현 및 테스트 완료 상태로 갱신
- 운영용 기본 피드 세트와 수집 상태 추적 기능 반영
- OpenAI `gpt-4.1-mini` 실호출 성공 및 운영 재작성 경로 활성화 반영
- ChainBounty Writing Style Guide 반영 및 출력 포맷 1차 튜닝
- 텔레그램 뉴스/게시글 1:1 순차 전송과 템플릿 분기 1차 구현 반영
- 생성 누락 원인 수정과 보안 relevance 강화 반영
- 보안 사건 전용 편향 강화와 community CTA 중심 출력 반영
- 공격 유형별 세부 템플릿 분화 반영
- X/Telegram 채널별 본문 분리와 텔레그램 장문 분석 반영
- X 글자 제한 제거와 thread split 준비 반영
