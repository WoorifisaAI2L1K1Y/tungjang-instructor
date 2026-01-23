import pymysql
import pandas as pd
import os
from dotenv import load_dotenv

# 1. 환경 변수 로드
load_dotenv()

pd.options.display.float_format = '{:.2f}'.format

# 2. 변수명 매칭 확인 (.env 파일의 키값과 동일하게)
HOST = os.getenv('DB_HOST')
PORT = int(os.getenv('DB_PORT', 3306))
USER = os.getenv('DB_USER')
PASSWD = os.getenv('DB_PASSWD')
DB_NAME = os.getenv('DB_NAME')

print(HOST, PORT, USER, PASSWD, DB_NAME)

# 3. DB 연결
try:
    db = pymysql.connect(
        user=USER,
        password=PASSWD,
        host=HOST,
        port=PORT,
        db=DB_NAME,
        charset='utf8mb4'
    )
    print("연결 성공!")
except Exception as e:
    print(f"연결 실패: {e}")
    db = None

def get_connection():
    """
    새로운 DB 연결을 반환하는 함수
    각 쿼리마다 새 연결을 사용하여 연결 끊김 문제 방지
    """
    try:
        conn = pymysql.connect(
            user=USER,
            password=PASSWD,
            host=HOST,
            port=PORT,
            db=DB_NAME,
            charset='utf8mb4'
        )
        return conn
    except Exception as e:
        raise Exception(f"DB 연결 실패: {e}")

def get_data(SQL: str):
    """
    SELECT 쿼리를 실행하고 DataFrame으로 반환
    
    Args:
        SQL (str): 실행할 SELECT 쿼리
    
    Returns:
        pd.DataFrame: 조회 결과
    """
    conn = None
    try:
        conn = get_connection()
        df = pd.read_sql(SQL, conn)
        return df
    except Exception as e:
        raise Exception(f"데이터 조회 오류: {e}")
    finally:
        if conn:
            conn.close()

def execute_query(query, params=None):
    """
    INSERT, UPDATE, DELETE 등의 쿼리를 실행하는 함수
    
    Args:
        query (str): 실행할 SQL 쿼리
        params (tuple, optional): 쿼리 파라미터
    
    Returns:
        int: 영향받은 행의 수
    
    Raises:
        Exception: 쿼리 실행 중 오류 발생 시
    
    Example:
        execute_query(
            "INSERT INTO expenses (budget, date, amount) VALUES (%s, %s, %s)",
            ("2024년 예산", "2024-01-15", 50000)
        )
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if params:
            affected_rows = cursor.execute(query, params)
        else:
            affected_rows = cursor.execute(query)
        
        conn.commit()
        return affected_rows
        
    except Exception as e:
        if conn:
            conn.rollback()
        raise Exception(f"쿼리 실행 오류: {e}")
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def execute_many(query, data_list):
    """
    여러 개의 데이터를 한 번에 삽입하는 함수
    
    Args:
        query (str): 실행할 SQL 쿼리
        data_list (list): 삽입할 데이터 리스트 [(val1, val2, ...), ...]
    
    Returns:
        int: 영향받은 행의 수
    
    Raises:
        Exception: 쿼리 실행 중 오류 발생 시
    
    Example:
        data = [
            ("2024년 예산", "2024-01-15", 50000),
            ("2024년 예산", "2024-01-16", 30000)
        ]
        execute_many(
            "INSERT INTO expenses (budget, date, amount) VALUES (%s, %s, %s)",
            data
        )
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        affected_rows = cursor.executemany(query, data_list)
        conn.commit()
        return affected_rows
        
    except Exception as e:
        if conn:
            conn.rollback()
        raise Exception(f"배치 쿼리 실행 오류: {e}")
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def init_database():
    """
    데이터베이스 테이블 초기화 함수
    sample 테이블이 없으면 생성
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # sample 테이블 생성
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sample (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                date DATE,
                time TIME,
                category VARCHAR(50),
                reason VARCHAR(50),
                cost BIGINT,
                memo VARCHAR(50),
                INDEX idx_date (date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        conn.commit()
        print("✅ 데이터베이스 초기화 완료")
        
    except Exception as e:
        print(f"❌ 데이터베이스 초기화 오류: {e}")
        if conn:
            conn.rollback()
            
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 모듈 임포트 시 테이블 자동 생성
# init_database()  # 이미 테이블이 존재하므로 주석 처리