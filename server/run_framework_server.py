#!/usr/bin/env python3
"""
MySQL MCP 서버 실행 스크립트 (실제 패키지 버전)
MySQL MCP 서버 실행을 위한 편의 스크립트입니다.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# .env 파일 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ .env 파일을 로드했습니다.")
except ImportError:
    print("⚠️ python-dotenv가 설치되지 않았습니다. .env 파일을 수동으로 로드하세요.")
except Exception as e:
    print(f"⚠️ .env 파일 로드 중 오류: {e}")

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
        'mcp',
        'fastmcp',  # FastMCP 프레임워크
        'mysql.connector',  # mysql-connector-python 패키지
        'openai',  # Groq API와 OpenAI API 모두 사용
        'pydantic'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            # mysql.connector는 특별 처리
            if package == 'mysql.connector':
                import mysql.connector
            else:
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

def run_server(server_file: str, server_type: str, debug: bool = False):
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
        
        print(f"🚀 {server_type.upper()} MySQL MCP 서버를 시작합니다...")
        print(f"서버 파일: {server_file}")
        print(f"서버 타입: {server_type.upper()}")
        print(f"로그 레벨: {env.get('LOG_LEVEL', 'INFO')}")
        print()
        
        # 서버 실행 (포그라운드에서 실행)
        process = subprocess.Popen(
            [sys.executable, str(server_path)],
            env=env
        )
        
        print("✅ 서버가 시작되었습니다.")
        print("종료하려면 Ctrl+C를 누르세요.")
        print()
        
        # 프로세스가 종료될 때까지 대기
        process.wait()
        
        return True
        
    except KeyboardInterrupt:
        print(f"\n🛑 {server_type.upper()} 서버를 종료합니다...")
        if process:
            process.terminate()
        return True
    except Exception as e:
        print(f"❌ {server_type.upper()} 서버 실행 중 오류 발생: {e}")
        return False

def list_available_servers():
    """사용 가능한 서버 목록 표시"""
    servers = [
        ("improved", "mysql_mcp_server_v2.py", "개선된 MCP 서버 (Groq API 지원, 권장)"),
        ("fastmcp", "fastmcp_mysql_server.py", "FastMCP 프레임워크 서버 (Groq API 지원)"),
        ("basic", "mysql_mcp_server.py", "기본 MCP 서버"),
    ]
    
    print("=== 사용 가능한 서버 목록 ===")
    for server_type, filename, description in servers:
        file_path = Path(filename)
        status = "✅ 사용 가능" if file_path.exists() else "❌ 파일 없음"
        print(f"- {server_type}: {filename}")
        print(f"  설명: {description}")
        print(f"  상태: {status}")
        print()

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='MySQL MCP 서버 실행')
    parser.add_argument(
        'server_type',
        choices=['improved', 'fastmcp', 'basic', 'list'],
        help='실행할 서버 타입 (improved, fastmcp, basic) 또는 서버 목록 조회 (list)'
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
    
    print("=== MySQL MCP 서버 실행 스크립트 ===")
    print()
    
    # 서버 목록 조회
    if args.server_type == 'list':
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
    if args.server_type == 'improved':
        server_file = "mysql_mcp_server_v2.py"
    elif args.server_type == 'fastmcp':
        server_file = "fastmcp_mysql_server.py"
    else:
        server_file = f"{args.server_type}_mysql_server.py"
    
    # 서버 실행
    success = run_server(server_file, args.server_type, args.debug)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main() 