import os
import sys
import time

import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")


def main():
    attempts = 0
    while attempts < 30:
        try:
            conn = psycopg2.connect(DATABASE_URL)
            conn.close()
            print("[wait_for_db] Postgres disponible.")
            return 0
        except psycopg2.OperationalError:
            attempts += 1
            print(f"[wait_for_db] Esperando a Postgres... intento {attempts}")
            time.sleep(2)
    print("[wait_for_db] Postgres nunca quedo disponible.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
