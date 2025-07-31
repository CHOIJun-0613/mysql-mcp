#!/usr/bin/env python3
"""
MySQL MCP(Model Context Protocol) Server - Streaming Version
Cursor AI에서 MySQL 데이터베이스에 자연어로 쿼리할 수 있는 MCP 서버
스트리밍 방식으로 결과를 실시간 전송하는 기본 버전
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional
import mysql.connector
from mysql.connector import Error
import openai
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
    ImageContent,
    EmbeddedResource,
    LoggingLevel,
)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MySQLMCPServer:
    """MySQL MCP 서버 클래스 (스트리밍 버전)"""
    
    def __init__(self):
        """서버 초기화"""
        self.server = Server("mysql-mcp-server")
        self.mysql_connection = None
        self.openai_client = None
        
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
            
            # 자연어를 SQL로 변환
            progress_contents.append(await self._stream_progress("자연어를 SQL로 변환하고 있습니다..."))
            sql_query = await self._convert_natural_to_sql(natural_query)
            
            if not sql_query:
                progress_contents.append(await self._stream_error("자연어를 SQL로 변환할 수 없습니다."))
                return CallToolResult(content=progress_contents)
            
            progress_contents.append(await self._stream_success(f"SQL 변환 완료: {sql_query}"))
            
            # MySQL 쿼리 실행
            progress_contents.append(await self._stream_progress("MySQL 쿼리를 실행하고 있습니다..."))
            result = await self._execute_mysql_query(sql_query)
            
            if result:
                progress_contents.append(await self._stream_success("쿼리 실행 완료"))
                
                # 결과를 스트리밍
                result_contents = await self._stream_text_content(result, chunk_size=800)
                progress_contents.extend(result_contents)
            else:
                progress_contents.append(await self._stream_error("쿼리 실행에 실패했습니다."))
            
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
            
            # MySQL 연결
            await self._connect_mysql()
            
            if not self.mysql_connection:
                progress_contents.append(await self._stream_error("MySQL 연결에 실패했습니다."))
                return CallToolResult(content=progress_contents)
            
            cursor = self.mysql_connection.cursor()
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            cursor.close()
            
            if tables:
                progress_contents.append(await self._stream_success(f"총 {len(tables)}개의 테이블을 찾았습니다."))
                
                # 테이블 목록을 스트리밍
                table_list = "\n".join([f"- {table[0]}" for table in tables])
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
            
            # MySQL 연결
            await self._connect_mysql()
            
            if not self.mysql_connection:
                progress_contents.append(await self._stream_error("MySQL 연결에 실패했습니다."))
                return CallToolResult(content=progress_contents)
            
            cursor = self.mysql_connection.cursor(dictionary=True)
            cursor.execute(f"DESCRIBE {table_name}")
            columns = cursor.fetchall()
            cursor.close()
            
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
    
    async def _convert_natural_to_sql(self, natural_query: str) -> Optional[str]:
        """자연어를 SQL로 변환"""
        try:
            # OpenAI API를 사용한 변환 (선택사항)
            if hasattr(self, 'openai_client') and self.openai_client:
                return await self._openai_natural_to_sql(natural_query)
            else:
                return self._basic_natural_to_sql(natural_query)
        except Exception as e:
            logger.error(f"자연어 변환 중 오류: {e}")
            return self._basic_natural_to_sql(natural_query)
    
    async def _openai_natural_to_sql(self, natural_query: str) -> Optional[str]:
        """OpenAI API를 사용한 자연어 변환"""
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 한국어 자연어를 MySQL SQL 쿼리로 변환하는 전문가입니다. SELECT 쿼리만 생성하세요."},
                    {"role": "user", "content": f"다음 한국어를 MySQL SQL로 변환해주세요: {natural_query}"}
                ],
                max_tokens=200,
                temperature=0.1
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"OpenAI 변환 실패: {e}")
            return None
    
    def _basic_natural_to_sql(self, natural_query: str) -> str:
        """기본 자연어 변환 로직"""
        query_lower = natural_query.lower()
        
        if "모든" in query_lower and "조회" in query_lower:
            # 테이블명 추출
            words = natural_query.split()
            for i, word in enumerate(words):
                if "테이블" in word and i > 0:
                    table_name = words[i-1]
                    return f"SELECT * FROM {table_name} LIMIT 10"
        
        # 기본 쿼리 반환
        return "SELECT * FROM users LIMIT 10"
    
    async def _connect_mysql(self):
        """MySQL 연결"""
        try:
            if not self.mysql_connection or not self.mysql_connection.is_connected():
                self.mysql_connection = mysql.connector.connect(
                    host="localhost",
                    user="root",
                    password="",
                    database="test_db",
                    charset="utf8mb4"
                )
                logger.info("MySQL 연결 성공")
        except Error as e:
            logger.error(f"MySQL 연결 실패: {e}")
            self.mysql_connection = None
    
    async def _execute_mysql_query(self, sql_query: str) -> str:
        """MySQL 쿼리 실행"""
        try:
            await self._connect_mysql()
            
            if not self.mysql_connection:
                return "MySQL 연결에 실패했습니다."
            
            cursor = self.mysql_connection.cursor(dictionary=True)
            cursor.execute(sql_query)
            results = cursor.fetchall()
            cursor.close()
            
            if results:
                # 결과 포맷팅
                formatted_result = "쿼리 결과:\n"
                for i, row in enumerate(results, 1):
                    formatted_result += f"\n--- 레코드 {i} ---\n"
                    for key, value in row.items():
                        formatted_result += f"{key}: {value}\n"
                return formatted_result
            else:
                return "쿼리가 실행되었지만 결과가 없습니다."
                
        except Error as e:
            logger.error(f"MySQL 쿼리 실행 오류: {e}")
            return f"쿼리 실행 오류: {str(e)}"
    
    async def run(self):
        """서버 실행"""
        async with stdio_server() as (read, write):
            await self.server.run(
                read,
                write,
                InitializationOptions(
                    server_name="mysql-mcp-server",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities=None,
                    ),
                ),
            )

async def main():
    """메인 함수"""
    try:
        # 서버 생성 및 실행
        server = MySQLMCPServer()
        
        logger.info("MySQL MCP 서버 (스트리밍)를 시작합니다...")
        logger.info("서버 이름: mysql-mcp-server")
        logger.info("서버 버전: 1.0.0")
        
        # 서버 실행
        await server.run()
        
    except KeyboardInterrupt:
        logger.info("서버가 사용자에 의해 중단되었습니다.")
    except Exception as e:
        logger.error(f"서버 실행 중 오류 발생: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 