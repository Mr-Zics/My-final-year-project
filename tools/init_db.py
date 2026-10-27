"""
Utility to test database connection and ensure library_db exists with utf8mb4.
"""
import sys
from decouple import config

def check_or_create_db():
    db_user = config('DB_USER', default='root')
    db_password = config('DB_PASSWORD')
    db_host = config('DB_HOST', default='127.0.0.1')
    db_port = config('DB_PORT', default=3306, cast=int)
    db_name = config('DB_NAME', default='library_db')

    # Try native mysqlclient first
    try:
        import MySQLdb
        driver_name = "mysqlclient"
        conn = MySQLdb.connect(host=db_host, user=db_user, passwd=db_password, port=db_port)
    except Exception as e_driver:
        # Fallback to PyMySQL if needed
        try:
            import pymysql
            driver_name = "pymysql"
            conn = pymysql.connect(host=db_host, user=db_user, password=db_password, port=db_port)
        except Exception as e_final:
            print(f"FAILED_TO_CONNECT: {type(e_final).__name__}: {e_final}")
            sys.exit(1)

    try:
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        cursor.execute(f"SHOW DATABASES LIKE '{db_name}';")
        res = cursor.fetchone()
        cursor.close()
        conn.close()
        print(f"SUCCESS: Driver={driver_name}, Database `{res[0]}` verified and ready.")
    except Exception as err:
        print(f"FAILED_QUERY: {type(err).__name__}: {err}")
        sys.exit(1)

if __name__ == "__main__":
    check_or_create_db()
