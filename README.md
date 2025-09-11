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

User(사람)
 ├─ Account(내 통장 여러 개)
 │    └─ Transaction(입출금 기록들)
 └─ Category(식비/교통/월급…; income or expense)
 └─ Budget(월별 예산: 카테고리마다)

-- 구현 계획
1. 초기 세팅: FastAPI, Alembic, JWT 인증 구현
2. DB 마이그레이션: User, Account, Category, Transaction, Budget 테이블 생성
3. 인증 API: 회원가입, 로그인(JWT), 사용자 권한 검증
4. 계좌/카테고리 API: CRUD, 소유권 검사
5. 거래 API: CRUD + Query 필터(기간/금액/카테고리별 조회)
6. 예산 API: CRUD, 월별 예산 조회
7. 리포트 API:
  /reports/summary?month=YYYY-MM (총수입/총지출, 카테고리별 합계)
  /reports/budget-status?month=YYYY-MM (예산 대비 사용률)
  /reports/summary.csv (CSV 다운로드)
8. Swagger/Thunder Client: API 문서화 및 테스트



-- 세팅 가이드

1. MySQL 계정 설정

MySQL 8 이상에서는 root 계정이 기본적으로 caching_sha2_password 인증 방식을 쓰는데,
Python 드라이버(pymysql)와 충돌이 날 수 있음.

SQL에서 다음 명령어로 root 계정 인증 방식을 바꿔주세요:

ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '비밀번호';
ALTER USER 'root'@'127.0.0.1' IDENTIFIED WITH mysql_native_password BY '비밀번호';
FLUSH PRIVILEGES;


⚠️ root@localhost와 root@127.0.0.1은 다른 계정으로 취급되므로 둘 다 바꿔야 합니다.

2. .env 파일 작성

프로젝트 루트에 .env 파일을 만들고 다음 내용을 채워주세요:

DB_USER=root
DB_PASSWORD=비밀번호
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=finance

SECRET_KEY=your_secret_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE=6000
REFRESH_TOKEN_EXPIRE=604800

3. 의존성 설치
pip install pymysql

4. Alembic 마이그레이션 실행

DB 테이블 자동 생성/업데이트는 Alembic으로 관리합니다:

alembic revision --autogenerate -m "init tables"
alembic upgrade head

5. 서버 실행
uvicorn app.main:app --reload --port 8081






-- 마이그레이션 사용법 (Alembic)

1. 마이그레이션 스크립트 생성

모델을 수정했을 때는 새로운 revision 파일을 생성합니다:

alembic revision --autogenerate -m "변경 내용"


-> alembic/versions/ 폴더에 자동으로 Python 스크립트가 생성됩니다.
(예: 20250912_init_tables.py)

2. DB에 반영

생성된 마이그레이션 스크립트를 실제 DB에 반영하려면:

alembic upgrade head

DB 스키마가 최신 상태로 업데이트됩니다.

3. DB 확인

MySQL에서 확인:

SHOW TABLES;


-> users, accounts, categories, budgets, transactions 등 우리가 만든 테이블이 보이면 정상입니다.

4. alembic_version 테이블

Alembic이 자동으로 만든 시스템 테이블입니다.

현재 DB가 적용 중인 revision ID를 저장하고 있어, upgrade/downgrade 실행 시 기준점이 됩니다.

이 테이블은 프로젝트마다 1개만 존재하며, 직접 수정하거나 삭제하면 안 됩니다.

Git에는 커밋할 필요 없습니다. (DB 내부에서만 쓰임)

5. 팀원용 사용법

프로젝트 클론 후 .env 세팅

pip install pymysql

최신 스키마 적용:

alembic upgrade head


필요 시 새로운 변경은:

alembic revision --autogenerate -m "message"
alembic upgrade head