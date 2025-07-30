"""
MySQL 데이터베이스 관리 모듈
MySQL 연결, 쿼리 실행, 결과 처리를 담당합니다.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
import mysql.connector
from mysql.connector import Error, pooling
from config import Config

logger = logging.getLogger(__name__)

class MySQLManager:
    """MySQL 데이터베이스 관리 클래스"""
    
    def __init__(self):
        """초기화"""
        self.connection_pool = None
        self.connection = None
        self._init_connection_pool()
    
    def _init_connection_pool(self):
        """연결 풀 초기화"""
        try:
            mysql_config = Config.get_mysql_config()
            
            # 연결 풀 설정
            pool_config = {
                'pool_name': 'mysql_mcp_pool',
                'pool_size': 5,
                'pool_reset_session': True,
                **mysql_config
            }
            
            self.connection_pool = mysql.connector.pooling.MySQLConnectionPool(**pool_config)
            logger.info("MySQL 연결 풀이 초기화되었습니다.")
            
        except Error as e:
            logger.error(f"MySQL 연결 풀 초기화 실패: {e}")
            self.connection_pool = None
    
    def get_connection(self):
        """데이터베이스 연결 가져오기"""
        try:
            if self.connection_pool:
                return self.connection_pool.get_connection()
            else:
                # 연결 풀이 없으면 직접 연결
                mysql_config = Config.get_mysql_config()
                return mysql.connector.connect(**mysql_config)
        except Error as e:
            logger.error(f"MySQL 연결 실패: {e}")
            raise
    
    async def execute_query(self, sql_query: str) -> Tuple[bool, str, Optional[List[Dict]]]:
        """
        SQL 쿼리 실행
        
        Returns:
            Tuple[bool, str, Optional[List[Dict]]]: (성공여부, 메시지, 결과데이터)
        """
        connection = None
        cursor = None
        
        try:
            # 연결 획득
            connection = self.get_connection()
            cursor = connection.cursor(dictionary=True)
            
            # 쿼리 실행
            cursor.execute(sql_query)
            
            # SELECT 쿼리인 경우 결과 반환
            if sql_query.strip().upper().startswith('SELECT'):
                results = cursor.fetchall()
                return True, "쿼리가 성공적으로 실행되었습니다.", results
            else:
                # INSERT, UPDATE, DELETE 등의 경우
                connection.commit()
                affected_rows = cursor.rowcount
                return True, f"쿼리가 성공적으로 실행되었습니다. 영향받은 행: {affected_rows}", None
                
        except Error as e:
            error_msg = f"MySQL 쿼리 실행 오류: {e}"
            logger.error(error_msg)
            return False, error_msg, None
            
        finally:
            # 리소스 정리
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    async def get_tables(self) -> List[str]:
        """데이터베이스의 모든 테이블 목록 조회"""
        success, message, results = await self.execute_query("SHOW TABLES")
        
        if success and results:
            # 결과에서 테이블명 추출
            table_names = []
            for row in results:
                # SHOW TABLES의 결과는 첫 번째 컬럼에 테이블명이 있음
                table_name = list(row.values())[0]
                table_names.append(table_name)
            return table_names
        else:
            logger.error(f"테이블 목록 조회 실패: {message}")
            return []
    
    async def describe_table(self, table_name: str) -> List[Dict]:
        """테이블 구조 조회"""
        success, message, results = await self.execute_query(f"DESCRIBE {table_name}")
        
        if success and results:
            return results
        else:
            logger.error(f"테이블 구조 조회 실패: {message}")
            return []
    
    async def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """테이블 상세 정보 조회"""
        try:
            # 테이블 구조 조회
            columns = await self.describe_table(table_name)
            
            # 레코드 수 조회
            success, message, results = await self.execute_query(f"SELECT COUNT(*) as count FROM {table_name}")
            record_count = results[0]['count'] if success and results else 0
            
            # 샘플 데이터 조회 (최대 5개)
            success, message, sample_data = await self.execute_query(f"SELECT * FROM {table_name} LIMIT 5")
            
            return {
                'table_name': table_name,
                'columns': columns,
                'record_count': record_count,
                'sample_data': sample_data if success else []
            }
            
        except Exception as e:
            logger.error(f"테이블 정보 조회 실패: {e}")
            return {
                'table_name': table_name,
                'columns': [],
                'record_count': 0,
                'sample_data': []
            }
    
    def format_query_results(self, results: List[Dict]) -> str:
        """쿼리 결과를 보기 좋게 포맷팅"""
        if not results:
            return "조회 결과가 없습니다."
        
        # 컬럼명 추출
        columns = list(results[0].keys())
        
        # 결과 문자열 생성
        result_str = "조회 결과:\n"
        result_str += f"총 {len(results)}개 레코드\n\n"
        
        for i, row in enumerate(results, 1):
            result_str += f"--- 레코드 {i} ---\n"
            for column in columns:
                value = row.get(column, 'NULL')
                result_str += f"{column}: {value}\n"
            result_str += "\n"
        
        return result_str
    
    def validate_sql_query(self, sql_query: str) -> Tuple[bool, str]:
        """SQL 쿼리 유효성 검사"""
        if not sql_query or not sql_query.strip():
            return False, "쿼리가 비어있습니다."
        
        sql_upper = sql_query.strip().upper()
        
        # 위험한 키워드 검사
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'CREATE', 'ALTER', 'TRUNCATE']
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False, f"안전하지 않은 키워드 '{keyword}'가 포함되어 있습니다."
        
        # SELECT 쿼리만 허용
        if not sql_upper.startswith('SELECT'):
            return False, "SELECT 쿼리만 허용됩니다."
        
        return True, "유효한 쿼리입니다."
    
    async def test_connection(self) -> bool:
        """데이터베이스 연결 테스트"""
        try:
            success, message, _ = await self.execute_query("SELECT 1")
            if success:
                logger.info("MySQL 연결 테스트 성공")
                return True
            else:
                logger.error(f"MySQL 연결 테스트 실패: {message}")
                return False
        except Exception as e:
            logger.error(f"MySQL 연결 테스트 중 오류: {e}")
            return False
    
    def close(self):
        """연결 풀 종료"""
        if self.connection_pool:
            self.connection_pool.close()
            logger.info("MySQL 연결 풀이 종료되었습니다.") 