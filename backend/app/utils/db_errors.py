"""Telling "the database is unreachable" apart from "this request was bad".

A connection failure does not surface as one tidy exception type. Verified
empirically against this stack - the same outage produces different classes
depending on where it fails:

  - socket.gaierror                  host can't be resolved (DB container or
                                     DNS down). Raised RAW by asyncpg, not
                                     wrapped by SQLAlchemy at all.
  - asyncpg.PostgresError subclasses server reachable but refusing the
                                     connection - this is what a Neon
                                     compute-quota rejection looks like
                                     (InsufficientResourcesError).
  - SQLAlchemy OperationalError /    when SQLAlchemy does wrap the DBAPI
    InterfaceError                   error, e.g. a connection dropped
                                     mid-query.

Deliberately does NOT match bare OSError, even though socket.gaierror and
ConnectionRefusedError are both OSError subclasses: the upload path does
real file I/O, and a failed disk write is a genuine 500, not a "database is
down" 503. The specific network subclasses are matched instead.
"""

import asyncio
import socket

from sqlalchemy.exc import DisconnectionError, InterfaceError, OperationalError

try:
    from asyncpg.exceptions import (
        CannotConnectNowError,
        InsufficientResourcesError,
        PostgresConnectionError,
    )

    _ASYNCPG_UNAVAILABLE: tuple = (
        # Covers ConnectionDoesNotExistError / ConnectionFailureError.
        PostgresConnectionError,
        # Covers TooManyConnectionsError, and is the class a provider uses
        # to reject connections once a plan's compute quota is spent.
        InsufficientResourcesError,
        # Server is starting up or shutting down.
        CannotConnectNowError,
    )
except ImportError:  # asyncpg isn't installed in sqlite-only environments
    _ASYNCPG_UNAVAILABLE = ()


DB_UNAVAILABLE_ERRORS: tuple = (
    OperationalError,
    InterfaceError,
    DisconnectionError,
    socket.gaierror,
    ConnectionRefusedError,
    ConnectionResetError,
    asyncio.TimeoutError,
    *_ASYNCPG_UNAVAILABLE,
)

DB_UNAVAILABLE_MESSAGE = (
    "Service temporarily unavailable - please try again shortly."
)


def is_db_unavailable(exc: BaseException) -> bool:
    """True when exc means the database can't be reached right now.

    Walks the __cause__/__context__ chain as well as checking exc itself,
    because SQLAlchemy and asyncpg both re-raise wrapped errors - the
    class that actually identifies the outage is often the inner one.
    """
    seen: set[int] = set()
    current: BaseException | None = exc

    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, DB_UNAVAILABLE_ERRORS):
            return True
        current = current.__cause__ or current.__context__

    return False
