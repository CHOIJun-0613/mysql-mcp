# MySQL MCP(Model Context Protocol) Server

Cursor AI에서 MySQL 데이터베이스에 자연어로 쿼리할 수 있는 MCP(Model Context Protocol) 서버입니다.

## 📋 목차

- [개요](#개요)
- [주요 기능](#주요-기능)
- [프로젝트 구조](#프로젝트-구조)
- [설치 및 설정](#설치-및-설정)
- [사용법](#사용법)
- [API 문서](#api-문서)
- [개발 가이드](#개발-가이드)
- [문제 해결](#문제-해결)
- [라이선스](#라이선스)

## 🎯 개요

이 프로젝트는 MCP(Model Context Protocol)를 구현하여 Cursor AI에서 MySQL 데이터베이스에 자연어로 쿼리를 실행할 수 있도록 합니다. 사용자는 복잡한 SQL 문법을 몰라도 자연어로 데이터를 조회할 수 있습니다.

### 기술 스택

- **언어**: Python 3.8+
- **프로토콜**: MCP(Model Context Protocol)
- **데이터베이스**: MySQL
- **자연어 처리**: OpenAI API (선택사항)
- **개발 도구**: Cursor IDE

## ✨ 주요 기능

### 1. 자연어 쿼리 처리
- 한국어 자연어를 MySQL SQL로 자동 변환
- OpenAI API를 활용한 고급 자연어 처리
- 기본 패턴 매칭을 통한 안정적인 변환

### 2. 데이터베이스 관리
- MySQL 연결 풀을 통한 효율적인 연결 관리
- 테이블 목록 조회
- 테이블 구조 및 상세 정보 조회
- 안전한 쿼리 실행 (SELECT 쿼리만 허용)

### 3. MCP 도구 제공
- `query_mysql`: 자연어로 데이터베이스 쿼리
- `list_tables`: 테이블 목록 조회
- `describe_table`: 테이블 구조 조회
- `get_table_info`: 테이블 상세 정보 조회
- `test_connection`: 데이터베이스 연결 테스트

## 📁 프로젝트 구조

```
mysql-mcp/
├── server/                          # MCP 서버 소스
│   ├── mysql_mcp_server.py         # 기본 MCP 서버
│   ├── mysql_mcp_server_v2.py      # 개선된 MCP 서버 (권장)
│   ├── config.py                   # 설정 관리
│   ├── mysql_manager.py            # MySQL 연결 관리
│   ├── natural_language_processor.py # 자연어 처리
│   ├── requirements.txt            # 서버 의존성
│   └── env_example.txt             # 환경 변수 예제
├── client/                         # 테스트 클라이언트
│   ├── test_client.py              # MCP 서버 테스트 클라이언트
│   └── requirements.txt            # 클라이언트 의존성
├── docs/                           # 문서
│   └── requirement.md              # 요구사항 문서
└── README.md                       # 프로젝트 README
```

## 🚀 설치 및 설정

### 1. 사전 요구사항

- Python 3.8 이상
- MySQL 서버
- Cursor IDE (MCP 클라이언트)

### 2. 저장소 클론

```bash
git clone <repository-url>
cd mysql-mcp
```

### 3. 서버 의존성 설치

```bash
cd server
pip install -r requirements.txt
```

### 4. 환경 변수 설정

`server/env_example.txt`를 참고하여 환경 변수를 설정하세요:

```bash
# MySQL 설정
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=your_password
export MYSQL_DATABASE=test_db

# OpenAI API 설정 (선택사항)
export OPENAI_API_KEY=your_openai_api_key
export OPENAI_MODEL=gpt-3.5-turbo

# 로깅 레벨
export LOG_LEVEL=INFO
```

### 5. MySQL 데이터베이스 설정

테스트용 데이터베이스와 테이블을 생성하세요:

```sql
CREATE DATABASE test_db;
USE test_db;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (name, email) VALUES 
    ('홍길동', 'hong@example.com'),
    ('김철수', 'kim@example.com'),
    ('이영희', 'lee@example.com');
```

## 📖 사용법

### 1. 서버 실행

```bash
cd server
python mysql_mcp_server_v2.py
```

### 2. 클라이언트 테스트

```bash
cd client
pip install -r requirements.txt
python test_client.py
```

### 3. Cursor IDE에서 사용

1. Cursor IDE의 설정에서 MCP 서버를 추가
2. 서버 경로: `python /path/to/mysql-mcp/server/mysql_mcp_server_v2.py`
3. 채팅에서 자연어로 쿼리 실행

### 4. 사용 예시

```
사용자: "사용자 테이블에서 모든 데이터를 조회해줘"
MCP: SELECT * FROM users LIMIT 10

사용자: "테이블 목록을 보여줘"
MCP: SHOW TABLES

사용자: "users 테이블의 구조를 설명해줘"
MCP: DESCRIBE users
```

## 🔧 API 문서

### MCP 도구 목록

#### 1. query_mysql
자연어로 MySQL 데이터베이스를 쿼리합니다.

**입력 스키마:**
```json
{
  "type": "object",
  "properties": {
    "natural_language_query": {
      "type": "string",
      "description": "실행할 자연어 쿼리"
    }
  },
  "required": ["natural_language_query"]
}
```

**사용 예시:**
```json
{
  "natural_language_query": "사용자 테이블에서 모든 데이터를 조회해줘"
}
```

#### 2. list_tables
데이터베이스의 모든 테이블 목록을 조회합니다.

**입력 스키마:**
```json
{
  "type": "object",
  "properties": {},
  "required": []
}
```

#### 3. describe_table
특정 테이블의 구조를 조회합니다.

**입력 스키마:**
```json
{
  "type": "object",
  "properties": {
    "table_name": {
      "type": "string",
      "description": "조회할 테이블 이름"
    }
  },
  "required": ["table_name"]
}
```

#### 4. get_table_info
테이블의 상세 정보(구조, 레코드 수, 샘플 데이터)를 조회합니다.

**입력 스키마:**
```json
{
  "type": "object",
  "properties": {
    "table_name": {
      "type": "string",
      "description": "조회할 테이블 이름"
    }
  },
  "required": ["table_name"]
}
```

#### 5. test_connection
MySQL 데이터베이스 연결을 테스트합니다.

**입력 스키마:**
```json
{
  "type": "object",
  "properties": {},
  "required": []
}
```

## 🛠️ 개발 가이드

### 1. 새로운 도구 추가

1. `mysql_mcp_server_v2.py`의 `_handle_list_tools` 메서드에 도구 정의 추가
2. `_handle_call_tool` 메서드에 도구 처리 로직 추가
3. 필요한 경우 새로운 핸들러 메서드 구현

### 2. 자연어 처리 개선

1. `natural_language_processor.py`에서 패턴 매칭 로직 수정
2. OpenAI API 프롬프트 개선
3. 새로운 한국어 키워드 추가

### 3. 데이터베이스 기능 확장

1. `mysql_manager.py`에 새로운 메서드 추가
2. 쿼리 유효성 검사 로직 수정
3. 결과 포맷팅 개선

### 4. 테스트 작성

```bash
cd client
python test_client.py --auto  # 자동화된 테스트 실행
```

## 🔍 문제 해결

### 일반적인 문제

#### 1. MySQL 연결 실패
- MySQL 서버가 실행 중인지 확인
- 환경 변수 설정 확인
- 사용자 권한 확인

#### 2. MCP 서버 시작 실패
- Python 버전 확인 (3.8+ 필요)
- 의존성 패키지 설치 확인
- 로그 확인

#### 3. 자연어 변환 실패
- OpenAI API 키 설정 확인
- 네트워크 연결 확인
- 기본 변환 로직으로 대체

#### 4. Cursor IDE에서 인식되지 않음
- MCP 서버 경로 확인
- 서버 실행 권한 확인
- Cursor IDE 재시작

### 로그 확인

서버 로그를 확인하여 문제를 진단할 수 있습니다:

```bash
export LOG_LEVEL=DEBUG
python mysql_mcp_server_v2.py
```

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 지원

문제가 발생하거나 질문이 있으시면 이슈를 생성해 주세요.

---

**참고 문서:**
- [MCP Specification](https://modelcontextprotocol.io/specification/2025-06-18/server)
- [MCP Quickstart](https://modelcontextprotocol.io/quickstart/server)
