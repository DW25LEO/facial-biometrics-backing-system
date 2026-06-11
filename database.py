import sqlite3
import uuid
from datetime import datetime
import json
import os

class Database:
    def __init__(self):
        db_path = 'banking.db'
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.init_tables()
    
    def init_tables(self):
        try:
            # Users table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT UNIQUE NOT NULL,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    full_name TEXT NOT NULL,
                    account_number TEXT UNIQUE NOT NULL,
                    balance REAL DEFAULT 0.0,
                    role TEXT DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Biometric templates table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS biometric_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    encrypted_template TEXT NOT NULL,
                    template_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    UNIQUE(user_id)
                )
            ''')
            
            # Transactions table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id TEXT UNIQUE NOT NULL,
                    from_account TEXT NOT NULL,
                    to_account TEXT NOT NULL,
                    amount REAL NOT NULL,
                    description TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'completed'
                )
            ''')
            
            self.conn.commit()
            
            # Create admin user if not exists
            self.cursor.execute("SELECT * FROM users WHERE username = 'admin'")
            if not self.cursor.fetchone():
                admin_id = str(uuid.uuid4())
                admin_account = 'ADMIN001'
                self.cursor.execute('''
                    INSERT INTO users (user_id, username, password, email, full_name, account_number, balance, role)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (admin_id, 'admin', 'admin123', 'admin@securebank.com', 'System Administrator', admin_account, 0, 'admin'))
                self.conn.commit()
                print("✅ Admin user created")
            
            # Create sample user if not exists
            self.cursor.execute("SELECT * FROM users WHERE username = 'john_doe'")
            if not self.cursor.fetchone():
                user_id = str(uuid.uuid4())
                account_number = '1000000001'
                self.cursor.execute('''
                    INSERT INTO users (user_id, username, password, email, full_name, account_number, balance, role)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, 'john_doe', 'pass123', 'john@example.com', 'John Doe', account_number, 5000.00, 'user'))
                self.conn.commit()
                print("✅ Sample user created")
                
        except Exception as e:
            print(f"Database initialization error: {str(e)}")
            raise
    
    def register_user(self, username, password, email, full_name, encrypted_biometric):
        user_id = str(uuid.uuid4())
        account_number = str(int(datetime.now().timestamp()))[-10:]
        
        try:
            self.cursor.execute('''
                INSERT INTO users (user_id, username, password, email, full_name, account_number, balance, role)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, password, email, full_name, account_number, 100.00, 'user'))
            
            self.cursor.execute('''
                INSERT INTO biometric_templates (user_id, encrypted_template)
                VALUES (?, ?)
            ''', (user_id, encrypted_biometric))
            
            self.conn.commit()
            return {'success': True, 'user_id': user_id, 'account_number': account_number}
        except sqlite3.IntegrityError as e:
            return {'success': False, 'error': f'User already exists: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_user_by_username(self, username):
        try:
            self.cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = self.cursor.fetchone()
            if user:
                return dict(user)
            return None
        except Exception as e:
            print(f"Error getting user: {str(e)}")
            return None
    
    def get_biometric_template(self, user_id):
        try:
            self.cursor.execute('SELECT encrypted_template FROM biometric_templates WHERE user_id = ?', (user_id,))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            print(f"Error getting biometric: {str(e)}")
            return None
    
    def update_balance(self, account_number, new_balance):
        try:
            self.cursor.execute('UPDATE users SET balance = ? WHERE account_number = ?', (new_balance, account_number))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating balance: {str(e)}")
            return False
    
    def transfer_money(self, from_account, to_account, amount, description):
        try:
            self.cursor.execute('BEGIN TRANSACTION')
            
            # Check sender balance
            self.cursor.execute('SELECT balance FROM users WHERE account_number = ?', (from_account,))
            result = self.cursor.fetchone()
            if not result:
                self.cursor.execute('ROLLBACK')
                return {'success': False, 'error': 'Sender account not found'}
            
            sender_balance = result[0]
            if sender_balance < amount:
                self.cursor.execute('ROLLBACK')
                return {'success': False, 'error': f'Insufficient funds. Available: ${sender_balance:.2f}'}
            
            # Check receiver exists
            self.cursor.execute('SELECT account_number FROM users WHERE account_number = ?', (to_account,))
            if not self.cursor.fetchone():
                self.cursor.execute('ROLLBACK')
                return {'success': False, 'error': 'Receiver account not found'}
            
            # Deduct from sender
            self.cursor.execute('UPDATE users SET balance = balance - ? WHERE account_number = ?', (amount, from_account))
            
            # Add to receiver
            self.cursor.execute('UPDATE users SET balance = balance + ? WHERE account_number = ?', (amount, to_account))
            
            # Record transaction
            transaction_id = str(uuid.uuid4())
            self.cursor.execute('''
                INSERT INTO transactions (transaction_id, from_account, to_account, amount, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (transaction_id, from_account, to_account, amount, description))
            
            self.conn.commit()
            return {'success': True, 'transaction_id': transaction_id}
            
        except Exception as e:
            self.cursor.execute('ROLLBACK')
            return {'success': False, 'error': str(e)}
    
    def get_transactions(self, account_number, limit=50):
        try:
            self.cursor.execute('''
                SELECT transaction_id, from_account, to_account, amount, description, timestamp, status
                FROM transactions
                WHERE from_account = ? OR to_account = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (account_number, account_number, limit))
            
            transactions = []
            for row in self.cursor.fetchall():
                transactions.append({
                    'transaction_id': row[0],
                    'from_account': row[1],
                    'to_account': row[2],
                    'amount': row[3],
                    'description': row[4] or 'Transfer',
                    'timestamp': row[5],
                    'status': row[6],
                    'type': 'sent' if row[1] == account_number else 'received'
                })
            return transactions
        except Exception as e:
            print(f"Error getting transactions: {str(e)}")
            return []
    
    def get_all_users(self):
        try:
            self.cursor.execute('''
                SELECT u.user_id, u.username, u.password, u.email, u.full_name, 
                       u.account_number, u.balance, u.role, u.created_at,
                       b.encrypted_template
                FROM users u
                LEFT JOIN biometric_templates b ON u.user_id = b.user_id
                ORDER BY u.created_at DESC
            ''')
            
            users = []
            for row in self.cursor.fetchall():
                users.append({
                    'user_id': row[0],
                    'username': row[1],
                    'password': row[2],
                    'email': row[3],
                    'full_name': row[4],
                    'account_number': row[5],
                    'balance': row[6],
                    'role': row[7],
                    'created_at': row[8],
                    'encrypted_biometric': row[9] if row[9] else 'No biometric enrolled'
                })
            return users
        except Exception as e:
            print(f"Error getting all users: {str(e)}")
            return []
    
    def close(self):
        try:
            self.conn.close()
        except:
            pass