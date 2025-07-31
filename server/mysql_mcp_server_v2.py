#!/usr/bin/env python3
"""
MySQL MCP(Model Context Protocol) Server v2 - Streaming Version
Cursor AI에서 MySQL 데이터베이스에 자연어로 쿼리할 수 있는 MCP 서버
스트리밍 방식으로 결과를 실시간 전송하는 개선된 버전
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional, AsyncGenerator
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
    """MySQL MCP 서버 클래스 (스트리밍 버전)"""
    
    def __init__(self):
        """서버 초기화"""
        self.server = Server(Config.SERVER_NAME)
        self.mysql_manager = MySQLManager()
        self.nlp_processor = NaturalLanguageProcessor()
        
        # 서버에 도구 등록
        self.server.list_tools(self._handle_list_tools)
        self.server.call_tool(self._handle_call_tool)
        
        logger.info("MySQL MCP 서버 (스트리밍)가 초기화되었습니다.")
    
    def _chunk_text(self, text: str, chunk_size: int = 1000) -> List[str]:
        """텍스트를 청크 단위로 분할"""
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunks.append(text[i:i + chunk_size])
        return chunks
    
    async def _stream_text_content(self, text: str, chunk_size: int = 1000) -> List[TextContent]:
        """텍스트를 스트리밍용 TextContent로 변환"""
        chunks = self._chunk_text(text, chunk_size)
        return [TextContent(type="text", text=chunk) for chunk in chunks]
    
    async def _stream_progress(self, message: str) -> TextContent:
        """진행 상황 메시지 스트리밍"""
        return TextContent(type="text", text=f"🔄 {message}")
    
    async def _stream_success(self, message: str) -> TextContent:
        """성공 메시지 스트리밍"""
        return TextContent(type="text", text=f"✅ {message}")
    
    async def _stream_error(self, message: str) -> TextContent:
        """에러 메시지 스트리밍"""
        return TextContent(type="text", text=f"❌ {message}")
        
    async def _handle_list_tools(self, request: ListToolsRequest) -> ListToolsResult:
        """사용 가능한 도구 목록 반환"""
        tools = [
            Tool(
                name="query_mysql",
                description="MySQL 데이터베이스에 자연어로 쿼리를 실행합니다. 스트리밍 방식으로 결과를 전송합니다. 예: '사용자 테이블에서 모든 데이터를 조회해줘'",
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
                description="MySQL 데이터베이스의 모든 테이블 목록을 조회합니다. 스트리밍 방식으로 결과를 전송합니다.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="describe_table",
                description="특정 테이블의 구조를 조회합니다. 스트리밍 방식으로 결과를 전송합니다.",
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
                description="테이블의 상세 정보(구조, 레코드 수, 샘플 데이터)를 조회합니다. 스트리밍 방식으로 결과를 전송합니다.",
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
        tool_name = request.name
        arguments = request.arguments
        
        logger.info(f"도구 호출: {tool_name}")
        
        if tool_name == "query_mysql":
            return await self._handle_mysql_query_streaming(arguments)
        elif tool_name == "list_tables":
            return await self._handle_list_tables_streaming(arguments)
        elif tool_name == "describe_table":
            return await self._handle_describe_table_streaming(arguments)
        elif tool_name == "get_table_info":
            return await self._handle_get_table_info_streaming(arguments)
        elif tool_name == "test_connection":
            return await self._handle_test_connection_streaming(arguments)
        else:
            return CallToolResult(
                content=[await self._stream_error(f"알 수 없는 도구: {tool_name}")]
            )
    
    async def _handle_mysql_query_streaming(self, arguments: Dict[str, Any]) -> CallToolResult:
        """MySQL 자연어 쿼리 처리 (스트리밍)"""
        natural_query = arguments.get("natural_language_query", "")
        if not natural_query:
            return CallToolResult(
                content=[await self._stream_error("자연어 쿼리가 제공되지 않았습니다.")]
            )
        
        try:
            # 진행 상황 스트리밍
            progress_contents = []
            progress_contents.append(await self._stream_progress("자연어 쿼리를 분석하고 있습니다..."))
            
            logger.info(f"자연어 쿼리 처리: {natural_query}")
            
            # 자연어를 SQL로 변환 (Groq API 사용)
            progress_contents.append(await self._stream_progress("Groq API를 사용하여 SQL로 변환하고 있습니다..."))
            sql_query = await self.nlp_processor.convert_to_sql(natural_query)
            
            if not sql_query:
                progress_contents.append(await self._stream_error("자연어를 SQL로 변환할 수 없습니다. Groq API 키를 확인하세요."))
                return CallToolResult(content=progress_contents)
            
            progress_contents.append(await self._stream_success(f"SQL 변환 완료: {sql_query}"))
            
            # SQL 쿼리 유효성 검사
            progress_contents.append(await self._stream_progress("SQL 쿼리 유효성을 검사하고 있습니다..."))
            is_valid, validation_message = self.mysql_manager.validate_sql_query(sql_query)
            
            if not is_valid:
                progress_contents.append(await self._stream_error(f"유효하지 않은 쿼리: {validation_message}"))
                return CallToolResult(content=progress_contents)
            
            progress_contents.append(await self._stream_success("SQL 쿼리 유효성 검사 통과"))
            
            # MySQL 쿼리 실행
            progress_contents.append(await self._stream_progress("MySQL 쿼리를 실행하고 있습니다..."))
            success, message, results = await self.mysql_manager.execute_query(sql_query)
            
            if success:
                progress_contents.append(await self._stream_success("쿼리 실행 완료"))
                
                if results:
                    # 결과를 스트리밍용으로 변환
                    progress_contents.append(await self._stream_progress("결과를 포맷팅하고 있습니다..."))
                    formatted_result = self.mysql_manager.format_query_results(results)
                    
                    # 결과를 청크 단위로 분할하여 스트리밍
                    result_contents = await self._stream_text_content(formatted_result, chunk_size=800)
                    progress_contents.extend(result_contents)
                else:
                    progress_contents.append(await self._stream_success(message))
            else:
                progress_contents.append(await self._stream_error(f"쿼리 실행 실패: {message}"))
            
            return CallToolResult(content=progress_contents)
                
        except Exception as e:
            logger.error(f"MySQL 쿼리 실행 중 오류: {e}")
            return CallToolResult(
                content=[await self._stream_error(f"쿼리 실행 중 오류 발생: {str(e)}")]
            )
    
    async def _handle_list_tables_streaming(self, arguments: Dict[str, Any]) -> CallToolResult:
        """테이블 목록 조회 (스트리밍)"""
        try:
            progress_contents = []
            progress_contents.append(await self._stream_progress("테이블 목록을 조회하고 있습니다..."))
            
            tables = await self.mysql_manager.get_tables()
            
            if tables:
                progress_contents.append(await self._stream_success(f"총 {len(tables)}개의 테이블을 찾았습니다."))
                
                # 테이블 목록을 스트리밍
                table_list = "\n".join([f"- {table}" for table in tables])
                result_contents = await self._stream_text_content(table_list, chunk_size=500)
                progress_contents.extend(result_contents)
            else:
                progress_contents.append(await self._stream_success("데이터베이스에 테이블이 없습니다."))
            
            return CallToolResult(content=progress_contents)
        except Exception as e:
            logger.error(f"테이블 목록 조회 중 오류: {e}")
            return CallToolResult(
                content=[await self._stream_error(f"테이블 목록 조회 중 오류 발생: {str(e)}")]
            )
    
    async def _handle_describe_table_streaming(self, arguments: Dict[str, Any]) -> CallToolResult:
        """테이블 구조 조회 (스트리밍)"""
        table_name = arguments.get("table_name", "")
        if not table_name:
            return CallToolResult(
                content=[await self._stream_error("테이블 이름이 제공되지 않았습니다.")]
            )
        
        try:
            progress_contents = []
            progress_contents.append(await self._stream_progress(f"테이블 '{table_name}'의 구조를 조회하고 있습니다..."))
            
            columns = await self.mysql_manager.describe_table(table_name)
            
            if columns:
                progress_contents.append(await self._stream_success(f"테이블 '{table_name}'의 {len(columns)}개 컬럼을 찾았습니다."))
                
                # 테이블 구조를 스트리밍
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
                
                result_contents = await self._stream_text_content(result, chunk_size=600)
                progress_contents.extend(result_contents)
            else:
                progress_contents.append(await self._stream_error(f"테이블 '{table_name}'을 찾을 수 없습니다."))
            
            return CallToolResult(content=progress_contents)
        except Exception as e:
            logger.error(f"테이블 구조 조회 중 오류: {e}")
            return CallToolResult(
                content=[await self._stream_error(f"테이블 구조 조회 중 오류 발생: {str(e)}")]
            )
    
    async def _handle_get_table_info_streaming(self, arguments: Dict[str, Any]) -> CallToolResult:
        """테이블 상세 정보 조회 (스트리밍)"""
        table_name = arguments.get("table_name", "")
        if not table_name:
            return CallToolResult(
                content=[await self._stream_error("테이블 이름이 제공되지 않았습니다.")]
            )
        
        try:
            progress_contents = []
            progress_contents.append(await self._stream_progress(f"테이블 '{table_name}'의 상세 정보를 조회하고 있습니다..."))
            
            # 테이블 구조 조회
            progress_contents.append(await self._stream_progress("테이블 구조를 조회하고 있습니다..."))
            columns = await self.mysql_manager.describe_table(table_name)
            
            if not columns:
                progress_contents.append(await self._stream_error(f"테이블 '{table_name}'을 찾을 수 없습니다."))
                return CallToolResult(content=progress_contents)
            
            progress_contents.append(await self._stream_success(f"테이블 구조 조회 완료 ({len(columns)}개 컬럼)"))
            
            # 레코드 수 조회
            progress_contents.append(await self._stream_progress("레코드 수를 조회하고 있습니다..."))
            count_success, count_message, count_result = await self.mysql_manager.execute_query(f"SELECT COUNT(*) as count FROM {table_name}")
            
            if count_success and count_result:
                record_count = count_result[0].get('count', 0)
                progress_contents.append(await self._stream_success(f"총 {record_count}개의 레코드가 있습니다."))
            else:
                progress_contents.append(await self._stream_error(f"레코드 수 조회 실패: {count_message}"))
            
            # 샘플 데이터 조회
            progress_contents.append(await self._stream_progress("샘플 데이터를 조회하고 있습니다..."))
            sample_success, sample_message, sample_result = await self.mysql_manager.execute_query(f"SELECT * FROM {table_name} LIMIT 5")
            
            if sample_success and sample_result:
                progress_contents.append(await self._stream_success(f"샘플 데이터 조회 완료 ({len(sample_result)}개 레코드)"))
                
                # 결과를 스트리밍
                sample_text = f"\n샘플 데이터 (최대 5개):\n{json.dumps(sample_result, indent=2, ensure_ascii=False)}"
                result_contents = await self._stream_text_content(sample_text, chunk_size=700)
                progress_contents.extend(result_contents)
            else:
                progress_contents.append(await self._stream_error(f"샘플 데이터 조회 실패: {sample_message}"))
            
            return CallToolResult(content=progress_contents)
        except Exception as e:
            logger.error(f"테이블 상세 정보 조회 중 오류: {e}")
            return CallToolResult(
                content=[await self._stream_error(f"테이블 상세 정보 조회 중 오류 발생: {str(e)}")]
            )
    
    async def _handle_test_connection_streaming(self, arguments: Dict[str, Any]) -> CallToolResult:
        """연결 테스트 (스트리밍)"""
        try:
            progress_contents = []
            progress_contents.append(await self._stream_progress("MySQL 데이터베이스 연결을 테스트하고 있습니다..."))
            
            success, message = await self.mysql_manager.test_connection()
            
            if success:
                progress_contents.append(await self._stream_success(f"MySQL 연결 성공: {message}"))
            else:
                progress_contents.append(await self._stream_error(f"MySQL 연결 실패: {message}"))
            
            return CallToolResult(content=progress_contents)
        except Exception as e:
            logger.error(f"연결 테스트 중 오류: {e}")
            return CallToolResult(
                content=[await self._stream_error(f"연결 테스트 중 오류 발생: {str(e)}")]
            )
    
    async def run(self):
        """서버 실행"""
        async with stdio_server() as (read, write):
            await self.server.run(
                read,
                write,
                InitializationOptions(
                    server_name=Config.SERVER_NAME,
                    server_version=Config.SERVER_VERSION,
                    capabilities=self.server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities=None,
                    ),
                ),
            )

async def main():
    """메인 함수"""
    try:
        # 설정 검증
        if not Config.validate_config():
            logger.error("설정 검증에 실패했습니다.")
            return
        
        # 서버 생성 및 실행
        server = MySQLMCPServerV2()
        
        logger.info("MySQL MCP 서버 (스트리밍)를 시작합니다...")
        logger.info(f"서버 이름: {Config.SERVER_NAME}")
        logger.info(f"서버 버전: {Config.SERVER_VERSION}")
        logger.info(f"MySQL 호스트: {Config.MYSQL_CONFIG['host']}")
        logger.info(f"MySQL 데이터베이스: {Config.MYSQL_CONFIG['database']}")
        
        # Groq API 설정 확인
        groq_config = Config.get_groq_config()
        if groq_config['api_key']:
            logger.info(f"Groq API 사용: {groq_config['model']}")
        else:
            logger.warning("Groq API 키가 설정되지 않았습니다. 기본 자연어 변환을 사용합니다.")
        
        # 서버 실행
        await server.run()
        
    except KeyboardInterrupt:
        logger.info("서버가 사용자에 의해 중단되었습니다.")
    except Exception as e:
        logger.error(f"서버 실행 중 오류 발생: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 