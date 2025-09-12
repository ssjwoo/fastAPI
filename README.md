# Account CRUD - B 도메인 담당 역할

## 📋 프로젝트 개요
FastAPI 개인 가계부 프로젝트에서 **B 도메인 - 계정/카테고리 CRUD** 담당 구현 파일들

## 👤 담당 역할
- **계정(Account) 관리**: 은행계좌, 카드, 지갑 등의 완전한 CRUD 구현
- **카테고리(Category) 관리**: 수입/지출 분류의 완전한 CRUD 구현

## 📁 파일 구조
```
account_CRUD/
├── models/
│   ├── account.py     # 계정 데이터베이스 모델
│   └── category.py    # 카테고리 데이터베이스 모델
├── schemas/
│   ├── account.py     # 계정 API 입출력 스키마
│   └── category.py    # 카테고리 API 입출력 스키마
├── routers/
│   ├── accounts.py    # 계정 API 엔드포인트 구현
│   └── categories.py  # 카테고리 API 엔드포인트 구현
└── README.md          # 이 파일
```

## 🛠️ 구현된 기능

### 계정(Account) 관리
- ✅ **POST /accounts** - 새 계정 생성
- ✅ **GET /accounts** - 계정 목록 조회 (타입별 필터링, 검색 기능)
- ✅ **GET /accounts/{id}** - 특정 계정 상세 조회
- ✅ **PATCH /accounts/{id}** - 계정 정보 수정
- ✅ **DELETE /accounts/{id}** - 계정 삭제

### 카테고리(Category) 관리
- ✅ **POST /categories** - 새 카테고리 생성
- ✅ **GET /categories** - 카테고리 목록 조회 (타입별 필터링)
- ✅ **GET /categories/{id}** - 특정 카테고리 상세 조회
- ✅ **PATCH /categories/{id}** - 카테고리 정보 수정
- ✅ **DELETE /categories/{id}** - 카테고리 삭제

## 🎯 주요 특징

### 계정 관리 특별 기능
- **타입별 필터링**: `?type=bank` (은행계좌만), `?type=card` (카드만)
- **이름 검색**: `?search=국민` (이름에 "국민" 포함된 계정만)
- **잔액 관리**: balance 필드로 계좌 잔액 추적

### 카테고리 관리 특별 기능
- **타입별 필터링**: `?type=income` (수입), `?type=expense` (지출)
- **중복 방지**: 같은 이름+타입 조합의 카테고리 생성 차단
- **적절한 에러 처리**: 409 상태 코드로 중복 오류 반환

## 🔧 기술 스택
- **FastAPI**: RESTful API 프레임워크
- **SQLAlchemy**: ORM (데이터베이스 모델)
- **Pydantic v2**: 데이터 검증 및 스키마
- **SQLite**: 데이터베이스

## 📝 과제 요구사항 충족
- ✅ **완전한 REST CRUD** 구현
- ✅ **Pydantic 모델링** 사용
- ✅ **경로/쿼리 매개변수** 처리
- ✅ **Request Body** 처리
- ✅ **적절한 에러 핸들링** (404, 409 상태 코드)
- ✅ **SQLAlchemy ORM** 사용

