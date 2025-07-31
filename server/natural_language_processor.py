"""
자연어 처리 모듈
자연어 쿼리를 MySQL SQL로 변환하는 기능을 제공합니다.
Groq API와 llama3-8b-8192 모델을 사용합니다.
"""

import re
import logging
from typing import Optional, Dict, List, Any
import openai
from config import Config

logger = logging.getLogger(__name__)

class NaturalLanguageProcessor:
    """자연어 처리 클래스"""
    
    def __init__(self):
        """초기화"""
        self.groq_client = None
        self.openai_client = None
        self._init_groq_client()
        self._init_openai_client()
        
        # 한국어 키워드 매핑
        self.korean_keywords = {
            '조회': 'SELECT',
            '검색': 'SELECT',
            '찾기': 'SELECT',
            '모든': '*',
            '전체': '*',
            '테이블': 'FROM',
            '에서': 'FROM',
            '조건': 'WHERE',
            '정렬': 'ORDER BY',
            '내림차순': 'DESC',
            '오름차순': 'ASC',
            '개수': 'COUNT',
            '평균': 'AVG',
            '합계': 'SUM',
            '최대': 'MAX',
            '최소': 'MIN'
        }
        
        # SQL 키워드 패턴
        self.sql_patterns = {
            'select_all': r'모든\s+(\w+)\s+조회',
            'select_where': r'(\w+)\s+테이블에서\s+(\w+)\s+조건으로\s+조회',
            'count': r'(\w+)\s+테이블의\s+개수',
            'order_by': r'(\w+)\s+테이블을\s+(\w+)\s+정렬'
        }
    
    def _init_groq_client(self):
        """Groq 클라이언트 초기화"""
        groq_config = Config.get_groq_config()
        if groq_config['api_key']:
            try:
                self.groq_client = openai.AsyncOpenAI(
                    api_key=groq_config['api_key'],
                    base_url=groq_config['api_base']
                )
                logger.info(f"Groq 클라이언트가 초기화되었습니다. 모델: {groq_config['model']}")
            except Exception as e:
                logger.warning(f"Groq 클라이언트 초기화 실패: {e}")
                self.groq_client = None
    
    def _init_openai_client(self):
        """OpenAI 클라이언트 초기화 (기존 호환성)"""
        openai_config = Config.get_openai_config()
        if openai_config['api_key']:
            try:
                self.openai_client = openai.AsyncOpenAI(api_key=openai_config['api_key'])
                logger.info("OpenAI 클라이언트가 초기화되었습니다.")
            except Exception as e:
                logger.warning(f"OpenAI 클라이언트 초기화 실패: {e}")
                self.openai_client = None
    
    async def convert_to_sql(self, natural_query: str) -> Optional[str]:
        """자연어를 SQL로 변환"""
        try:
            # Groq API를 사용한 고급 변환 시도 (우선순위)
            if self.groq_client:
                sql_query = await self._convert_with_groq(natural_query)
                if sql_query:
                    return sql_query
            
            # OpenAI API를 사용한 고급 변환 시도 (대체)
            if self.openai_client:
                sql_query = await self._convert_with_openai(natural_query)
                if sql_query:
                    return sql_query
            
            # 기본 변환 로직 사용
            return self._convert_with_patterns(natural_query)
            
        except Exception as e:
            logger.error(f"자연어 변환 중 오류: {e}")
            return None
    
    async def _convert_with_groq(self, natural_query: str) -> Optional[str]:
        """Groq API를 사용한 자연어 변환"""
        try:
            groq_config = Config.get_groq_config()
            
            system_prompt = """
당신은 한국어 자연어를 MySQL SQL 쿼리로 변환하는 전문가입니다.
다음 규칙을 따라주세요:
1. SELECT 쿼리만 생성하세요
2. 안전한 쿼리만 생성하세요 (LIMIT 사용 권장)
3. 한국어 테이블명과 컬럼명을 그대로 사용하세요
4. SQL 키워드는 대문자로 작성하세요
5. 쿼리만 반환하고 설명은 하지 마세요
6. Llama 모델의 특성을 고려하여 정확한 SQL을 생성하세요
"""
            
            response = await self.groq_client.chat.completions.create(
                model=groq_config['model'],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"다음 한국어를 MySQL SQL로 변환해주세요: {natural_query}"}
                ],
                max_tokens=200,
                temperature=0.1
            )
            
            sql_query = response.choices[0].message.content.strip()
            
            # SQL 키워드 검증
            if self._validate_sql_query(sql_query):
                logger.info(f"Groq API 변환 성공: {sql_query}")
                return sql_query
            else:
                logger.warning(f"Groq가 생성한 쿼리가 유효하지 않습니다: {sql_query}")
                return None
                
        except Exception as e:
            logger.warning(f"Groq 변환 실패: {e}")
            return None
    
    async def _convert_with_openai(self, natural_query: str) -> Optional[str]:
        """OpenAI API를 사용한 자연어 변환 (기존 호환성)"""
        try:
            system_prompt = """
당신은 한국어 자연어를 MySQL SQL 쿼리로 변환하는 전문가입니다.
다음 규칙을 따라주세요:
1. SELECT 쿼리만 생성하세요
2. 안전한 쿼리만 생성하세요 (LIMIT 사용 권장)
3. 한국어 테이블명과 컬럼명을 그대로 사용하세요
4. SQL 키워드는 대문자로 작성하세요
5. 쿼리만 반환하고 설명은 하지 마세요
"""
            
            response = await self.openai_client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"다음 한국어를 MySQL SQL로 변환해주세요: {natural_query}"}
                ],
                max_tokens=200,
                temperature=0.1
            )
            
            sql_query = response.choices[0].message.content.strip()
            
            # SQL 키워드 검증
            if self._validate_sql_query(sql_query):
                logger.info(f"OpenAI API 변환 성공: {sql_query}")
                return sql_query
            else:
                logger.warning(f"OpenAI가 생성한 쿼리가 유효하지 않습니다: {sql_query}")
                return None
                
        except Exception as e:
            logger.warning(f"OpenAI 변환 실패: {e}")
            return None
    
    def _convert_with_patterns(self, natural_query: str) -> str:
        """패턴 매칭을 사용한 기본 변환"""
        query_lower = natural_query.lower()
        
        # 패턴 매칭
        for pattern_name, pattern in self.sql_patterns.items():
            match = re.search(pattern, query_lower)
            if match:
                if pattern_name == 'select_all':
                    table_name = match.group(1)
                    return f"SELECT * FROM {table_name} LIMIT 10"
                elif pattern_name == 'select_where':
                    table_name = match.group(1)
                    condition = match.group(2)
                    return f"SELECT * FROM {table_name} WHERE {condition} LIMIT 10"
                elif pattern_name == 'count':
                    table_name = match.group(1)
                    return f"SELECT COUNT(*) FROM {table_name}"
                elif pattern_name == 'order_by':
                    table_name = match.group(1)
                    order_field = match.group(2)
                    return f"SELECT * FROM {table_name} ORDER BY {order_field} LIMIT 10"
        
        # 기본 키워드 매칭
        if "모든" in query_lower and "조회" in query_lower:
            # 테이블명 추출
            words = natural_query.split()
            for i, word in enumerate(words):
                if "테이블" in word and i > 0:
                    table_name = words[i-1]
                    return f"SELECT * FROM {table_name} LIMIT 10"
        
        # 기본 쿼리 반환
        return "SELECT * FROM users LIMIT 10"
    
    def _validate_sql_query(self, sql_query: str) -> bool:
        """SQL 쿼리 유효성 검사"""
        if not sql_query:
            return False
        
        # 기본 SQL 키워드 검사
        sql_upper = sql_query.upper()
        if not sql_upper.startswith('SELECT'):
            return False
        
        # 위험한 키워드 검사
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'CREATE', 'ALTER']
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False
        
        return True
    
    def extract_table_name(self, natural_query: str) -> Optional[str]:
        """자연어에서 테이블명 추출"""
        # "테이블" 키워드 주변 단어 추출
        words = natural_query.split()
        for i, word in enumerate(words):
            if "테이블" in word:
                if i > 0:
                    return words[i-1]
                elif i < len(words) - 1:
                    return words[i+1]
        
        return None
    
    def extract_conditions(self, natural_query: str) -> List[str]:
        """자연어에서 조건 추출"""
        conditions = []
        
        # 조건 관련 키워드 패턴
        condition_patterns = [
            r'(\w+)\s+이\s+(\w+)',
            r'(\w+)\s+가\s+(\w+)',
            r'(\w+)\s+조건',
            r'(\w+)\s+필터'
        ]
        
        for pattern in condition_patterns:
            matches = re.findall(pattern, natural_query)
            conditions.extend(matches)
        
        return conditions 