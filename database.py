# importing the required libraries
import os, sqlite3, hashlib, hmac, secrets
DB_PATH=os.getenv("KRISHIMITRA_DB","krishimitra.db")

# connect to the database
def connect():
    con=sqlite3.connect(DB_PATH); con.row_factory=sqlite3.Row; return con

# initialize the database
def init_db():
    with connect() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS farmers(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,location TEXT NOT NULL,language TEXT NOT NULL,password_hash TEXT NOT NULL,salt TEXT NOT NULL,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS chats(id INTEGER PRIMARY KEY AUTOINCREMENT,farmer_id INTEGER NOT NULL,question TEXT NOT NULL,answer TEXT NOT NULL,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(farmer_id) REFERENCES farmers(id))""")

def _hash(password,salt): return hashlib.pbkdf2_hmac("sha256",password.encode(),salt.encode(),200000).hex()

# creating the function to create user
def create_user(name,email,location,language,password):
    salt=secrets.token_hex(16); hashed=_hash(password,salt)
    try:
        with connect() as c:
            c.execute("INSERT INTO farmers(name,email,location,language,password_hash,salt) VALUES(?,?,?,?,?,?)",(name.strip(),email.strip().lower(),location.strip(),language,hashed,salt))
        return True,"Account created"
    except sqlite3.IntegrityError: return False,"An account with this email already exists."

# create the function to authenticate the user
def authenticate_user(email,password):
    with connect() as c: row=c.execute("SELECT * FROM farmers WHERE email=?",(email.strip().lower(),)).fetchone()
    if not row or not hmac.compare_digest(row["password_hash"],_hash(password,row["salt"])): return None
    return {"id":row["id"],"name":row["name"],"email":row["email"],"location":row["location"],"language":row["language"]}

# save the chat
def save_chat(farmer_id,question,answer):
    with connect() as c: c.execute("INSERT INTO chats(farmer_id,question,answer) VALUES(?,?,?)",(farmer_id,question,answer))

# get the chats from user
def get_chats(farmer_id):
    with connect() as c: return [dict(r) for r in c.execute("SELECT * FROM chats WHERE farmer_id=? ORDER BY id",(farmer_id,))]
