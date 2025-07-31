#!/usr/bin/env python3
"""
FastMCP MySQL MCP 서버 - Streaming Version
FastMCP 프레임워크를 사용한 MySQL MCP 서버 구현
스트리밍 방식으로 결과를 실시간 전송하는 버전
Groq API와 llama3-8b-8192 모델을 지원합니다.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from fastmcp import FastMCP, Tool, ToolResult
from pydantic import BaseModel, Field

from config import Config
from mysql_manager import MySQLManager
from natural_language_processor import NaturalLanguageProcessor

# 로깅 설정
logging.basicConfig(level=getattr(logging, Config.LOG_LEVEL))
logger = logging.getLogger(__name__)

# Pydantic 모델 정의
class NaturalLanguageQuery(BaseModel):
    """자연어 쿼리 입력 모델"""
    natural_language_query: str = Field(
        ..., 
        description="MySQL 쿼리로 변환할 자연어 질문",
        examples=["사용자 테이블에서 모든 데이터를 조회해줘", "users 테이블의 레코드 수를 알려줘"]
    )

class TableNameQuery(BaseModel):
    """테이블명 쿼리 입력 모델"""
    table_name: str = Field(
        ..., 
        description="조회할 테이블명",
        examples=["users", "orders", "products"]
    )

class FastMCPMySQLServer(FastMCP):
    """FastMCP를 사용한 MySQL MCP 서버 (스트리밍 버전)"""
    
    def __init__(self):
        """초기화"""
        super().__init__(
            name=Config.SERVER_NAME,
            version=Config.SERVER_VERSION,
            description="FastMCP 프레임워크를 사용한 MySQL MCP 서버 (스트리밍, Groq API 지원)"
        )
        
        # 컴포넌트 초기화
        self.mysql_manager = MySQLManager()
        self.nlp_processor = NaturalLanguageProcessor()
        
        # 도구 등록
        self._register_tools()
        
        logger.info("FastMCP MySQL MCP 서버 (스트리밍)가 초기화되었습니다.")
    
    def _chunk_text(self, text: str, chunk_size: int = 1000) -> List[str]:
        """텍스트를 청크 단위로 분할"""
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunks.append(text[i:i + chunk_size])
        return chunks
    
    def _create_streaming_content(self, text: str, chunk_size: int = 1000) -> str:
        """텍스트를 스트리밍용으로 변환"""
        chunks = self._chunk_text(text, chunk_size)
        return "\n".join(chunks)
    
    def _create_progress_message(self, message: str) -> str:
        """진행 상황 메시지 생성"""
        return f"🔄 {message}"
    
    def _create_success_message(self, message: str) -> str:
        """성공 메시지 생성"""
        return f"✅ {message}"
    
    def _create_error_message(self, message: str) -> str:
        """에러 메시지 생성"""
        return f"❌ {message}"
    
    def _register_tools(self):
        """MCP 도구들을 등록"""
        logger.info("FastMCP 도구들을 등록합니다...")
    
    @self.tool(
        name="query_mysql",
        description="자연어를 MySQL SQL로 변환하여 쿼리를 실행합니다. 스트리밍 방식으로 결과를 전송합니다. Groq API와 llama3-8b-8192 모델을 사용합니다."
    )
    async def query_mysql(self, query: NaturalLanguageQuery) -> ToolResult:
        """자연어 쿼리 처리 (스트리밍)"""
        try:
            # 진행 상황 메시지 수집
            progress_messages = []
            progress_messages.append(self._create_progress_message("자연어 쿼리를 분석하고 있습니다..."))
            
            logger.info(f"자연어 쿼리 처리: {query.natural_language_query}")
            
            # 자연어를 SQL로 변환 (Groq API 사용)
            progress_messages.append(self._create_progress_message("Groq API를 사용하여 SQL로 변환하고 있습니다..."))
            sql_query = await self.nlp_processor.convert_to_sql(query.natural_language_query)
            
            if not sql_query:
                progress_messages.append(self._create_error_message("자연어를 SQL로 변환할 수 없습니다. Groq API 키를 확인하세요."))
                return ToolResult(
                    success=False,
                    content="\n".join(progress_messages)
                )
            
            progress_messages.append(self._create_success_message(f"SQL 변환 완료: {sql_query}"))
            
            # SQL 쿼리 실행
            progress_messages.append(self._create_progress_message("MySQL 쿼리를 실행하고 있습니다..."))
            success, message, results = await self.mysql_manager.execute_query(sql_query)
            
            if success:
                progress_messages.append(self._create_success_message("쿼리 실행 완료"))
                
                if results:
                    # 결과를 스트리밍용으로 변환
                    progress_messages.append(self._create_progress_message("결과를 포맷팅하고 있습니다..."))
                    formatted_result = self.mysql_manager.format_query_results(results)
                    
                    # 결과를 청크 단위로 분할하여 스트리밍
                    streaming_content = self._create_streaming_content(formatted_result, chunk_size=800)
                    progress_messages.append(streaming_content)
                else:
                    progress_messages.append(self._create_success_message(message))
            else:
                progress_messages.append(self._create_error_message(f"쿼리 실행 실패: {message}"))
            
            return ToolResult(
                success=True,
                content="\n".join(progress_messages)
            )
                
        except Exception as e:
            logger.error(f"자연어 쿼리 처리 중 오류: {e}")
            return ToolResult(
                success=False,
                content=self._create_error_message(f"쿼리 처리 중 오류가 발생했습니다: {str(e)}")
            )
    
    @self.tool(
        name="list_tables",
        description="데이터베이스의 모든 테이블 목록을 조회합니다. 스트리밍 방식으로 결과를 전송합니다."
    )
    async def list_tables(self) -> ToolResult:
        """테이블 목록 조회 (스트리밍)"""
        try:
            progress_messages = []
            progress_messages.append(self._create_progress_message("테이블 목록을 조회하고 있습니다..."))
            
            logger.info("테이블 목록 조회")
            
            success, message, results = await self.mysql_manager.list_tables()
            
            if success:
                progress_messages.append(self._create_success_message(f"총 {len(results)}개의 테이블을 찾았습니다."))
                
                # 테이블 목록을 스트리밍
                table_list = "\n".join([f"- {table}" for table in results])
                streaming_content = self._create_streaming_content(table_list, chunk_size=500)
                progress_messages.append(streaming_content)
            else:
                progress_messages.append(self._create_error_message(f"테이블 목록 조회 실패: {message}"))
            
            return ToolResult(
                success=success,
                content="\n".join(progress_messages)
            )
                
        except Exception as e:
            logger.error(f"테이블 목록 조회 중 오류: {e}")
            return ToolResult(
                success=False,
                content=self._create_error_message(f"테이블 목록 조회 중 오류가 발생했습니다: {str(e)}")
            )
    
    @self.tool(
        name="describe_table",
        description="지정된 테이블의 구조를 조회합니다. 스트리밍 방식으로 결과를 전송합니다."
    )
    async def describe_table(self, table_query: TableNameQuery) -> ToolResult:
        """테이블 구조 조회 (스트리밍)"""
        try:
            progress_messages = []
            progress_messages.append(self._create_progress_message(f"테이블 '{table_query.table_name}'의 구조를 조회하고 있습니다..."))
            
            logger.info(f"테이블 구조 조회: {table_query.table_name}")
            
            success, message, results = await self.mysql_manager.describe_table(table_query.table_name)
            
            if success:
                progress_messages.append(self._create_success_message(f"테이블 '{table_query.table_name}'의 {len(results)}개 컬럼을 찾았습니다."))
                
                # 테이블 구조를 스트리밍
                structure_text = f"테이블 '{table_query.table_name}' 구조:\n"
                for column in results:
                    field = column.get('Field', '')
                    type_info = column.get('Type', '')
                    null_info = column.get('Null', '')
                    key_info = column.get('Key', '')
                    default_info = column.get('Default', '')
                    
                    structure_text += f"- {field}: {type_info}"
                    if null_info == 'NO':
                        structure_text += " (NOT NULL)"
                    if key_info:
                        structure_text += f" (Key: {key_info})"
                    if default_info:
                        structure_text += f" (Default: {default_info})"
                    structure_text += "\n"
                
                streaming_content = self._create_streaming_content(structure_text, chunk_size=600)
                progress_messages.append(streaming_content)
            else:
                progress_messages.append(self._create_error_message(f"테이블 구조 조회 실패: {message}"))
            
            return ToolResult(
                success=success,
                content="\n".join(progress_messages)
            )
                
        except Exception as e:
            logger.error(f"테이블 구조 조회 중 오류: {e}")
            return ToolResult(
                success=False,
                content=self._create_error_message(f"테이블 구조 조회 중 오류가 발생했습니다: {str(e)}")
            )
    
    @self.tool(
        name="get_table_info",
        description="지정된 테이블의 상세 정보를 조회합니다. 스트리밍 방식으로 결과를 전송합니다."
    )
    async def get_table_info(self, table_query: TableNameQuery) -> ToolResult:
        """테이블 상세 정보 조회 (스트리밍)"""
        try:
            progress_messages = []
            progress_messages.append(self._create_progress_message(f"테이블 '{table_query.table_name}'의 상세 정보를 조회하고 있습니다..."))
            
            logger.info(f"테이블 상세 정보 조회: {table_query.table_name}")
            
            # 테이블 구조 조회
            progress_messages.append(self._create_progress_message("테이블 구조를 조회하고 있습니다..."))
            success, message, results = await self.mysql_manager.describe_table(table_query.table_name)
            
            if not success:
                progress_messages.append(self._create_error_message(f"테이블 '{table_query.table_name}'을 찾을 수 없습니다."))
                return ToolResult(
                    success=False,
                    content="\n".join(progress_messages)
                )
            
            progress_messages.append(self._create_success_message(f"테이블 구조 조회 완료 ({len(results)}개 컬럼)"))
            
            # 레코드 수 조회
            progress_messages.append(self._create_progress_message("레코드 수를 조회하고 있습니다..."))
            count_success, count_message, count_result = await self.mysql_manager.execute_query(f"SELECT COUNT(*) as count FROM {table_query.table_name}")
            
            if count_success and count_result:
                record_count = count_result[0].get('count', 0)
                progress_messages.append(self._create_success_message(f"총 {record_count}개의 레코드가 있습니다."))
            else:
                progress_messages.append(self._create_error_message(f"레코드 수 조회 실패: {count_message}"))
            
            # 샘플 데이터 조회
            progress_messages.append(self._create_progress_message("샘플 데이터를 조회하고 있습니다..."))
            sample_success, sample_message, sample_result = await self.mysql_manager.execute_query(f"SELECT * FROM {table_query.table_name} LIMIT 5")
            
            if sample_success and sample_result:
                progress_messages.append(self._create_success_message(f"샘플 데이터 조회 완료 ({len(sample_result)}개 레코드)"))
                
                # 결과를 스트리밍
                sample_text = f"\n샘플 데이터 (최대 5개):\n{json.dumps(sample_result, indent=2, ensure_ascii=False)}"
                streaming_content = self._create_streaming_content(sample_text, chunk_size=700)
                progress_messages.append(streaming_content)
            else:
                progress_messages.append(self._create_error_message(f"샘플 데이터 조회 실패: {sample_message}"))
            
            return ToolResult(
                success=True,
                content="\n".join(progress_messages)
            )
                
        except Exception as e:
            logger.error(f"테이블 상세 정보 조회 중 오류: {e}")
            return ToolResult(
                success=False,
                content=self._create_error_message(f"테이블 상세 정보 조회 중 오류가 발생했습니다: {str(e)}")
            )
    
    @self.tool(
        name="test_connection",
        description="MySQL 데이터베이스 연결을 테스트합니다."
    )
    async def test_connection(self) -> ToolResult:
        """연결 테스트 (스트리밍)"""
        try:
            progress_messages = []
            progress_messages.append(self._create_progress_message("MySQL 데이터베이스 연결을 테스트하고 있습니다..."))
            
            logger.info("MySQL 연결 테스트")
            
            success, message = await self.mysql_manager.test_connection()
            
            if success:
                progress_messages.append(self._create_success_message(f"MySQL 연결 성공: {message}"))
            else:
                progress_messages.append(self._create_error_message(f"MySQL 연결 실패: {message}"))
            
            return ToolResult(
                success=success,
                content="\n".join(progress_messages)
            )
                
        except Exception as e:
            logger.error(f"연결 테스트 중 오류: {e}")
            return ToolResult(
                success=False,
                content=self._create_error_message(f"연결 테스트 중 오류가 발생했습니다: {str(e)}")
            )

async def main():
    """메인 함수"""
    try:
        # 설정 검증
        if not Config.validate_config():
            logger.error("설정 검증에 실패했습니다.")
            return
        
        # FastMCP 서버 생성 및 실행
        server = FastMCPMySQLServer()
        
        logger.info("FastMCP MySQL MCP 서버 (스트리밍)를 시작합니다...")
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