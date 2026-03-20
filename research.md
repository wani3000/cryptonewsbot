# research.md

## 조사 목적

이 문서는 `cryptonewsbot` 저장소가 현재 정확히 어떤 상태인지 기록하고, 이후 구현 과정에서 기존 시스템을 파괴하거나 중복 구현하는 일을 방지하기 위해 작성한다.

## 조사 시점

- 날짜: 2026-03-20
- 작업 디렉토리: `/Users/chulwan/Documents/GitHub/cryptonewsbot`

## 조사 방법

아래 항목을 직접 확인했다.

- 현재 작업 경로 확인
- 루트 디렉토리 파일 목록 확인
- 상위 디렉토리 구조 확인
- Git 저장소 여부 확인
- 저장소 내 추적 가능한 파일 존재 여부 확인
- Git 브랜치 / 상태 / 최근 커밋 확인
- `git fetch origin`, `git pull --ff-only` 실행 시도
- `unittest` 실제 실행 결과 확인
- 접근 가능한 Jira 프로젝트와 이슈 검색
- ChainBounty X 자동화 저장소 구조 확인

## 확인 결과 요약

### 1. 저장소 루트 상태

초기 조사 시점에는 비어 있었지만, 현재는 아래 구조가 생성되었다.

- `pyproject.toml`
- `.env.example`
- `config/style_profile.example.json`
- `config/style_profile.production.json`
- `config/feeds/crypto_sources.json`
  - 글로벌/지역별 기본 피드 세트 정의
- `style-guide.html`
- `src/cryptonewsbot/*`
- `tests/*`
- `scripts/run_daily.py`
- `scripts/run_tests.sh`

즉, 저장소는 이제 문서 전용 상태가 아니라 실행 가능한 MVP 코드베이스가 되었다.

### 2. Git 상태

- 현재 디렉토리는 Git 저장소다.
- 원격은 `https://github.com/wani3000/cryptonewsbot.git`로 설정되어 있다.
- 기본 브랜치는 `main`이다.
- 작업 시작 시 워킹트리는 깨끗했고, 로컬 브랜치는 `origin/main` 대비 1커밋 앞서 있었다.
- `git fetch origin`, `git pull --ff-only`는 모두 `Could not resolve host: github.com`으로 실패했다.
- 최근 커밋 3개는 `0bef623 Update schedule and strip markdown formatting`, `4757b8d Stabilize local launchd runtime and repeat suppression`, `f7c9a28 Initial cryptonewsbot MVP and local deployment setup`다.

### 2-1. Jira 조회 결과

- 접근 가능한 Jira Cloud는 `https://oxaz1234.atlassian.net` 하나였다.
- 조회 가능한 프로젝트에는 `CHAIN`도 포함되어 있었다.
- 2026-03-20 기준으로 ChainBounty X 연동 작업용 태스크 `CHAIN-1`, `CHAIN-2`, `CHAIN-3`를 생성했다.
- 현재 저장소와 직접 연결된 Jira 작업 트래킹은 위 3개 이슈를 기준으로 시작된 상태다.

### 3. 현재 애플리케이션 구조

존재하는 핵심 항목:

- `src/cryptonewsbot/main.py`
  - 단일 CLI 엔트리포인트
- `src/cryptonewsbot/config.py`
  - 환경 변수, `.env`, 스타일 프로필 JSON, 피드 설정 JSON 로딩
- `src/cryptonewsbot/database.py`
  - SQLite 스키마 초기화
- `src/cryptonewsbot/domain/models.py`
  - 도메인 데이터 구조 정의
- `src/cryptonewsbot/application/*`
  - 정규화, 중복 제거, relevance filtering, 템플릿 분류, 요약, ChainBounty 스타일 기반 포스트 생성, digest formatting, 파이프라인 orchestration
- `src/cryptonewsbot/infrastructure/*`
  - RSS/Atom 수집기, SQLite 저장소, Telegram 전송기, X 게시 클라이언트
- `.env`
  - 로컬 텔레그램 토큰과 런타임 설정 저장
  - 현재 `chat_id`까지 반영되어 테스트 전송 성공
- `tests/*`
  - deduplication, post generation, pipeline 검증
- `tests/test_config.py`
  - `.env` 로딩 검증
- `tests/test_filtering.py`
  - 보안 relevance와 incident subtype 분류 검증
- `tests/test_clustering.py`
  - 유사 사건 story clustering과 representative 선택 검증
- `config/style_profile.production.json`
  - 운영용 writing style variants 정의
- `config/feeds/crypto_sources.json`
  - source category 외에 `tier` 메타데이터도 포함
- `scripts/run_daily.sh`
  - 로컬 운영 실행 스크립트
- `scripts/run_daily.py`
  - `src` 레이아웃 진입용 Python 래퍼
- `scripts/run_tests.sh`
  - `PYTHONPATH=src`를 고정한 표준 테스트 진입점
- `scripts/install_launchd.sh`
  - macOS `launchd` LaunchAgent 설치 스크립트
- `scripts/deploy_local_runtime.sh`
  - 현재 작업본을 `~/bots/cryptonewsbot`으로 동기화하고, 그 위치에서 LaunchAgent를 재설치
- `deploy/com.chainbounty.cryptonewsbot.daily.plist.template`
  - 로컬 배포용 LaunchAgent 템플릿

### 4. 레이어 구조 분석

현재 레이어는 비교적 명확하게 분리되어 있다.

- Domain
  - `Article`, `ArticleSummary`, `GeneratedPost`, `StyleProfile`, `RunResult`
- Application
  - 순수 함수 중심으로 뉴스 처리 파이프라인을 구성
- Infrastructure
  - 외부 I/O(RSS, SQLite, Telegram)를 담당
- Interface
  - CLI 파서만 담당

동작 흐름:

1. `main.py`가 환경 변수를 읽어 `AppConfig`를 만든다.
   - 이때 `.env`가 있으면 먼저 읽는다.
2. `pipeline.py`가 스타일 프로필과 DB를 초기화한다.
3. `RSSCollector`가 RSS/Atom 피드에서 지난 24시간 기사를 수집하고, 피드별 성공/실패 상태를 기록한다.
4. `normalize_article`이 URL, 텍스트, fingerprint를 표준화한다.
5. `deduplicate_articles`가 기존 저장 기사와 중복을 제거한다.
   - 최근 실제 텔레그램 전송 이력 기준 fingerprint와 canonical URL도 함께 차단한다.
6. `select_relevant_articles`가 스타일 프로필의 `focus_topics` 기준으로 관련 기사만 우선 선별한다.
7. `summarize_articles`가 기사 유형을 `incident/statistical/discussion`으로 분류하고 summary structure를 만든다.
8. `generate_posts`가 유형별 구조를 반영해 X용 포스트를 생성한다.
9. `format_telegram_message_pairs`가 `뉴스 메시지 -> ChainBounty 게시글 메시지` 쌍을 만든다.
   - 뉴스 제목 라인에는 기사 유형에 맞는 이모지를 함께 붙인다.
10. `TelegramClient`가 메시지 리스트를 순서대로 전송한다.
11. 선택적으로 `XClient`가 생성된 ChainBounty 포스트를 X에 regular tweet 또는 thread로 게시한다.
12. `SQLiteRepository`가 run/article/post 결과와 Telegram/X 전달 결과를 저장한다.

### 5. 데이터 관리 방식

현재 ORM은 사용하지 않고 `sqlite3` 직접 접근 방식이다.

스키마:

- `articles`
  - 기사 원문 메타데이터와 fingerprint 저장
- `runs`
  - 배치 실행 이력 저장
- `generated_posts`
  - 실행 결과로 생성된 X용 포스트 저장
- `feed_fetch_results`
  - 피드별 수집 성공/실패, 아이템 수, 에러 메시지 저장
- `delivered_articles`
  - 실제 텔레그램 전송된 기사 fingerprint/canonical URL 이력 저장
- `delivered_x_posts`
  - 실제 X 전송된 기사 fingerprint/canonical URL/tweet_id 이력 저장

중복 제거 방식:

- `normalize_article`에서 `title + canonical_url + summary[:280]` 기반 SHA-256 fingerprint 생성
- `articles.fingerprint`에 `UNIQUE` 제약 적용
- 파이프라인에서 최근 실제 전송 이력의 fingerprint/canonical URL을 읽어 선제 제거

### 6. 비즈니스 로직 분석

현재 구현된 영역:

- 뉴스 수집
  - RSS 2.0 `channel/item`과 Atom `feed/entry` 구조 파싱
  - 기본 피드 세트는 미국/글로벌 매체, 한국/일본 지역 매체, 미국/유럽/일본/캐나다/홍콩 규제기관 피드, 미국/한국/유럽/캐나다/일본/중국 Google News 검색 RSS로 확장되었다.
- 수집 소스 정규화
  - URL의 `utm_*`, `fbclid`, `gclid` 제거
  - 공백 정리
- 중복 제거
  - fingerprint + DB 저장 이력 기반
- 중요도/주제 분류
  - `focus_topics` 키워드 포함 여부 점수화
- 템플릿 분류
  - 기사 내용을 기준으로 `incident`, `statistical`, `discussion` 1차 분류
- incident 세부 분류
  - `drainer`, `phishing`, `bridge_hack`, `sanction_seizure`, `pyramid_scam`, `general`로 추가 세분화
- 보안 사건 필터링
  - `hack`, `scam`, `fraud`, `phishing`, `exploit`, `wallet drain`, `laundering`, `seized` 등 보안 사건 신호가 강한 기사 우선
  - 한국어/일본어/중국어 보안 키워드도 함께 인식해 지역 기사 relevance를 잡는다.
  - 소스 카테고리 우선순위를 함께 반영해 `regulator > media > search-aggregated` 순으로 정렬한다.
  - 일반 가격/ETF/거시 시장 기사만 있는 경우는 제외
- story clustering
  - relevance selection 전에 유사 제목/요약을 기준으로 같은 사건을 묶는다.
  - 대표 기사는 source priority와 내용 밀도로 선택한다.
  - cluster size와 related source 정보는 이후 summary/prompt 단계로 전달된다.
- source curation / selection precision
  - source priority는 `category + tier` 조합으로 계산된다.
  - 현재 tier는 `core`, `extended`, `watch`를 지원한다.
  - search-aggregated 기사에는 stronger security signal requirement를 적용한다.
  - `best crypto to buy`, `presale`, `token launch`, `price prediction` 같은 프로모션/SEO 노이즈는 기본적으로 제외한다.
- 요약
  - 규칙 기반 `key_point`, `why_it_matters` 생성
- 사용자 기준 기반 재가공
  - 스타일 프로필의 금지 표현, signature, hashtag, audience 반영
  - LLM 프롬프트에 `incident_type`별 문체, ChainBounty 분석 포인트, Telegram 확장 깊이 지시 반영
- X 포스트 포맷팅
  - 길이 제한 기반 trim 처리
  - subtype별 incident guidance를 이용해 문체/분석 강조점을 분기
  - 최종 X 전송 시 280자 초과 본문은 thread로 분할 가능
- 텔레그램 전송
  - dry-run 또는 Bot API `sendMessage`
  - 최종 전송 본문에서는 Markdown bold 표기 `**`를 제거해 Telegram에서 원문 기호가 그대로 노출되지 않게 정리
  - LLM 실패 시에도 subtype별 watchpoint가 들어간 더 긴 fallback Telegram 본문 생성
- 텔레그램 운영 진단
  - `telegram-get-updates` 커맨드로 최근 업데이트 확인
  - `telegram-send-test` 커맨드로 수동 테스트 메시지 전송
- X 운영 진단
  - `x-send-test` 커맨드로 수동 X 테스트 게시 가능
- 선택적 LLM 재작성
  - `CRYPTO_NEWSBOT_LLM_API_KEY`, `CRYPTO_NEWSBOT_LLM_MODEL`이 설정되면 OpenAI-compatible endpoint 호출
  - 미설정 또는 실패 시 규칙 기반 생성으로 fallback
  - Gemini provider도 지원하며 `generateContent` 호출 결과를 JSON으로 파싱
- 운영 피드 관리
  - `CRYPTO_NEWSBOT_FEED_URLS`가 비어 있으면 `config/feeds/crypto_sources.json` 사용
- 피드 모니터링
  - digest 하단과 DB에 피드별 OK/Error 상태 기록
- X 통합
  - `CRYPTO_NEWSBOT_ENABLE_X_POSTING`, `CRYPTO_NEWSBOT_X_DRY_RUN`, `CRYPTO_NEWSBOT_X_MAX_POSTS`로 제어
  - `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_TOKEN_SECRET`를 사용
  - 게시 성공 시 root tweet id를 `generated_posts`와 `delivered_x_posts`에 함께 저장
- ChainBounty 회사 관점 프롬프트
  - LLM 시스템/유저 프롬프트에 ChainBounty를 커뮤니티 기반 crypto crime investigation 플랫폼으로 명시한다.
  - neutral news voice 대신 ChainBounty 조사팀/보안팀 브리핑 톤을 지시한다.
- writing style rotation
  - 기본 글쓰기 스타일은 `incident_briefing`, `operator_alert`, `casefile_note`, `community_watch` 4종이다.
  - 한 배치 안에서는 바로 같은 스타일이 반복되지 않도록 순환한다.
  - 날짜 기준으로 시작 스타일이 회전해 매일 같은 톤으로 시작하지 않게 한다.
  - 생성된 `writing_style_name`은 DB에 저장되고, 다음 실행은 마지막 사용 스타일의 다음 variant부터 이어서 시작한다.
  - 스타일별로 opening pattern과 analyst phrasing도 분기한다.

현재 미구현 영역:

- LLM 기반 정교한 요약/재작성
- HTML 본문 파싱
- 비동기 수집
- 텔레그램 명령형 인터페이스
- 실패 재시도/백오프
- 운영용 스케줄러 내장

현재 외부 배포 상태:

- Git 저장소는 이미 구성되어 있고, 로컬 운영 배포는 macOS `launchd` 기준으로 구성되어 있다.
- `scripts/install_launchd.sh`는 `~/Library/LaunchAgents/com.chainbounty.cryptonewsbot.daily.plist`를 생성하고 등록한다.
- 기본 실행 시각은 매일 08:00 로컬 시간이다.
- `config/feeds/crypto_sources.json`의 현재 기본 소스 수는 16개다.
- 현재 Jira 후속 작업으로 `CHAIN-4`(company-angle prompt 강화), `CHAIN-5`(story clustering), `CHAIN-6`(source curation), `CHAIN-7`(selection precision), `CHAIN-8`(rotating writing styles)가 추가되었다.
- 현재 LaunchAgent는 `~/bots/cryptonewsbot` 런타임을 기준으로 재설치되어 있다.
- 개발 저장소가 `/Users/chulwan/Documents/...` 아래에 있어 `launchd` 직접 실행은 `Operation not permitted`로 실패할 수 있다.
- 이를 피하기 위해 런타임 경로를 `~/bots/cryptonewsbot`로 분리하고, LaunchAgent는 그 복사본만 실행하도록 조정했다.

### 7. 2026-03-19 테스트 재현성 재검증

원인을 단정하기 전에 아래 후보 3개를 분리해 반증했다.

1. 후보: `src` 레이아웃 import 경로가 기본 `unittest` 실행에 반영되지 않아 테스트가 실패한다.
   - 검증: `python3 -m unittest discover -s tests` 실행 결과 `ModuleNotFoundError: No module named 'cryptonewsbot'`가 재현됐다.
   - 반증 결과: `PYTHONPATH=/Users/chulwan/Documents/GitHub/cryptonewsbot/src python3 -m unittest discover -s tests`로 import 오류는 사라졌다.
   - 결론: 실행 진입점 문제는 실제로 존재한다.
2. 후보: 보안 편향 필터가 `Bitcoin ETF flows keep rising` 기사를 모두 제외해서 파이프라인 테스트가 깨진다.
   - 검증: 같은 제목/요약을 현재 시점 `published_at`으로 만든 단일 기사에 `select_relevant_articles`를 직접 호출했을 때 `selected_count 1`이 나왔다.
   - 반증 결과: 필터 단독으로는 이 기사 케이스를 제거하지 않았다.
   - 결론: 주요 원인은 아니다.
3. 후보: repeat suppression / delivered dedupe가 첫 실행부터 게시글을 막고 있다.
   - 검증: 현재 시점 `pubDate`를 가진 RSS fixture로 fresh DB에서 `run_daily_digest`를 실행했을 때 `articles 1 posts 1 delivered True`가 나왔다.
   - 반증 결과: 첫 실행에는 suppression이 조기 적용되지 않았다.
   - 결론: 주요 원인은 아니다.

최종 결론:

- 실제 파이프라인 테스트 실패의 직접 원인은 고정 날짜 RSS fixture가 현재 시점에서 24시간 윈도우 밖으로 밀려 `No new crypto news matched the current rules in the last 24 hours.`가 발생한 것이다.
- 별도로, 기본 `unittest` 실행만으로는 `src` 레이아웃 import가 풀리지 않아 표준 테스트 진입점도 부족했다.
- 따라서 `tests/test_pipeline.py`의 RSS fixture를 현재 시점 기준으로 바꾸고, `scripts/run_tests.sh`를 추가해 재현 가능한 테스트 경로를 고정했다.

### 8. ChainBounty X 연동 조사 결과

- 별도 저장소 `chainbounty-x-automation`는 X 검색, Claude 기반 코멘트 생성, quote tweet 게시 흐름을 갖고 있었다.
- 이번 연동 방향에서는 그 저장소의 핵심 재사용 포인트를 “X 인증/게시 자격 증명 규칙”과 “게시 이력 관리 개념”으로 한정했다.
- 실제 통합은 `cryptonewsbot`를 오케스트레이터로 유지하고, 기사 수집과 ChainBounty 재작성 이후 X를 두 번째 전달 채널로 붙이는 방식이 가장 단순했다.
- 별도 설계 메모는 [chainbounty_x_integration.md](/Users/chulwan/Documents/GitHub/cryptonewsbot/chainbounty_x_integration.md)에 기록했다.

## 구현 대상 기능과 직접 연관된 조사 결과

요구사항상 최소한 아래 기능군이 필요하다.

1. 뉴스 수집 계층
   - 지난 24시간 기준으로 암호화폐 산업 뉴스를 수집해야 한다.
   - 다중 소스 지원 가능성을 전제로 설계해야 한다.
2. 정규화 및 중복 제거 계층
   - 기사 URL, 제목, 발행 시각, 본문/요약 텍스트를 표준 형태로 다뤄야 한다.
   - 동일 기사 재배포, 제목 변형 기사, 요약본 재인용 기사에 대한 중복 전략이 필요하다.
3. 분석 및 요약 계층
   - 산업적 의미를 중심으로 핵심 포인트를 추출해야 한다.
   - 단순 요약이 아니라 X 게시글 생성을 위한 입력 구조를 만들어야 한다.
4. 사용자 맞춤 재작성 계층
   - 사전 입력된 정보(톤, 관심 주제, 금지 표현, 포맷 규칙 등)를 기반으로 재작성해야 한다.
5. 전달 계층
   - 최종 결과를 텔레그램에서 소비하기 쉬운 형태로 보내야 한다.
   - X에 바로 옮겨 적기 쉬운 포맷이 필요하다.

## 현재 기준 리스크

- 규칙 기반 summary/post generation은 빠르지만 표현 품질 한계가 있다.
- RSS/Atom 외 변형 피드에는 취약할 수 있다.
- 실제 운영 피드 품질과 기사 본문 길이에 따라 relevance filtering 품질이 달라질 수 있다.
- 텔레그램 전송 실패 시 현재는 예외 전파 외 추가 재시도 로직이 없다.
- 외부 네트워크가 막힌 환경에서는 `git fetch`, `git pull`, 실 API quota 확인 같은 원격 검증이 제한된다.
- 기본 `python3 -m unittest discover -s tests`는 여전히 `src` 경로를 자동으로 잡지 않으므로, 테스트는 `zsh scripts/run_tests.sh` 기준으로 실행해야 한다.

## 권장 후속 조사 항목

다음 고도화 전에 아래를 확정해야 한다.

- 운영용 RSS 소스 목록
- LLM 도입 여부와 공급자
- 주제별 클러스터링 필요 여부
- 텔레그램 상호작용 인터페이스 필요 여부
- 외부 스케줄러(cron, GitHub Actions, 서버 cron) 방식

## 변경 이력

### 2026-03-09

- 초기 조사 문서 작성
- 저장소가 비어 있고 Git 초기화도 되지 않았음을 기록
- 기존 레이어, ORM, API, 비즈니스 로직이 모두 미구현 상태임을 확인
- 실행 환경 조사 결과 `Python 3.9.6`만 기본 확인되었고 `pytest`, `uv`는 설치되어 있지 않음을 반영
- 구현 전략이 외부 의존성 최소화 방향으로 조정되었음을 기록
- 표준 라이브러리 기반 MVP가 실제 구현되었음을 반영
- 현재 코드의 레이어 구조, 데이터 흐름, 저장 스키마, 테스트 범위를 분석 결과에 추가
- 운영용 기본 피드 설정, Atom 지원, feed 상태 추적 기능을 분석 결과에 추가
- `.env` 자동 로딩과 텔레그램 진단 커맨드를 분석 결과에 추가
- 봇 토큰 검증, `chat_id` 확인, 테스트 메시지 전송 성공 상태를 반영
- 선택적 LLM 재작성 계층과 fallback 동작을 분석 결과에 추가
- Gemini 2.0 Flash 설정을 반영했지만 실호출 검증에서는 `429 Too Many Requests`가 발생해 fallback이 실제 활성화됨을 기록
- OpenAI `gpt-4.1-mini`로 provider 전환 후 실호출과 daily run에서 재작성 결과가 실제 반영됨을 기록
- 사용자 제공 ChainBounty 스타일 가이드를 HTML로 보관하고 프롬프트/프로필에 반영했음을 기록
- 텔레그램 전송이 digest 1건에서 뉴스/게시글 쌍 순차 전송으로 변경되었음을 기록
- DB 기반 영구 dedupe를 제거해 수동 테스트 후에도 같은 24시간 윈도우 기사 재생성이 가능해졌음을 기록
- security keyword layer를 relevance scoring에 추가해 ChainBounty 성격의 기사 누락을 줄였음을 기록
- 필터가 일반 시장 뉴스보다 보안 사건/사기/수사 기사에 더 강하게 편향되도록 추가 조정했음을 기록
- 생성문 마지막에 ChainBounty community CTA와 링크를 남기도록 강화했음을 기록
- incident subtype별 분석 문장과 보호조치가 다르게 생성되도록 세부 템플릿을 분화했음을 기록
- X용 `body`와 텔레그램용 `telegram_body`를 분리해 텔레그램에서는 더 긴 분석 본문을 전송하도록 변경했음을 기록
- X용 본문은 더 이상 280자 제한으로 잘리지 않고, 필요 시 `split_x_thread` 유틸리티로 스레드 분할할 수 있게 변경했음을 기록
- 텔레그램 뉴스 제목과 생성문 도입부에 기사 유형별 이모지를 붙여 가독성을 높였음을 기록
- macOS `launchd` 기준 로컬 배포 스크립트와 LaunchAgent 템플릿을 추가했음을 기록
- `launchd` 실실행이 `Documents` 폴더 접근 제한으로 막히는 운영 제약을 확인했음을 기록
- 최근 실제 전송된 기사만 `repeat suppression` 윈도우 동안 다시 보내지 않도록 `delivered_articles` 기반 dedupe를 추가했음을 기록
- 로컬 Mac 상시 운영용으로 `~/bots/cryptonewsbot` 런타임 동기화 스크립트를 추가했음을 기록

### 2026-03-10

- GitHub 원격 저장소를 현재 작업 경로로 clone해 Git 관리 상태로 전환했음을 기록
- 기본 `launchd` 실행 시각을 매일 08:00으로 조정하고 문서와 배포 템플릿을 동기화했음을 기록
- 운영용 `.env`를 연결해 Telegram 테스트 메시지와 실제 daily run 전송을 검증했음을 기록
- 최종 생성 본문에서 Markdown bold 표기 `**`가 남지 않도록 후처리와 템플릿을 조정했음을 기록

### 2026-03-19

- 실제 Git 루트가 `/Users/chulwan/Documents/GitHub/cryptonewsbot`임을 재확인하고, `~/bots/cryptonewsbot`은 런타임 복사본임을 분리 기록
- `git fetch origin`, `git pull --ff-only`가 DNS 해석 실패로 막힌 상태를 기록
- 접근 가능한 Jira 인스턴스에서 현재 저장소와 직접 매칭되는 이슈를 찾지 못한 사실을 기록
- 기본 `unittest discover`가 `src` 레이아웃 import를 재현하지 못함을 기록
- 파이프라인 테스트 실패 후보 3개를 검증하고, 고정 날짜 RSS fixture가 직접 원인임을 반영
- `scripts/run_tests.sh` 추가와 `tests/test_pipeline.py` 현재 시점 fixture 전환으로 테스트 재현성을 복구했음을 기록

### 2026-03-20

- ChainBounty X 자동 게시 1차 통합 설계 메모를 추가했음을 기록
- Jira `CHAIN-1`, `CHAIN-2`, `CHAIN-3`를 생성해 연동 작업을 추적하기 시작했음을 기록
- `XClient`, X 관련 `.env` 설정, CLI 테스트 명령, X 전달 이력 저장을 추가했음을 기록
- `zsh scripts/run_tests.sh` 기준 24개 테스트가 통과함을 기록
