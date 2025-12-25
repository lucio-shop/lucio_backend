import os
import sqlite3
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DB_PATH = "lucio.db"

# ⚠️ Вставь сюда ID админа (число). Его можно узнать через @userinfobot
ADMIN_ID = 0

app = FastAPI(title="Lucio Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # для продакшена лучше ограничить домен
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            price INTEGER NOT NULL,
            color TEXT NOT NULL,
            img TEXT NOT NULL
        );
    """)
    conn.commit()

    # если пусто — добавим дефолтные товары
    cur.execute("SELECT COUNT(*) as c FROM products")
    c = cur.fetchone()["c"]
    if c == 0:
        seed = [
            ("KITON", 32000, "Коричневый", "https://images.unsplash.com/photo-1520975958225-3f61d18026c9?auto=format&fit=crop&w=900&q=80"),
            ("LORO PIANA", 3500, "Темно-синий", "https://images.unsplash.com/photo-1520975732158-0c2d9933b4aa?auto=format&fit=crop&w=900&q=80"),
            ("ZEGNA", 4500, "Серый", "https://images.unsplash.com/photo-1520975748162-79a2b1a6df9a?auto=format&fit=crop&w=900&q=80"),
            ("HERMES", 2000, "Черный", "https://images.unsplash.com/photo-1520975682031-a54f4a7d2b53?auto=format&fit=crop&w=900&q=80"),
        ]
        cur.executemany("INSERT INTO products(brand, price, color, img) VALUES (?,?,?,?)", seed)
        conn.commit()
    conn.close()

init_db()

# ---- модели ----
class ProductIn(BaseModel):
    brand: str
    price: int
    color: str
    img: str

class ProductUpdate(BaseModel):
    brand: Optional[str] = None
    price: Optional[int] = None
    color: Optional[str] = None
    img: Optional[str] = None

def require_admin(request: Request):
    # Клиент должен прислать header: X-Admin-Id: <telegram_user_id>
    try:
        uid = int(request.headers.get("X-Admin-Id", "0"))
    except:
        uid = 0
    if ADMIN_ID <= 741824475:
        raise HTTPException(500, "ADMIN_ID не настроен на сервере")
    if uid != ADMIN_ID:
        raise HTTPException(403, "Admin only")

@app.get("/products")
def get_products():
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT id, brand, price, color, img FROM products ORDER BY id DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

@app.post("/products")
def add_product(p: ProductIn, request: Request):
    require_admin(request)
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO products(brand, price, color, img) VALUES (?,?,?,?)",
        (p.brand, p.price, p.color, p.img),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"id": new_id}

@app.put("/products/{pid}")
def update_product(pid: int, patch: ProductUpdate, request: Request):
    require_admin(request)
    data = patch.dict(exclude_none=True)
    if not data:
        return {"ok": True}

    sets = []
    values = []
    for k, v in data.items():
        sets.append(f"{k}=?")
        values.append(v)
    values.append(pid)

    conn = db()
    cur = conn.cursor()
    cur.execute(f"UPDATE products SET {', '.join(sets)} WHERE id=?", values)
    conn.commit()
    conn.close()
    return {"ok": True}

@app.delete("/products/{pid}")
def delete_product(pid: int, request: Request):
    require_admin(request)
    conn = db()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return {"ok": True}
