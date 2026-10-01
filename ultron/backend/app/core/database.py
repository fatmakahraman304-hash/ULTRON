"""Explicit SQLite resource lifetime for Windows (commit alone does not close)."""
from contextlib import contextmanager
import sqlite3
import weakref

_open = weakref.WeakSet()

class Connection(sqlite3.Connection):
    pass

def connect(*args, **kwargs):
    kwargs.setdefault('factory', Connection)
    db=sqlite3.connect(*args, **kwargs)
    _open.add(db)
    return db

@contextmanager
def transaction(*args, **kwargs):
    db=connect(*args, **kwargs)
    try:
        with db:
            yield db
    finally:
        db.close()

def close_all():
    for db in list(_open):
        db.close()
    _open.clear()
