# MySQL MCP(Model Context Protocol) Server

Cursor AI에서 MySQL 데이터베이스에 자연어로 쿼리할 수 있는 MCP(Model Context Protocol) 서버입니다.

## 📋 목차

- [개요](#개요)
- [주요 기능](#주요-기능)
- [프로젝트 구조](#프로젝트-구조)
- [설치 및 설정](#설치-및-설정)
- [사용법](#사용법)
- [프레임워크 비교](#프레임워크-비교)
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
- **자연어 처리**: Groq API (llama3-8b-8192 모델), OpenAI API (대체)
- **개발 도구**: Cursor IDE
- **프레임워크**: FastMCP (선택사항)

## ✨ 주요 기능

### 1. 자연어 쿼리 처리
- 한국어 자연어를 MySQL SQL로 자동 변환
- Groq API와 llama3-8b-8192 모델을 활용한 고급 자연어 처리
- OpenAI API를 대체 옵션으로 지원
- 기본 패턴 매칭을 통한 안정적인 변환

### 2. 스트리밍 방식 결과 전송
- 실시간 진행 상황 표시 (🔄, ✅, ❌ 이모지)
- 대용량 결과를 청크 단위로 분할하여 전송
- 사용자 경험 향상을 위한 즉시 피드백
- 안정적인 대용량 데이터 처리

### 3. 데이터베이스 관리
- MySQL 연결 풀을 통한 효율적인 연결 관리
- 테이블 목록 조회
- 테이블 구조 및 상세 정보 조회
- 안전한 쿼리 실행 (SELECT 쿼리만 허용)

### 4. MCP 도구 제공
- `query_mysql`: 자연어로 데이터베이스 쿼리
- `list_tables`: 테이블 목록 조회
- `describe_table`: 테이블 구조 조회
- `get_table_info`: 테이블 상세 정보 조회
- `test_connection`: 데이터베이스 연결 테스트
- `get_database_stats`: 데이터베이스 통계 조회 (FyMCP 전용)

## 📁 프로젝트 구조

```
mysql-mcp/
├── server/                          # MCP 서버 소스
│   ├── mysql_mcp_server.py         # 기본 MCP 서버
│   ├── mysql_mcp_server_v2.py      # 개선된 MCP 서버 (Groq API 지원, 권장)
│   ├── fastmcp_mysql_server.py     # FastMCP 프레임워크 서버 (Groq API 지원)
│   ├── config.py                   # 설정 관리
│   ├── mysql_manager.py            # MySQL 연결 관리
│   ├── natural_language_processor.py # 자연어 처리
│   ├── run_server.py               # 기존 서버 실행 스크립트
│   ├── run_framework_server.py     # 서버 실행 스크립트
│   ├── requirements.txt            # 서버 의존성
│   └── env_example.txt             # 환경 변수 예제
├── client/                         # 테스트 클라이언트
│   ├── test_client.py              # 기존 MCP 서버 테스트 클라이언트
│   ├── test_fastmcp_client.py      # 개선된 테스트 클라이언트
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
- Groq API 키 (권장) 또는 OpenAI API 키

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

#### Groq API 설정 (권장)
1. [Groq Console](https://console.groq.com/)에서 API 키를 발급받으세요
2. 환경 변수에 Groq API 키를 설정하세요:
   ```bash
   export GROQ_API_KEY=your_groq_api_key
   export GROQ_API_BASE=https://api.groq.com/openai/v1
   export GROQ_MODEL=llama3-8b-8192
   ```

#### OpenAI API 설정 (대체)
Groq API를 사용할 수 없는 경우 OpenAI API를 대체로 사용할 수 있습니다:

```bash
# MySQL 설정
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=your_password
export MYSQL_DATABASE=test_db

# Groq API 설정 (llama3-8b-8192 모델 사용)
export GROQ_API_KEY=your_groq_api_key
export GROQ_API_BASE=https://api.groq.com/openai/v1
export GROQ_MODEL=llama3-8b-8192

# OpenAI API 설정 (기존 호환성을 위해 유지)
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

#### 개선된 MCP 서버 (권장)
```bash
cd server
python run_framework_server.py improved
```

#### FastMCP 프레임워크 서버
```bash
cd server
python run_framework_server.py fastmcp
```

#### 기본 MCP 서버
```bash
cd server
python run_framework_server.py basic
```

#### 서버 목록 조회
```bash
cd server
python run_framework_server.py list
```

### 2. 클라이언트 테스트

#### 기존 클라이언트
```bash
cd client
pip install -r requirements.txt
python test_client.py
```

#### 개선된 클라이언트
```bash
cd client
python test_fastmcp_client.py improved
python test_fastmcp_client.py fastmcp
python test_fastmcp_client.py basic
python test_fastmcp_client.py compare  # 서버 비교 테스트
```

### 3. Cursor IDE에서 사용

1. Cursor IDE의 설정에서 MCP 서버를 추가
2. 서버 경로 선택:
   - 개선된 서버 (권장): `python /path/to/mysql-mcp/server/mysql_mcp_server_v2.py`
   - FastMCP 서버: `python /path/to/mysql-mcp/server/fastmcp_mysql_server.py`
   - 기본 서버: `python /path/to/mysql-mcp/server/mysql_mcp_server.py`
3. 채팅에서 자연어로 쿼리 실행

### 4. 사용 예시

```
사용자: "사용자 테이블에서 모든 데이터를 조회해줘"
MCP: SELECT * FROM users LIMIT 10

사용자: "테이블 목록을 보여줘"
MCP: SHOW TABLES

사용자: "users 테이블의 구조를 설명해줘"
MCP: DESCRIBE users

사용자: "테이블 구조를 설명해줘"
MCP: DESCRIBE users

## 🔄 서버 비교

### 개선된 MCP vs FastMCP vs 기본 MCP

| 기능 | 기본 MCP | 개선된 MCP | FastMCP |
|------|----------|------------|---------|
| **Groq API 지원** | ❌ | ✅ | ✅ |
| **스트리밍 지원** | ✅ | ✅ | ✅ |
| **자연어 처리** | 기본 | 고급 | 고급 |
| **에러 처리** | 기본 | 개선됨 | 개선됨 |
| **로깅** | 기본 | 상세함 | 상세함 |
| **모듈화** | 기본 | 완전 분리 | 완전 분리 |
| **설정 관리** | 하드코딩 | 환경 변수 | 환경 변수 |
| **개발 편의성** | 기본 | 기본 | ⭐⭐⭐⭐ |
| **코드 간결성** | 기본 | 기본 | ⭐⭐⭐⭐ |
| **타입 안전성** | 기본 | 기본 | ⭐⭐⭐⭐ |

### 개선된 MCP 서버 특징
- **스트리밍 지원**: 실시간 진행 상황 표시 및 청크 단위 결과 전송
- **Groq API 통합**: llama3-8b-8192 모델을 사용한 고성능 자연어 처리
- **모듈화된 구조**: 기능별로 분리된 깔끔한 코드 구조
- **환경 변수 설정**: 유연한 설정 관리
- **상세한 로깅**: 디버깅과 모니터링을 위한 로그 시스템
- **안전성 강화**: SQL 인젝션 방지 및 쿼리 검증

### FastMCP 서버 특징
- **스트리밍 지원**: 실시간 진행 상황 표시 및 청크 단위 결과 전송
- **간단한 데코레이터**: `@self.tool()` 데코레이터로 쉽게 도구 등록
- **Pydantic 모델**: 타입 안전한 입력 검증
- **자동 스키마 생성**: 입력 모델에서 자동으로 JSON 스키마 생성
- **Groq API 통합**: llama3-8b-8192 모델을 사용한 고성능 자연어 처리
- **모듈화된 구조**: 기능별로 분리된 깔끔한 코드 구조

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

#### FastMCP 서버에서 (권장)
```python
@self.tool(
    name="new_tool",
    description="새로운 도구 설명"
)
async def new_tool(self, input_data: InputModel) -> ToolResult:
    # 도구 로직 구현
    return ToolResult(success=True, content="결과")
```

#### 개선된 MCP 서버에서
```python
# mysql_mcp_server_v2.py의 _handle_list_tools 메서드에 도구 정의 추가
Tool(
    name="new_tool",
    description="새로운 도구 설명",
    inputSchema={
        "type": "object",
        "properties": {
            "parameter": {
                "type": "string",
                "description": "매개변수 설명"
            }
        },
        "required": ["parameter"]
    }
)

# _handle_call_tool 메서드에 도구 처리 로직 추가
elif request.name == "new_tool":
    return await self._handle_new_tool(request.arguments)
```

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
python test_fastmcp_client.py fastmcp --interactive
python test_fastmcp_client.py fymcp --interactive
python test_fastmcp_client.py compare
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
- Groq API 키 설정 확인 (우선순위)
- OpenAI API 키 설정 확인 (대체)
- 네트워크 연결 확인
- 기본 변환 로직으로 대체

#### 4. Cursor IDE에서 인식되지 않음
- MCP 서버 경로 확인
- 서버 실행 권한 확인
- Cursor IDE 재시작

#### 5. 프레임워크 관련 오류
- FastMCP/FyMCP 패키지 설치 확인
- Pydantic 버전 호환성 확인
- 프레임워크별 문서 참조

### 로그 확인

서버 로그를 확인하여 문제를 진단할 수 있습니다:

```bash
export LOG_LEVEL=DEBUG
python run_framework_server.py fastmcp --debug
python run_framework_server.py fymcp --debug
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
- [Groq API Documentation](https://console.groq.com/docs)
- [Llama 3 Model Information](https://huggingface.co/meta-llama/Meta-Llama-3-8B)
- [FastMCP Documentation](https://github.com/fastmcp/fastmcp)
