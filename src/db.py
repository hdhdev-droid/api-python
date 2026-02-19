"""
DB 연결: PostgreSQL, MySQL/MariaDB, MongoDB 지원.
DB_TYPE 미지정 시 DB_PORT로 유형 추론 (5432=PostgreSQL, 3306=MySQL, 27017=MongoDB).
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

try:
    from . import config as config_module
    from . import db_logger
except ImportError:
    import config as config_module
    import db_logger

DB_TYPES = ["POSTGRESQL", "MYSQL", "MARIADB", "MONGODB"]
PORT_TO_TYPE = {5432: "POSTGRESQL", 3306: "MYSQL", 27017: "MONGODB"}

_pg_pool = None
_mysql_pool = None  # unused; MySQL uses _mysql_get_connection() per request
_mongo_client = None
_mongo_db = None
_ping_ok_logged = False


def get_db_type() -> Optional[str]:
    explicit = (config_module.DB_TYPE or "").strip().upper() or None
    if explicit and explicit in DB_TYPES:
        return explicit
    try:
        port = int(config_module.DB_PORT) if config_module.DB_PORT else None
    except (TypeError, ValueError):
        return None
    return PORT_TO_TYPE.get(port) if port is not None else None


def is_configured() -> bool:
    t = get_db_type()
    if not t:
        return False
    return bool(config_module.DB_HOST and config_module.DB_NAME)


def _item_from_row(r: Dict[str, Any]) -> Dict[str, Any]:
    created = r.get("created_at") or r.get("createdAt")
    if hasattr(created, "isoformat"):
        created_str = created.isoformat()
    elif created is not None:
        created_str = str(created)
    else:
        created_str = None
    return {
        "id": r.get("id"),
        "name": r.get("name"),
        "createdAt": created_str,
    }


# ---------- PostgreSQL ----------
def _get_pg_pool():
    global _pg_pool
    if _pg_pool is not None:
        return _pg_pool
    import psycopg2
    from psycopg2 import pool

    c = config_module
    port = int(c.DB_PORT) if c.DB_PORT else 5432
    db_logger.add_log(
        f"Connecting to PostgreSQL {dict(host=c.DB_HOST, port=port, database=c.DB_NAME, user=c.DB_USER)}"
    )
    _pg_pool = pool.SimpleConnectionPool(
        1, 10,
        host=c.DB_HOST,
        port=port,
        database=c.DB_NAME,
        user=c.DB_USER,
        password=c.DB_PASSWORD,
    )
    return _pg_pool


def _pg_get_tables() -> Dict[str, Any]:
    pool = _get_pg_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """
            )
            rows = cur.fetchall()
        return {"tables": [r[0] for r in rows]}
    finally:
        pool.putconn(conn)


def _pg_ensure_items() -> None:
    pool = _get_pg_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS items (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )
        conn.commit()
    finally:
        pool.putconn(conn)


def _pg_get_items() -> List[Dict[str, Any]]:
    _pg_ensure_items()
    pool = _get_pg_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, created_at FROM items ORDER BY id")
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return [_item_from_row(r) for r in rows]
    finally:
        pool.putconn(conn)


def _pg_get_item_by_id(id: int) -> Optional[Dict[str, Any]]:
    _pg_ensure_items()
    pool = _get_pg_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, created_at FROM items WHERE id = %s", (id,))
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
        if not row:
            return None
        return _item_from_row(dict(zip(cols, row)))
    finally:
        pool.putconn(conn)


def _pg_create_item(name: str) -> Dict[str, Any]:
    _pg_ensure_items()
    pool = _get_pg_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO items (name) VALUES (%s) RETURNING id, name, created_at",
                (name,),
            )
            row = cur.fetchone()
            cols = [d[0] for d in cur.description]
        conn.commit()
        return _item_from_row(dict(zip(cols, row)))
    finally:
        pool.putconn(conn)


# ---------- MySQL / MariaDB ----------
def _mysql_get_connection():
    """MySQL은 매 요청마다 새 연결 사용 (간단한 구현)."""
    import pymysql
    c = config_module
    port = int(c.DB_PORT) if c.DB_PORT else 3306
    return pymysql.connect(
        host=c.DB_HOST,
        port=port,
        database=c.DB_NAME,
        user=c.DB_USER,
        password=c.DB_PASSWORD,
    )


def _mysql_get_tables() -> Dict[str, Any]:
    conn = _mysql_get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = %s AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """,
                (config_module.DB_NAME,),
            )
            rows = cur.fetchall()
        return {"tables": [r[0] for r in rows]}
    finally:
        conn.close()


def _mysql_ensure_items() -> None:
    conn = _mysql_get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS items (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6)
                )
                """
            )
        conn.commit()
    finally:
        conn.close()


def _mysql_get_items() -> List[Dict[str, Any]]:
    _mysql_ensure_items()
    conn = _mysql_get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, created_at FROM items ORDER BY id")
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return [_item_from_row(r) for r in rows]
    finally:
        conn.close()


def _mysql_get_item_by_id(id: int) -> Optional[Dict[str, Any]]:
    _mysql_ensure_items()
    conn = _mysql_get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, created_at FROM items WHERE id = %s", (id,))
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
        if not row:
            return None
        return _item_from_row(dict(zip(cols, row)))
    finally:
        conn.close()


def _mysql_create_item(name: str) -> Dict[str, Any]:
    _mysql_ensure_items()
    conn = _mysql_get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO items (name) VALUES (%s)", (name,))
            insert_id = cur.lastrowid
        conn.commit()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, created_at FROM items WHERE id = %s", (insert_id,)
            )
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
        return _item_from_row(dict(zip(cols, row)))
    finally:
        conn.close()


# ---------- MongoDB ----------
def _get_mongo_db():
    global _mongo_client, _mongo_db
    if _mongo_db is not None:
        return _mongo_db
    from pymongo import MongoClient
    from urllib.parse import quote_plus

    c = config_module
    port = int(c.DB_PORT) if c.DB_PORT else 27017
    auth = ""
    if c.DB_USER and c.DB_PASSWORD:
        auth = f"{quote_plus(c.DB_USER)}:{quote_plus(c.DB_PASSWORD)}@"
    db_logger.add_log(
        f"Connecting to MongoDB {dict(host=c.DB_HOST, port=port, database=c.DB_NAME, user='(set)' if c.DB_USER else '(none)')}"
    )
    url = f"mongodb://{auth}{c.DB_HOST}:{port}/{c.DB_NAME}"
    _mongo_client = MongoClient(url)
    _mongo_db = _mongo_client[c.DB_NAME]
    return _mongo_db


def _mongo_get_tables() -> Dict[str, Any]:
    db = _get_mongo_db()
    names = db.list_collection_names()
    return {"tables": names}


def _mongo_items_collection(db):
    return db["items"]


def _mongo_doc_to_item(doc: Dict[str, Any]) -> Dict[str, Any]:
    created = doc.get("createdAt")
    if hasattr(created, "isoformat"):
        created_str = created.isoformat()
    elif created is not None:
        created_str = str(created)
    else:
        created_str = None
    return {
        "id": doc.get("id"),
        "name": doc.get("name"),
        "createdAt": created_str,
    }


def _mongo_get_items() -> List[Dict[str, Any]]:
    db = _get_mongo_db()
    col = _mongo_items_collection(db)
    list_ = list(col.find({}).sort("id", 1))
    return [_mongo_doc_to_item(d) for d in list_]


def _mongo_get_item_by_id(id: int) -> Optional[Dict[str, Any]]:
    try:
        num_id = int(id)
    except (TypeError, ValueError):
        return None
    db = _get_mongo_db()
    col = _mongo_items_collection(db)
    doc = col.find_one({"id": num_id})
    if not doc:
        return None
    return _mongo_doc_to_item(doc)


def _mongo_create_item(name: str) -> Dict[str, Any]:
    db = _get_mongo_db()
    col = _mongo_items_collection(db)
    last = col.find_one(sort=[("id", -1)])
    next_id = (last["id"] + 1) if last else 1
    doc = {"id": next_id, "name": name, "createdAt": datetime.utcnow()}
    col.insert_one(doc)
    return _mongo_doc_to_item(doc)


# ---------- Ping ----------
def ping() -> bool:
    global _ping_ok_logged
    if not is_configured():
        return False
    t = get_db_type()
    try:
        if t == "POSTGRESQL":
            pool = _get_pg_pool()
            conn = pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            finally:
                pool.putconn(conn)
            if not _ping_ok_logged:
                db_logger.add_log("Ping OK (PostgreSQL)")
                _ping_ok_logged = True
            return True
        if t in ("MYSQL", "MARIADB"):
            conn = _mysql_get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            finally:
                conn.close()
            if not _ping_ok_logged:
                db_logger.add_log("Ping OK (MySQL/MariaDB)")
                _ping_ok_logged = True
            return True
        if t == "MONGODB":
            db = _get_mongo_db()
            db.command("ping")
            if not _ping_ok_logged:
                db_logger.add_log("Ping OK (MongoDB)")
                _ping_ok_logged = True
            return True
        return False
    except Exception as e:
        db_logger.add_log(f"Ping failed: {e}", is_error=True)
        return False


# ---------- Public API ----------
def get_tables() -> Dict[str, Any]:
    if not is_configured():
        return {
            "error": "DB가 설정되지 않았습니다. DB_TYPE, DB_HOST, DB_NAME 등 환경 변수를 확인하세요."
        }
    t = get_db_type()
    try:
        if t == "POSTGRESQL":
            return _pg_get_tables()
        if t in ("MYSQL", "MARIADB"):
            return _mysql_get_tables()
        if t == "MONGODB":
            return _mongo_get_tables()
        return {
            "error": "지원하지 않는 DB_TYPE입니다. POSTGRESQL, MYSQL, MARIADB, MONGODB 중 하나를 사용하세요."
        }
    except Exception as e:
        return {"error": str(e)}


def get_items() -> Optional[List[Dict[str, Any]]]:
    if not is_configured():
        return None
    t = get_db_type()
    if t == "POSTGRESQL":
        return _pg_get_items()
    if t in ("MYSQL", "MARIADB"):
        return _mysql_get_items()
    if t == "MONGODB":
        return _mongo_get_items()
    return None


def get_item_by_id(id: int) -> Optional[Dict[str, Any]]:
    if not is_configured():
        return None
    t = get_db_type()
    if t == "POSTGRESQL":
        return _pg_get_item_by_id(id)
    if t in ("MYSQL", "MARIADB"):
        return _mysql_get_item_by_id(id)
    if t == "MONGODB":
        return _mongo_get_item_by_id(id)
    return None


def create_item(name: str) -> Optional[Dict[str, Any]]:
    if not is_configured():
        return None
    t = get_db_type()
    if t == "POSTGRESQL":
        return _pg_create_item(name)
    if t in ("MYSQL", "MARIADB"):
        return _mysql_create_item(name)
    if t == "MONGODB":
        return _mongo_create_item(name)
    return None
