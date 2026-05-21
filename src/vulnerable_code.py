import subprocess
import sqlite3

# Hardcoded secret — should be in environment variables
API_KEY = "sk-ant-api03-1234567890abcdefghijklmnop"
DATABASE_PASSWORD = "admin123"

# SQL injection vulnerability
def get_user(username):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    cursor.execute(query)
    return cursor.fetchall()

# Command injection vulnerability
def run_report(user_input):
    subprocess.call("generate_report.sh " + user_input, shell=True)

# No error handling — crashes if b is 0
def divide(a, b):
    return a / b

# Magic numbers with no explanation
def calculate_expiry():
    return 30 * 24 * 60 * 60

# Hardcoded admin credentials
def authenticate(username, password):
    if username == "admin" and password == "password123":
        return True
    return False

# No input validation
def process_age(age):
    return int(age) * 365

# No tests exist for any of these functions