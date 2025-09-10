import sqlite3

class Data:
    def __init__(self, db_path='user_data.db'):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                chat_id TEXT PRIMARY KEY,
                tickers TEXT
            )
        ''')

    def startup(self):
        self.cursor.execute('SELECT chat_id FROM users')
        rows = self.cursor.fetchall()
        return [row[0] for row in rows] 

    def update_user_data(self, chat_id, new_tickers=[]):
        self.cursor.execute('SELECT tickers FROM users WHERE chat_id = ?', (chat_id,))
        result = self.cursor.fetchone()
        
        if result:
            existing_tickers = result[0].split(',') if result[0] else []
            for ticker in new_tickers:
                if ticker not in existing_tickers:
                    existing_tickers.append(ticker)
            updated_tickers = ','.join(existing_tickers)
            self.cursor.execute('UPDATE users SET tickers = ? WHERE chat_id = ?', (updated_tickers, chat_id))
        else:
            updated_tickers = ','.join(set(new_tickers))
            self.cursor.execute('INSERT INTO users (chat_id, tickers) VALUES (?, ?)', (chat_id, updated_tickers))
        
        self.conn.commit()
    
    def remove_from_user_data(self, chat_id, ticker):
        self.cursor.execute('SELECT tickers FROM users WHERE chat_id = ?', (chat_id,))
        result = self.cursor.fetchone()
        
        if result:
            tickers = set(result[0].split(','))
            if ticker in tickers:
                tickers.remove(ticker)
                updated = ','.join(tickers)
                self.cursor.execute('UPDATE users SET tickers = ? WHERE chat_id = ?', (updated, chat_id))
                self.conn.commit()
                return True  
        return False

    def get_user_tickers(self, chat_id):
        self.cursor.execute('SELECT tickers FROM users WHERE chat_id = ?', (chat_id,))
        result = self.cursor.fetchone()
        existing_tickers = set(result[0].split(',') if result[0] else [])
        return list(existing_tickers)

    def close(self):
        self.conn.close()