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
PASSWD = os.getenv('DB_PASSWD') # DB_PASS -> DB_PASSWD로 수정
DB_NAME = os.getenv('DB_NAME')


print(HOST, PORT, USER, PASSWD, DB_NAME)
# 3. DB 연결
try:
    db = pymysql.connect(
        user = USER,
        password = PASSWD, # passwd 보다는 password 매개변수 사용 권장
        host = HOST,
        port = PORT,
        db = DB_NAME,
        charset='utf8mb4'
    )
    print("연결 성공!")
except Exception as e:
    print(f"연결 실패: {e}")

def get_data(SQL:str):
    df = pd.read_sql(SQL, db)
    return df