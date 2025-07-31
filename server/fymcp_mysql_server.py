#!/usr/bin/env python3
"""
FyMCP MySQL MCP(Model Context Protocol) Server
FyMCP 프레임워크를 사용하여 구현한 MySQL MCP 서버
Cursor AI에서 MySQL 데이터베이스에 자연어로 쿼리할 수 있는 MCP 서버
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from fymcp import FyMCP, Tool, ToolResult, ToolInput
from pydantic import BaseModel, Field

# 로컬 모듈 임포트
from config import Config
from mysql_manager import MySQLManager
from natural_language_processor import NaturalLanguageProcessor

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Pydantic 모델 정의
class NaturalLanguageQueryInput(ToolInput):
    """자연어 쿼리 입력 모델"""
    natural_language_query: str = Field(
        description="실행할 자연어 쿼리",
        example="사용자 테이블에서 모든 데이터를 조회해줘"
    )

class TableNameQueryInput(ToolInput):
    """테이블명 쿼리 입력 모델"""
    table_name: str = Field(
        description="조회할 테이블 이름",
        example="users"
    )

class FyMCPMySQLServer(FyMCP):
    """FyMCP를 사용한 MySQL MCP 서버 클래스"""
    
    def __init__(self):
        """서버 초기화"""
        super().__init__(
            name=Config.SERVER_NAME,
            version=Config.SERVER_VERSION,
            description="MySQL 데이터베이스에 자연어로 쿼리할 수 있는 MCP 서버"
        )
        
        # MySQL 관리자와 자연어 처리기 초기화
        self.mysql_manager = MySQLManager()
        self.nlp_processor = NaturalLanguageProcessor()
        
        # 도구 등록
        self._register_tools()
        
        logger.info("FyMCP MySQL MCP 서버가 초기화되었습니다.")
    
    def _register_tools(self):
        """MCP 도구들을 등록"""
        
        @self.tool(
            name="query_mysql",
            description="MySQL 데이터베이스에 자연어로 쿼리를 실행합니다. 예: '사용자 테이블에서 모든 데이터를 조회해줘'",
            input_model=NaturalLanguageQueryInput
        )
        async def query_mysql(input_data: NaturalLanguageQueryInput) -> ToolResult:
            """MySQL 자연어 쿼리 처리"""
            try:
                logger.info(f"자연어 쿼리 처리: {input_data.natural_language_query}")
                
                # 자연어를 SQL로 변환 (Groq API 사용)
                sql_query = await self.nlp_processor.convert_to_sql(input_data.natural_language_query)
                if not sql_query:
                    return ToolResult(
                        success=False,
                        content="자연어를 SQL로 변환할 수 없습니다. Groq API 키를 확인하세요.",
                        error_code="NLP_CONVERSION_FAILED"
                    )
                
                logger.info(f"변환된 SQL: {sql_query}")
                
                # SQL 쿼리 유효성 검사
                is_valid, validation_message = self.mysql_manager.validate_sql_query(sql_query)
                if not is_valid:
                    return ToolResult(
                        success=False,
                        content=f"유효하지 않은 쿼리: {validation_message}",
                        error_code="INVALID_SQL_QUERY"
                    )
                
                # MySQL 쿼리 실행
                success, message, results = await self.mysql_manager.execute_query(sql_query)
                
                if success:
                    if results:
                        # 결과 포맷팅
                        formatted_result = self.mysql_manager.format_query_results(results)
                        return ToolResult(
                            success=True,
                            content=formatted_result,
                            metadata={
                                "sql_query": sql_query,
                                "result_count": len(results)
                            }
                        )
                    else:
                        return ToolResult(
                            success=True,
                            content=message,
                            metadata={"sql_query": sql_query}
                        )
                else:
                    return ToolResult(
                        success=False,
                        content=f"쿼리 실행 실패: {message}",
                        error_code="QUERY_EXECUTION_FAILED"
                    )
                    
            except Exception as e:
                logger.error(f"MySQL 쿼리 실행 중 오류: {e}")
                return ToolResult(
                    success=False,
                    content=f"쿼리 실행 중 오류 발생: {str(e)}",
                    error_code="INTERNAL_ERROR"
                )
        
        @self.tool(
            name="list_tables",
            description="MySQL 데이터베이스의 모든 테이블 목록을 조회합니다."
        )
        async def list_tables() -> ToolResult:
            """테이블 목록 조회"""
            try:
                tables = await self.mysql_manager.get_tables()
                
                if tables:
                    table_list = "\n".join([f"- {table}" for table in tables])
                    result = f"데이터베이스의 테이블 목록:\n{table_list}"
                    
                    return ToolResult(
                        success=True,
                        content=result,
                        metadata={
                            "table_count": len(tables),
                            "tables": tables
                        }
                    )
                else:
                    return ToolResult(
                        success=True,
                        content="데이터베이스에 테이블이 없습니다.",
                        metadata={"table_count": 0}
                    )
            except Exception as e:
                logger.error(f"테이블 목록 조회 중 오류: {e}")
                return ToolResult(
                    success=False,
                    content=f"테이블 목록 조회 중 오류 발생: {str(e)}",
                    error_code="TABLE_LIST_ERROR"
                )
        
        @self.tool(
            name="describe_table",
            description="특정 테이블의 구조를 조회합니다.",
            input_model=TableNameQueryInput
        )
        async def describe_table(input_data: TableNameQueryInput) -> ToolResult:
            """테이블 구조 조회"""
            try:
                columns = await self.mysql_manager.describe_table(input_data.table_name)
                
                if columns:
                    result = f"테이블 '{input_data.table_name}' 구조:\n"
                    for column in columns:
                        field = column.get('Field', '')
                        type_info = column.get('Type', '')
                        null_info = column.get('Null', '')
                        key_info = column.get('Key', '')
                        default_info = column.get('Default', '')
                        
                        result += f"- {field}: {type_info}"
                        if null_info == 'NO':
                            result += " (NOT NULL)"
                        if key_info:
                            result += f" (Key: {key_info})"
                        if default_info:
                            result += f" (Default: {default_info})"
                        result += "\n"
                    
                    return ToolResult(
                        success=True,
                        content=result,
                        metadata={
                            "table_name": input_data.table_name,
                            "column_count": len(columns),
                            "columns": columns
                        }
                    )
                else:
                    return ToolResult(
                        success=False,
                        content=f"테이블 '{input_data.table_name}'을 찾을 수 없습니다.",
                        error_code="TABLE_NOT_FOUND"
                    )
            except Exception as e:
                logger.error(f"테이블 구조 조회 중 오류: {e}")
                return ToolResult(
                    success=False,
                    content=f"테이블 구조 조회 중 오류 발생: {str(e)}",
                    error_code="DESCRIBE_TABLE_ERROR"
                )
        
        @self.tool(
            name="get_table_info",
            description="테이블의 상세 정보(구조, 레코드 수, 샘플 데이터)를 조회합니다.",
            input_model=TableNameQueryInput
        )
        async def get_table_info(input_data: TableNameQueryInput) -> ToolResult:
            """테이블 상세 정보 조회"""
            try:
                table_info = await self.mysql_manager.get_table_info(input_data.table_name)
                
                result = f"테이블 '{input_data.table_name}' 상세 정보:\n\n"
                result += f"레코드 수: {table_info['record_count']}\n\n"
                
                if table_info['columns']:
                    result += "컬럼 구조:\n"
                    for column in table_info['columns']:
                        field = column.get('Field', '')
                        type_info = column.get('Type', '')
                        result += f"- {field}: {type_info}\n"
                    
                    result += "\n"
                
                if table_info['sample_data']:
                    result += "샘플 데이터:\n"
                    for i, row in enumerate(table_info['sample_data'], 1):
                        result += f"\n--- 샘플 {i} ---\n"
                        for key, value in row.items():
                            result += f"{key}: {value}\n"
                else:
                    result += "샘플 데이터가 없습니다."
                
                return ToolResult(
                    success=True,
                    content=result,
                    metadata={
                        "table_name": input_data.table_name,
                        "record_count": table_info['record_count'],
                        "column_count": len(table_info['columns']),
                        "sample_count": len(table_info['sample_data'])
                    }
                )
            except Exception as e:
                logger.error(f"테이블 정보 조회 중 오류: {e}")
                return ToolResult(
                    success=False,
                    content=f"테이블 정보 조회 중 오류 발생: {str(e)}",
                    error_code="GET_TABLE_INFO_ERROR"
                )
        
        @self.tool(
            name="test_connection",
            description="MySQL 데이터베이스 연결을 테스트합니다."
        )
        async def test_connection() -> ToolResult:
            """데이터베이스 연결 테스트"""
            try:
                is_connected = await self.mysql_manager.test_connection()
                
                if is_connected:
                    result = "MySQL 데이터베이스 연결이 정상입니다."
                    return ToolResult(
                        success=True,
                        content=result,
                        metadata={"connection_status": "connected"}
                    )
                else:
                    result = "MySQL 데이터베이스 연결에 실패했습니다."
                    return ToolResult(
                        success=False,
                        content=result,
                        error_code="CONNECTION_FAILED",
                        metadata={"connection_status": "failed"}
                    )
            except Exception as e:
                logger.error(f"연결 테스트 중 오류: {e}")
                return ToolResult(
                    success=False,
                    content=f"연결 테스트 중 오류 발생: {str(e)}",
                    error_code="CONNECTION_TEST_ERROR"
                )
        
        @self.tool(
            name="get_database_stats",
            description="데이터베이스 통계 정보를 조회합니다."
        )
        async def get_database_stats() -> ToolResult:
            """데이터베이스 통계 정보 조회"""
            try:
                # 테이블 목록 조회
                tables = await self.mysql_manager.get_tables()
                
                # 각 테이블의 레코드 수 조회
                table_stats = {}
                total_records = 0
                
                for table in tables:
                    try:
                        success, message, results = await self.mysql_manager.execute_query(f"SELECT COUNT(*) as count FROM {table}")
                        if success and results:
                            record_count = results[0]['count']
                            table_stats[table] = record_count
                            total_records += record_count
                    except Exception:
                        table_stats[table] = "조회 실패"
                
                result = f"데이터베이스 통계 정보:\n\n"
                result += f"총 테이블 수: {len(tables)}\n"
                result += f"총 레코드 수: {total_records}\n\n"
                
                result += "테이블별 레코드 수:\n"
                for table, count in table_stats.items():
                    result += f"- {table}: {count}\n"
                
                return ToolResult(
                    success=True,
                    content=result,
                    metadata={
                        "table_count": len(tables),
                        "total_records": total_records,
                        "table_stats": table_stats
                    }
                )
            except Exception as e:
                logger.error(f"데이터베이스 통계 조회 중 오류: {e}")
                return ToolResult(
                    success=False,
                    content=f"데이터베이스 통계 조회 중 오류 발생: {str(e)}",
                    error_code="STATS_ERROR"
                )
    
    async def startup(self):
        """서버 시작 시 실행되는 메서드"""
        logger.info("FyMCP MySQL 서버가 시작되었습니다.")
        
        # 설정 유효성 검사
        if not Config.validate_config():
            logger.warning("설정 검증에 실패했습니다. 기본값을 사용합니다.")
        
        # MySQL 연결 테스트
        try:
            is_connected = await self.mysql_manager.test_connection()
            if is_connected:
                logger.info("MySQL 데이터베이스 연결이 정상입니다.")
            else:
                logger.warning("MySQL 데이터베이스 연결에 실패했습니다.")
        except Exception as e:
            logger.error(f"MySQL 연결 테스트 중 오류: {e}")
    
    async def shutdown(self):
        """서버 종료 시 실행되는 메서드"""
        logger.info("FyMCP MySQL 서버를 종료합니다.")
        
        # MySQL 연결 풀 종료
        self.mysql_manager.close()

async def main():
    """메인 함수"""
    # FyMCP 서버 생성
    server = FyMCPMySQLServer()
    
    # 서버 실행
    await server.run()

if __name__ == "__main__":
    asyncio.run(main()) 