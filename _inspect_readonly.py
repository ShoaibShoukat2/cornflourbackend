import sqlite3

con = sqlite3.connect("file:db.sqlite3?mode=ro", uri=True)
cur = con.cursor()
print("TABLES")
for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
    print(row[0])
print("--- USERS ---")
print("count", cur.execute("select count(*) from accounts_user").fetchone())
print("staff", cur.execute("select count(*) from accounts_user where is_staff=1").fetchone())
print("referred", cur.execute("select count(*) from accounts_user where referred_by_id is not null").fetchone())
print("levels", cur.execute("select level, count(*) from accounts_user group by level").fetchall())
print("active", cur.execute("select is_active, is_blocked, count(*) from accounts_user group by is_active, is_blocked").fetchall())
try:
    print("payments", cur.execute("select status, count(*) from administration_packagepayment group by status").fetchall())
    print("pkg", cur.execute("select package_name, status, count(*) from administration_packagepayment group by package_name, status").fetchall())
except Exception as exc:
    print("pay err", exc)
print("USER COLS")
print([row[1] for row in cur.execute("pragma table_info(accounts_user)")])
