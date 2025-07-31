#!/usr/bin/env python3
"""
FastMCP/FyMCP MySQL MCP 서버 실행 스크립트
FastMCP와 FyMCP 프레임워크를 사용한 서버 실행을 위한 편의 스크립트입니다.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def check_python_version():
    """Python 버전 확인"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 이상이 필요합니다.")
        print(f"현재 버전: {sys.version}")
        return False
    return True

def check_dependencies():
    """의존성 패키지 확인"""
    required_packages = [
        'fastmcp',
        'fymcp',
        'mysql-connector-python',
        'openai',  # Groq API와 OpenAI API 모두 사용
        'pydantic'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 다음 패키지가 설치되지 않았습니다: {', '.join(missing_packages)}")
        print("다음 명령어로 설치하세요:")
        print("pip install -r requirements.txt")
        return False
    
    return True

def check_environment():
    """환경 변수 확인"""
    required_vars = ['MYSQL_HOST', 'MYSQL_DATABASE']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  다음 환경 변수가 설정되지 않았습니다: {', '.join(missing_vars)}")
        print("기본값을 사용합니다.")
    
    return True

def run_server(server_file: str, framework: str, debug: bool = False):
    """서버 실행"""
    try:
        # 서버 파일 경로 확인
        server_path = Path(server_file)
        if not server_path.exists():
            print(f"❌ 서버 파일을 찾을 수 없습니다: {server_file}")
            return False
        
        # 환경 변수 설정
        env = os.environ.copy()
        if debug:
            env['LOG_LEVEL'] = 'DEBUG'
        
        print(f"🚀 {framework.upper()} MySQL MCP 서버를 시작합니다...")
        print(f"서버 파일: {server_file}")
        print(f"프레임워크: {framework.upper()}")
        print(f"로그 레벨: {env.get('LOG_LEVEL', 'INFO')}")
        print()
        
        # 서버 실행
        process = subprocess.Popen(
            [sys.executable, str(server_path)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print("✅ 서버가 시작되었습니다.")
        print("종료하려면 Ctrl+C를 누르세요.")
        print()
        
        # 출력 모니터링
        while True:
            output = process.stdout.readline()
            if output:
                print(output.strip())
            
            # 프로세스 종료 확인
            if process.poll() is not None:
                break
        
        return True
        
    except KeyboardInterrupt:
        print(f"\n🛑 {framework.upper()} 서버를 종료합니다...")
        if process:
            process.terminate()
        return True
    except Exception as e:
        print(f"❌ {framework.upper()} 서버 실행 중 오류 발생: {e}")
        return False

def list_available_servers():
    """사용 가능한 서버 목록 표시"""
    servers = [
        ("fastmcp", "fastmcp_mysql_server.py", "FastMCP 프레임워크를 사용한 MySQL MCP 서버"),
        ("fymcp", "fymcp_mysql_server.py", "FyMCP 프레임워크를 사용한 MySQL MCP 서버"),
        ("original", "mysql_mcp_server_v2.py", "기존 MCP 서버 (참고용)")
    ]
    
    print("=== 사용 가능한 서버 목록 ===")
    for framework, filename, description in servers:
        file_path = Path(filename)
        status = "✅ 사용 가능" if file_path.exists() else "❌ 파일 없음"
        print(f"- {framework}: {filename}")
        print(f"  설명: {description}")
        print(f"  상태: {status}")
        print()

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='FastMCP/FyMCP MySQL MCP 서버 실행')
    parser.add_argument(
        'framework',
        choices=['fastmcp', 'fymcp', 'list'],
        help='실행할 프레임워크 (fastmcp, fymcp) 또는 서버 목록 조회 (list)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='디버그 모드로 실행'
    )
    parser.add_argument(
        '--check-only',
        action='store_true',
        help='환경 확인만 수행하고 서버는 실행하지 않음'
    )
    
    args = parser.parse_args()
    
    print("=== FastMCP/FyMCP MySQL MCP 서버 실행 스크립트 ===")
    print()
    
    # 서버 목록 조회
    if args.framework == 'list':
        list_available_servers()
        return
    
    # 환경 확인
    if not check_python_version():
        sys.exit(1)
    
    if not check_dependencies():
        sys.exit(1)
    
    if not check_environment():
        print("⚠️  환경 변수 설정을 확인하세요.")
    
    if args.check_only:
        print("✅ 환경 확인이 완료되었습니다.")
        return
    
    # 서버 파일 경로 설정
    server_file = f"{args.framework}_mysql_server.py"
    
    # 서버 실행
    success = run_server(server_file, args.framework, args.debug)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main() 