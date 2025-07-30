#!/usr/bin/env python3
"""
MySQL MCP(Model Context Protocol) Server
Cursor AI에서 MySQL 데이터베이스에 자연어로 쿼리할 수 있는 MCP 서버
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
    """MySQL MCP 서버 클래스"""
    
    def __init__(self):
        """서버 초기화"""
        self.server = Server("mysql-mcp-server")
        self.mysql_connection = None
        self.openai_client = None
        
        # 서버에 도구 등록
        self.server.list_tools(self._handle_list_tools)
        self.server.call_tool(self._handle_call_tool)
        
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
            # 자연어를 SQL로 변환
            sql_query = await self._convert_natural_to_sql(natural_query)
            if not sql_query:
                return CallToolResult(
                    content=[TextContent(type="text", text="자연어를 SQL로 변환할 수 없습니다.")]
                )
            
            # MySQL 쿼리 실행
            result = await self._execute_mysql_query(sql_query)
            
            return CallToolResult(
                content=[TextContent(type="text", text=result)]
            )
        except Exception as e:
            logger.error(f"MySQL 쿼리 실행 중 오류: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"쿼리 실행 중 오류 발생: {str(e)}")]
            )
    
    async def _handle_list_tables(self, arguments: Dict[str, Any]) -> CallToolResult:
        """테이블 목록 조회"""
        try:
            if not self.mysql_connection:
                await self._connect_mysql()
            
            cursor = self.mysql_connection.cursor()
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            cursor.close()
            
            table_list = "\n".join([table[0] for table in tables])
            result = f"데이터베이스의 테이블 목록:\n{table_list}"
            
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
            if not self.mysql_connection:
                await self._connect_mysql()
            
            cursor = self.mysql_connection.cursor()
            cursor.execute(f"DESCRIBE {table_name}")
            columns = cursor.fetchall()
            cursor.close()
            
            result = f"테이블 '{table_name}' 구조:\n"
            for column in columns:
                result += f"- {column[0]}: {column[1]} ({column[2]})\n"
            
            return CallToolResult(
                content=[TextContent(type="text", text=result)]
            )
        except Exception as e:
            logger.error(f"테이블 구조 조회 중 오류: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"테이블 구조 조회 중 오류 발생: {str(e)}")]
            )
    
    async def _convert_natural_to_sql(self, natural_query: str) -> Optional[str]:
        """자연어를 SQL로 변환 (OpenAI API 사용)"""
        try:
            if not self.openai_client:
                # OpenAI API 키가 설정되어 있지 않으면 기본 SQL 변환 로직 사용
                return self._basic_natural_to_sql(natural_query)
            
            # OpenAI API를 사용한 고급 자연어 변환
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 자연어를 MySQL SQL 쿼리로 변환하는 전문가입니다. SELECT 쿼리만 생성하세요."},
                    {"role": "user", "content": f"다음 자연어를 MySQL SQL로 변환해주세요: {natural_query}"}
                ],
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"OpenAI API 변환 실패, 기본 변환 사용: {e}")
            return self._basic_natural_to_sql(natural_query)
    
    def _basic_natural_to_sql(self, natural_query: str) -> str:
        """기본적인 자연어를 SQL로 변환하는 로직"""
        query_lower = natural_query.lower()
        
        # 기본적인 패턴 매칭
        if "모든" in query_lower and "조회" in query_lower:
            # 테이블 이름 추출 시도
            words = natural_query.split()
            for i, word in enumerate(words):
                if "테이블" in word and i > 0:
                    table_name = words[i-1]
                    return f"SELECT * FROM {table_name}"
        
        # 기본 SELECT 쿼리
        return f"SELECT * FROM users LIMIT 10"
    
    async def _connect_mysql(self):
        """MySQL 데이터베이스 연결"""
        try:
            # 환경 변수에서 설정 읽기 (실제 구현시 설정 파일 사용 권장)
            config = {
                'host': 'localhost',
                'user': 'root',
                'password': '',
                'database': 'test_db'
            }
            
            self.mysql_connection = mysql.connector.connect(**config)
            logger.info("MySQL 데이터베이스에 성공적으로 연결되었습니다.")
        except Error as e:
            logger.error(f"MySQL 연결 실패: {e}")
            raise
    
    async def _execute_mysql_query(self, sql_query: str) -> str:
        """MySQL 쿼리 실행"""
        if not self.mysql_connection:
            await self._connect_mysql()
        
        try:
            cursor = self.mysql_connection.cursor(dictionary=True)
            cursor.execute(sql_query)
            
            if sql_query.strip().upper().startswith('SELECT'):
                results = cursor.fetchall()
                cursor.close()
                
                if not results:
                    return "조회 결과가 없습니다."
                
                # 결과를 보기 좋게 포맷팅
                result_str = "조회 결과:\n"
                for i, row in enumerate(results, 1):
                    result_str += f"\n--- 레코드 {i} ---\n"
                    for key, value in row.items():
                        result_str += f"{key}: {value}\n"
                
                return result_str
            else:
                self.mysql_connection.commit()
                cursor.close()
                return "쿼리가 성공적으로 실행되었습니다."
                
        except Error as e:
            logger.error(f"MySQL 쿼리 실행 오류: {e}")
            raise
    
    async def run(self):
        """서버 실행"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
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
    server = MySQLMCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main()) 