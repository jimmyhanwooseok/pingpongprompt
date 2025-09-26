import sqlite3

def init_database():
    conn = sqlite3.connect('templates.db')
    c = conn.cursor()
    
    # 테이블 생성
    c.execute('''
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            fixed_content TEXT NOT NULL,
            variables TEXT NOT NULL,
            tags TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    
    # 테이블 확인
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = c.fetchall()
    print("생성된 테이블:")
    for table in tables:
        print(f"- {table[0]}")
    
    conn.close()
    print("데이터베이스 초기화 완료!")

if __name__ == "__main__":
    init_database()
