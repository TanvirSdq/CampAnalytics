"""Best-effort persistent campaign cache.

Toolforge uses MariaDB when explicit credentials or a replica.my.cnf file is
available. Local runs use SQLite only when explicitly configured (or outside
Toolforge). Database failures are cache misses, never request failures.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)
DEFAULT_TTL = 7 * 24 * 60 * 60
METRIC_KEYS = ("quality_image_share", "top10_uploader_share", "usage_share", "total_uploads")
_state_lock = threading.Lock()
_thread_state = threading.local()
_initialized = set()


def _ttl():
    try:
        return max(0, int(os.getenv("CAMPAIGN_CACHE_TTL", DEFAULT_TTL)))
    except ValueError:
        return DEFAULT_TTL


def _mariadb_config():
    """Read explicit credentials, then standard Toolforge replica.my.cnf."""
    host = (
        os.getenv("MYSQL_HOST")
        or os.getenv("TOOLFORGE_DB_HOST")
        or os.getenv("TOOL_TOOLSDB_HOST")
    )
    database = (
        os.getenv("MYSQL_DATABASE")
        or os.getenv("TOOLFORGE_DB_NAME")
        or os.getenv("TOOL_TOOLSDB_NAME")
    )
    user = (
        os.getenv("MYSQL_USER")
        or os.getenv("TOOLFORGE_DB_USER")
        or os.getenv("TOOL_TOOLSDB_USER")
    )
    password = (
        os.getenv("MYSQL_PASSWORD")
        or os.getenv("TOOLFORGE_DB_PASSWORD")
        or os.getenv("TOOL_TOOLSDB_PASSWORD")
    )
    defaults = os.getenv("TOOLFORGE_REPLICA_CNF") or os.getenv("MYSQL_DEFAULTS_FILE")
    if not (host and database and user):
        candidates = [
            Path.home() / "replica.my.cnf",
            Path("/etc/mysql/conf.d/replica.my.cnf"),
        ]
        defaults = defaults or next((str(path) for path in candidates if path.exists()), None)
        if defaults and Path(defaults).exists():
            try:
                import configparser
                parser = configparser.ConfigParser()
                parser.read(defaults)
                section = parser["client"]
                host = host or section.get("host")
                database = database or section.get("database") or section.get("dbname") or os.getenv("TOOLFORGE_DB_NAME")
                user = user or section.get("user")
                password = password or section.get("password")
            except Exception as exc:
                logger.warning("Unable to read Toolforge database config: %s", exc)
    if not (host and database and user):
        return None
    try:
        port = int(os.getenv("MYSQL_PORT", "3306"))
    except ValueError:
        port = 3306
    return {"host": host, "port": port, "database": database, "user": user,
            "password": password or "", "charset": "utf8mb4",
            "connect_timeout": 5, "autocommit": False}


def _backend_key():
    config = _mariadb_config()
    if config:
        return ("mariadb", config["host"], config["port"], config["database"], config["user"])
    
    if os.path.exists("/data/project/campanalytics"):
        db_path = "/data/project/campanalytics/campaign_cache.sqlite3"
    else:
        db_path = os.getenv("CAMPAIGN_CACHE_SQLITE_PATH", "campaign_cache.sqlite3")
        
    return ("sqlite", os.path.abspath(db_path))


def _new_connection(key):
    if key[0] == "mariadb":
        import pymysql
        config = _mariadb_config()
        if not config:
            raise RuntimeError("MariaDB configuration disappeared")
        return pymysql.connect(**config), "mariadb"
    return sqlite3.connect(key[1], timeout=5), "sqlite"


@contextmanager
def _connection():
    key = _backend_key()
    if key is None:
        raise RuntimeError("Toolforge database credentials or replica.my.cnf are not configured")
    current = getattr(_thread_state, "connection", None)
    if current is None or getattr(_thread_state, "key", None) != key:
        current, backend = _new_connection(key)
        _thread_state.connection, _thread_state.key, _thread_state.backend = current, key, backend
    try:
        yield current, _thread_state.backend
    except Exception:
        try:
            current.rollback()
        except Exception:
            pass
        raise


def initialize_cache():
    """Lazily create schema once per backend/process."""
    key = _backend_key()
    if key is None:
        return False
    if key in _initialized:
        return True
    with _state_lock:
        if key in _initialized:
            return True
        try:
            with _connection() as (connection, backend):
                cursor = connection.cursor()
                statements = [
                    """CREATE TABLE IF NOT EXISTS campaign_participant_fetches (
                    code VARCHAR(32) PRIMARY KEY, fetched_at DOUBLE NOT NULL)""",
                    """CREATE TABLE IF NOT EXISTS campaign_participants (
                    code VARCHAR(32) NOT NULL, username VARCHAR(255) NOT NULL,
                    PRIMARY KEY (code, username))""",
                    """CREATE TABLE IF NOT EXISTS campaign_metrics (
                    code VARCHAR(32) PRIMARY KEY, fetched_at DOUBLE NOT NULL,
                    quality_image_share DOUBLE NOT NULL, top10_uploader_share DOUBLE NOT NULL,
                    usage_share DOUBLE NOT NULL, total_uploads DOUBLE NOT NULL)""",
                ]
                for statement in statements:
                    cursor.execute(statement)
                connection.commit()
            _initialized.add(key)
            return True
        except Exception as exc:
            logger.warning("Persistent campaign cache unavailable: %s", exc)
            return False


def _fresh(timestamp):
    return _ttl() == 0 or time.time() - timestamp <= _ttl()


def get_participants(code):
    try:
        if not initialize_cache():
            return None
        with _connection() as (connection, backend):
            cursor = connection.cursor()
            cursor.execute("SELECT fetched_at FROM campaign_participant_fetches WHERE code=" + ("%s" if backend == "mariadb" else "?"), (code,))
            row = cursor.fetchone()
            if not row or not _fresh(float(row[0])):
                return None
            cursor.execute("SELECT username FROM campaign_participants WHERE code=" + ("%s" if backend == "mariadb" else "?"), (code,))
            return {item[0] for item in cursor.fetchall()}
    except Exception as exc:
        logger.warning("Unable to read participant cache: %s", exc)
        return None


def put_participants(code, usernames):
    try:
        if not initialize_cache():
            return False
        with _connection() as (connection, backend):
            placeholder = "%s" if backend == "mariadb" else "?"
            cursor = connection.cursor()
            cursor.execute("DELETE FROM campaign_participants WHERE code=" + placeholder, (code,))
            if usernames:
                cursor.executemany(
                    ("INSERT IGNORE" if backend == "mariadb" else "INSERT OR IGNORE")
                    + " INTO campaign_participants (code, username) VALUES (" + placeholder + ", " + placeholder + ")",
                    [(code, name) for name in set(usernames)],
                )
            cursor.execute(
                ("INSERT INTO campaign_participant_fetches (code, fetched_at) VALUES (" + placeholder + ", " + placeholder + ") "
                 + ("ON DUPLICATE KEY UPDATE fetched_at=VALUES(fetched_at)" if backend == "mariadb"
                    else "ON CONFLICT(code) DO UPDATE SET fetched_at=excluded.fetched_at")),
                (code, time.time()),
            )
            connection.commit()
            return True
    except Exception as exc:
        logger.warning("Unable to write participant cache: %s", exc)
        return False


def get_metrics(code):
    try:
        if not initialize_cache():
            return None
        with _connection() as (connection, backend):
            placeholder = "%s" if backend == "mariadb" else "?"
            cursor = connection.cursor()
            cursor.execute("SELECT fetched_at, quality_image_share, top10_uploader_share, usage_share, total_uploads FROM campaign_metrics WHERE code=" + placeholder, (code,))
            row = cursor.fetchone()
            if not row or not _fresh(float(row[0])):
                return None
            return dict(zip(METRIC_KEYS, (float(value) for value in row[1:])))
    except Exception as exc:
        logger.warning("Unable to read metrics cache: %s", exc)
        return None


def put_metrics(code, metrics):
    try:
        if not initialize_cache():
            return False
        with _connection() as (connection, backend):
            placeholder = "%s" if backend == "mariadb" else "?"
            values = [float(metrics[key]) for key in METRIC_KEYS]
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO campaign_metrics (code, fetched_at, quality_image_share, top10_uploader_share, usage_share, total_uploads) "
                "VALUES (" + ", ".join([placeholder] * 6) + ") "
                + ("ON DUPLICATE KEY UPDATE fetched_at=VALUES(fetched_at), quality_image_share=VALUES(quality_image_share), "
                   "top10_uploader_share=VALUES(top10_uploader_share), usage_share=VALUES(usage_share), total_uploads=VALUES(total_uploads)"
                   if backend == "mariadb" else
                   "ON CONFLICT(code) DO UPDATE SET fetched_at=excluded.fetched_at, quality_image_share=excluded.quality_image_share, "
                   "top10_uploader_share=excluded.top10_uploader_share, usage_share=excluded.usage_share, total_uploads=excluded.total_uploads"),
                (code, time.time(), *values),
            )
            connection.commit()
            return True
    except Exception as exc:
        logger.warning("Unable to write metrics cache: %s", exc)
        return False
