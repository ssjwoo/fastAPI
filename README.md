개인 가계부 프로젝트

-- 프로젝트 소개
: 개인 사용자가 자신의 수입과 지출을 기록하고, 카테고리별 예산 목표를 설정하여 월별 소비 현황을 확인할 수 있는 웹 애플리케이션 구현을 목표로 하고 있습니다.
FastAPI 백엔드를 활용해 인증, CRUD, 통계 리포트를 제공하며, 제출 과제 요구사항(4~5개 테이블, JWT 인증, RESTful API 설계, Swagger/Thunder Client 제출)에 맞게 구현되었습니다.

-- 주요 기능
거래 관리: 수입/지출 내역 등록, 수정, 삭제, 조회
계정 관리: 지갑/은행/카드 계정별 잔액 관리
카테고리 관리: 수입/지출 카테고리 생성 및 분류
목표 설정: 카테고리별 월별 예산 한도 설정
리포트 제공: 월별 총수입/총지출, 카테고리별 집계, 목표 대비 사용률 확인

-- 기술 스택
Backend: FastAPI, SQLAlchemy, Alembic
Database: SQLite (개발용), PostgreSQL (확장 가능)
Auth: OAuth2 + JWT (로그인/회원가입, 권한 검증)
Validation: Pydantic v2
Docs & Test: Swagger UI, Thunder Client

-- 테이블 구조
users: 사용자 계정 (이메일, 비밀번호 해시, 역할) 등
accounts: 계정(은행/카드/지갑) 정보 등
categories: 카테고리(수입/지출) 분류 등
transactions: 거래 내역 (금액, 메모, 발생일, 계정, 카테고리) 등
budget: 설정 예산, 월 예산 등

-- 구현 계획
1. 초기 세팅: FastAPI, Alembic, JWT 인증 구현
2. DB 마이그레이션: User, Account, Category, Transaction, Budget 테이블 생성
3. 인증 API: 회원가입, 로그인(JWT), 사용자 권한 검증
4. 계좌/카테고리 API: CRUD, 소유권 검사
5. 거래 API: CRUD + Query 필터(기간/금액/카테고리별 조회)
6. 예산 API: CRUD, 월별 예산 조회
7.리포트 API:
  /reports/summary?month=YYYY-MM (총수입/총지출, 카테고리별 합계)
  /reports/budget-status?month=YYYY-MM (예산 대비 사용률)
  /reports/summary.csv (CSV 다운로드)
8. Swagger/Thunder Client: API 문서화 및 테스트
