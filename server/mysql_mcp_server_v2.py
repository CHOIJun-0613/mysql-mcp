#!/usr/bin/env python3
"""
MySQL MCP(Model Context Protocol) Server v2
Cursor AI에서 MySQL 데이터베이스에 자연어로 쿼리할 수 있는 MCP 서버
모듈화된 구조로 개선된 버전
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
)

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

class MySQLMCPServerV2:
    """MySQL MCP 서버 클래스 (개선된 버전)"""
    
    def __init__(self):
        """서버 초기화"""
        self.server = Server(Config.SERVER_NAME)
        self.mysql_manager = MySQLManager()
        self.nlp_processor = NaturalLanguageProcessor()
        
        # 서버에 도구 등록
        self.server.list_tools(self._handle_list_tools)
        self.server.call_tool(self._handle_call_tool)
        
        logger.info("MySQL MCP 서버가 초기화되었습니다.")
        
    async def _handle_list_tools(self, request: ListToolsRequest) -> ListToolsResult:
        """사용 가능한 도구 목록 반환"""
        tools = [
            Tool(
                name="query_mysql",
                description="MySQL 데이터베이스에 자연어로 쿼리를 실행합니다. 예: '사용자 테이블에서 모든 데이터를 조회해줘'",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "natural_language_query": {
                            "type": "string",
                            "description": "실행할 자연어 쿼리"
                        }
                    },
                    "required": ["natural_language_query"]
                }
            ),
            Tool(
                name="list_tables",
                description="MySQL 데이터베이스의 모든 테이블 목록을 조회합니다.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="describe_table",
                description="특정 테이블의 구조를 조회합니다.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "table_name": {
                            "type": "string",
                            "description": "조회할 테이블 이름"
                        }
                    },
                    "required": ["table_name"]
                }
            ),
            Tool(
                name="get_table_info",
                description="테이블의 상세 정보(구조, 레코드 수, 샘플 데이터)를 조회합니다.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "table_name": {
                            "type": "string",
                            "description": "조회할 테이블 이름"
                        }
                    },
                    "required": ["table_name"]
                }
            ),
            Tool(
                name="test_connection",
                description="MySQL 데이터베이스 연결을 테스트합니다.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            )
        ]
        return ListToolsResult(tools=tools)
    
    async def _handle_call_tool(self, request: CallToolRequest) -> CallToolResult:
        """도구 호출 처리"""
        try:
            if request.name == "query_mysql":
                return await self._handle_mysql_query(request.arguments)
            elif request.name == "list_tables":
                return await self._handle_list_tables(request.arguments)
            elif request.name == "describe_table":
                return await self._handle_describe_table(request.arguments)
            elif request.name == "get_table_info":
                return await self._handle_get_table_info(request.arguments)
            elif request.name == "test_connection":
                return await self._handle_test_connection(request.arguments)
            else:
                raise ValueError(f"알 수 없는 도구: {request.name}")
        except Exception as e:
            logger.error(f"도구 실행 중 오류 발생: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"오류 발생: {str(e)}")]
            )
    
    async def _handle_mysql_query(self, arguments: Dict[str, Any]) -> CallToolResult:
        """MySQL 자연어 쿼리 처리"""
        natural_query = arguments.get("natural_language_query", "")
        if not natural_query:
            return CallToolResult(
                content=[TextContent(type="text", text="자연어 쿼리가 제공되지 않았습니다.")]
            )
        
        try:
            logger.info(f"자연어 쿼리 처리: {natural_query}")
            
            # 자연어를 SQL로 변환 (Groq API 사용)
            sql_query = await self.nlp_processor.convert_to_sql(natural_query)
            if not sql_query:
                return CallToolResult(
                    content=[TextContent(type="text", text="자연어를 SQL로 변환할 수 없습니다. Groq API 키를 확인하세요.")]
                )
            
            logger.info(f"변환된 SQL: {sql_query}")
            
            # SQL 쿼리 유효성 검사
            is_valid, validation_message = self.mysql_manager.validate_sql_query(sql_query)
            if not is_valid:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"유효하지 않은 쿼리: {validation_message}")]
                )
            
            # MySQL 쿼리 실행
            success, message, results = await self.mysql_manager.execute_query(sql_query)
            
            if success:
                if results:
                    # 결과 포맷팅
                    formatted_result = self.mysql_manager.format_query_results(results)
                    return CallToolResult(
                        content=[TextContent(type="text", text=formatted_result)]
                    )
                else:
                    return CallToolResult(
                        content=[TextContent(type="text", text=message)]
                    )
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"쿼리 실행 실패: {message}")]
                )
                
        except Exception as e:
            logger.error(f"MySQL 쿼리 실행 중 오류: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"쿼리 실행 중 오류 발생: {str(e)}")]
            )
    
    async def _handle_list_tables(self, arguments: Dict[str, Any]) -> CallToolResult:
        """테이블 목록 조회"""
        try:
            tables = await self.mysql_manager.get_tables()
            
            if tables:
                table_list = "\n".join([f"- {table}" for table in tables])
                result = f"데이터베이스의 테이블 목록:\n{table_list}"
            else:
                result = "데이터베이스에 테이블이 없습니다."
            
            return CallToolResult(
                content=[TextContent(type="text", text=result)]
            )
        except Exception as e:
            logger.error(f"테이블 목록 조회 중 오류: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"테이블 목록 조회 중 오류 발생: {str(e)}")]
            )
    
    async def _handle_describe_table(self, arguments: Dict[str, Any]) -> CallToolResult:
        """테이블 구조 조회"""
        table_name = arguments.get("table_name", "")
        if not table_name:
            return CallToolResult(
                content=[TextContent(type="text", text="테이블 이름이 제공되지 않았습니다.")]
            )
        
        try:
            columns = await self.mysql_manager.describe_table(table_name)
            
            if columns:
                result = f"테이블 '{table_name}' 구조:\n"
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
            else:
                result = f"테이블 '{table_name}'을 찾을 수 없습니다."
            
            return CallToolResult(
                content=[TextContent(type="text", text=result)]
            )
        except Exception as e:
            logger.error(f"테이블 구조 조회 중 오류: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"테이블 구조 조회 중 오류 발생: {str(e)}")]
            )
    
    async def _handle_get_table_info(self, arguments: Dict[str, Any]) -> CallToolResult:
        """테이블 상세 정보 조회"""
        table_name = arguments.get("table_name", "")
        if not table_name:
            return CallToolResult(
                content=[TextContent(type="text", text="테이블 이름이 제공되지 않았습니다.")]
            )
        
        try:
            table_info = await self.mysql_manager.get_table_info(table_name)
            
            result = f"테이블 '{table_name}' 상세 정보:\n\n"
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
            
            return CallToolResult(
                content=[TextContent(type="text", text=result)]
            )
        except Exception as e:
            logger.error(f"테이블 정보 조회 중 오류: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"테이블 정보 조회 중 오류 발생: {str(e)}")]
            )
    
    async def _handle_test_connection(self, arguments: Dict[str, Any]) -> CallToolResult:
        """데이터베이스 연결 테스트"""
        try:
            is_connected = await self.mysql_manager.test_connection()
            
            if is_connected:
                result = "MySQL 데이터베이스 연결이 정상입니다."
            else:
                result = "MySQL 데이터베이스 연결에 실패했습니다."
            
            return CallToolResult(
                content=[TextContent(type="text", text=result)]
            )
        except Exception as e:
            logger.error(f"연결 테스트 중 오류: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"연결 테스트 중 오류 발생: {str(e)}")]
            )
    
    async def run(self):
        """서버 실행"""
        try:
            # 설정 유효성 검사
            if not Config.validate_config():
                logger.warning("설정 검증에 실패했습니다. 기본값을 사용합니다.")
            
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name=Config.SERVER_NAME,
                        server_version=Config.SERVER_VERSION,
                        capabilities=self.server.get_capabilities(
                            notification_options=None,
                            experimental_capabilities=None,
                        ),
                    ),
                )
        except Exception as e:
            logger.error(f"서버 실행 중 오류: {e}")
            raise
        finally:
            # 리소스 정리
            self.mysql_manager.close()

async def main():
    """메인 함수"""
    server = MySQLMCPServerV2()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main()) 