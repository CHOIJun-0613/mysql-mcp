"""
MySQL MCP 서버 설정 파일
데이터베이스 연결 정보와 API 키 설정을 관리합니다.
"""

import os
from typing import Dict, Any

class Config:
    """설정 관리 클래스"""
    
    # MySQL 데이터베이스 설정
    MYSQL_CONFIG = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', 3306)),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', ''),
        'database': os.getenv('MYSQL_DATABASE', 'test_db'),
        'charset': 'utf8mb4',
        'autocommit': True
    }
    
    # OpenAI API 설정
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    
    # MCP 서버 설정
    SERVER_NAME = "mysql-mcp-server"
    SERVER_VERSION = "1.0.0"
    
    # 로깅 설정
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def get_mysql_config(cls) -> Dict[str, Any]:
        """MySQL 설정 반환"""
        return cls.MYSQL_CONFIG.copy()
    
    @classmethod
    def get_openai_config(cls) -> Dict[str, str]:
        """OpenAI 설정 반환"""
        return {
            'api_key': cls.OPENAI_API_KEY,
            'model': cls.OPENAI_MODEL
        }
    
    @classmethod
    def validate_config(cls) -> bool:
        """설정 유효성 검사"""
        # MySQL 설정 검사
        if not cls.MYSQL_CONFIG['host']:
            print("경고: MySQL 호스트가 설정되지 않았습니다.")
            return False
        
        if not cls.MYSQL_CONFIG['database']:
            print("경고: MySQL 데이터베이스 이름이 설정되지 않았습니다.")
            return False
        
        # OpenAI API 키 검사 (선택사항)
        if not cls.OPENAI_API_KEY:
            print("정보: OpenAI API 키가 설정되지 않았습니다. 기본 자연어 변환을 사용합니다.")
        
        return True 