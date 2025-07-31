#!/usr/bin/env python3
"""
MySQL MCP 서버 테스트 클라이언트 (실제 패키지 버전)
MySQL MCP 서버를 테스트하기 위한 클라이언트 애플리케이션
"""

import asyncio
import json
import logging
import subprocess
import sys
from typing import Dict, Any, Optional
from mcp.client import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPTestClient:
    """MCP 테스트 클라이언트 클래스"""
    
    def __init__(self, server_path: str, server_type: str = "improved"):
        """초기화"""
        self.server_path = server_path
        self.server_type = server_type
        self.session: Optional[ClientSession] = None
        
    async def connect(self):
        """MCP 서버에 연결"""
        try:
            # 서버 파라미터 설정
            server_params = StdioServerParameters(
                command="python",
                args=[self.server_path],
                env={}
            )
            
            # 클라이언트 연결
            async with stdio_client(server_params) as (read, write):
                self.session = ClientSession(read, write, f"test-client-{self.server_type}")
                
                # 서버 초기화
                await self.session.initialize()
                logger.info(f"{self.server_type.upper()} MCP 서버에 성공적으로 연결되었습니다.")
                
        except Exception as e:
            logger.error(f"{self.server_type.upper()} MCP 서버 연결 실패: {e}")
            raise
    
    async def list_tools(self):
        """사용 가능한 도구 목록 조회"""
        try:
            tools = await self.session.list_tools()
            print(f"\n=== {self.server_type.upper()} 사용 가능한 도구 목록 ===")
            for tool in tools:
                print(f"- {tool.name}: {tool.description}")
                if tool.inputSchema:
                    print(f"  입력 스키마: {json.dumps(tool.inputSchema, indent=2, ensure_ascii=False)}")
                print()
            return tools
        except Exception as e:
            logger.error(f"도구 목록 조회 실패: {e}")
            return []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]):
        """도구 호출"""
        try:
            result = await self.session.call_tool(tool_name, arguments)
            print(f"\n=== {self.server_type.upper()} 도구 호출 결과: {tool_name} ===")
            for content in result.content:
                if hasattr(content, 'text'):
                    print(content.text)
            return result
        except Exception as e:
            logger.error(f"도구 호출 실패: {e}")
            return None
    
    async def run_comparison_test(self):
        """서버 비교 테스트"""
        print(f"=== {self.server_type.upper()} MySQL MCP 서버 테스트 ===")
        
        test_cases = [
            ("test_connection", {}, "연결 테스트"),
            ("list_tables", {}, "테이블 목록 조회"),
            ("query_mysql", {"natural_language_query": "사용자 테이블에서 모든 데이터를 조회해줘"}, "자연어 쿼리 테스트"),
            ("describe_table", {"table_name": "users"}, "테이블 구조 조회"),
            ("get_table_info", {"table_name": "users"}, "테이블 상세 정보 조회"),
        ]
        
        for tool_name, arguments, description in test_cases:
            print(f"\n--- {description} ---")
            try:
                result = await self.call_tool(tool_name, arguments)
                if result:
                    print("✅ 성공")
                else:
                    print("❌ 실패")
            except Exception as e:
                print(f"❌ 오류: {e}")
        
        print(f"\n=== {self.server_type.upper()} 테스트 완료 ===")
    
    async def run_interactive_test(self):
        """대화형 테스트 실행"""
        print(f"=== {self.server_type.upper()} MySQL MCP 서버 대화형 테스트 ===")
        print("종료하려면 'quit' 또는 'exit'를 입력하세요.")
        print()
        
        # 도구 목록 표시
        tools = await self.list_tools()
        tool_names = [tool.name for tool in tools]
        
        while True:
            try:
                # 사용자 입력 받기
                user_input = input(f"\n[{self.server_type.upper()}] 도구명과 인수를 입력하세요 (예: query_mysql '사용자 테이블 조회'): ").strip()
                
                if user_input.lower() in ['quit', 'exit', '종료']:
                    print("테스트를 종료합니다.")
                    break
                
                if not user_input:
                    continue
                
                # 입력 파싱
                parts = user_input.split(' ', 1)
                if len(parts) < 2:
                    print("형식: 도구명 '인수'")
                    continue
                
                tool_name = parts[0]
                arguments_str = parts[1]
                
                # 도구명 검증
                if tool_name not in tool_names:
                    print(f"알 수 없는 도구: {tool_name}")
                    print(f"사용 가능한 도구: {', '.join(tool_names)}")
                    continue
                
                # 인수 파싱
                try:
                    if tool_name == "query_mysql":
                        arguments = {"natural_language_query": arguments_str.strip("'\"")}
                    elif tool_name == "describe_table":
                        arguments = {"table_name": arguments_str.strip("'\"")}
                    elif tool_name == "get_table_info":
                        arguments = {"table_name": arguments_str.strip("'\"")}
                    else:
                        arguments = {}
                except Exception as e:
                    print(f"인수 파싱 오류: {e}")
                    continue
                
                # 도구 호출
                await self.call_tool(tool_name, arguments)
                
            except KeyboardInterrupt:
                print("\n테스트를 종료합니다.")
                break
            except Exception as e:
                logger.error(f"테스트 중 오류: {e}")
    
    async def close(self):
        """연결 종료"""
        if self.session:
            await self.session.close()
            logger.info(f"{self.server_type.upper()} MCP 클라이언트 연결이 종료되었습니다.")

async def run_server_comparison():
    """서버 비교 테스트"""
    print("=== MySQL MCP 서버 비교 테스트 ===")
    
    servers = [
        ("improved", "../server/mysql_mcp_server_v2.py"),
        ("fastmcp", "../server/fastmcp_mysql_server.py"),
        ("basic", "../server/mysql_mcp_server.py")
    ]
    
    for server_type, server_path in servers:
        print(f"\n{'='*50}")
        print(f"테스트 중: {server_type.upper()}")
        print(f"{'='*50}")
        
        client = MCPTestClient(server_path, server_type)
        
        try:
            # 서버 연결
            await client.connect()
            
            # 비교 테스트 실행
            await client.run_comparison_test()
            
        except Exception as e:
            print(f"❌ {server_type.upper()} 서버 테스트 실패: {e}")
        finally:
            await client.close()
    
    print("\n=== 서버 비교 테스트 완료 ===")

async def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("사용법:")
        print("  python test_fastmcp_client.py improved [--interactive]")
        print("  python test_fastmcp_client.py fastmcp [--interactive]")
        print("  python test_fastmcp_client.py basic [--interactive]")
        print("  python test_fastmcp_client.py compare")
        return
    
    server_type = sys.argv[1].lower()
    interactive_mode = "--interactive" in sys.argv
    
    if server_type == "compare":
        await run_server_comparison()
        return
    
    if server_type not in ["improved", "fastmcp", "basic"]:
        print("지원하는 서버 타입: improved, fastmcp, basic")
        return
    
    # 서버 경로 설정
    if server_type == "improved":
        server_path = "../server/mysql_mcp_server_v2.py"
    elif server_type == "fastmcp":
        server_path = "../server/fastmcp_mysql_server.py"
    else:
        server_path = f"../server/{server_type}_mysql_server.py"
    
    # 클라이언트 생성
    client = MCPTestClient(server_path, server_type)
    
    try:
        # 서버 연결
        await client.connect()
        
        # 테스트 모드 선택
        if interactive_mode:
            await client.run_interactive_test()
        else:
            await client.run_comparison_test()
            
    except Exception as e:
        logger.error(f"클라이언트 실행 중 오류: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main()) 