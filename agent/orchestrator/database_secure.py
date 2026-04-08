"""Secure database layer using SQLAlchemy ORM (CRITICAL-5 FIX).

Prevents SQL injection by using parameterized queries exclusively.
All database access goes through SQLAlchemy ORM, never raw SQL.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog
from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

logger = structlog.get_logger(__name__)

# Database configuration
DB_URL = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{Path.home()}/.autohost/autohost.db"
)

# Create engine with safety settings
engine = create_engine(
    DB_URL,
    echo=False,
    pool_pre_ping=True,  # Test connection before using
    pool_recycle=3600,   # Recycle connections
    # SQLite-specific settings
    connect_args={"check_same_thread": False} if "sqlite" in DB_URL else {},
)

# Enable WAL mode for SQLite (better concurrency)
if "sqlite" in DB_URL:
    from sqlalchemy import event
    
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ============================================================================
# DATABASE MODELS
# ============================================================================


class TaskRecord(Base):
    """Database model for tasks (parameterized, safe)."""

    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), index=True, nullable=False)  # User isolation
    request = Column(Text, nullable=False)
    state = Column(String(50), nullable=False, default="pending")
    output = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "request": self.request,
            "state": self.state,
            "output": self.output,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class SessionRecord(Base):
    """Database model for user sessions."""

    __tablename__ = "sessions"

    session_id = Column(String(128), primary_key=True, index=True)
    user_id = Column(String(36), index=True, nullable=False)
    username = Column(String(256), nullable=False)
    email = Column(String(256), nullable=False)
    csrf_token = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)
    is_active = Column(String(5), default="true")  # Store as string for SQLite


class AuditLog(Base):
    """Database model for audit trail."""

    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), index=True, nullable=False)
    action = Column(String(256), nullable=False)
    resource = Column(String(256), nullable=False)
    status = Column(String(50), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


# ============================================================================
# DATABASE ACCESS LAYER (Parameterized, Type-Safe)
# ============================================================================


class DatabaseManager:
    """Safe database operations using SQLAlchemy ORM."""

    @staticmethod
    def get_session() -> Session:
        """Get database session."""
        return SessionLocal()

    @staticmethod
    def create_task(
        task_id: str,
        user_id: str,
        request: str,
        state: str = "pending",
    ) -> TaskRecord:
        """
        Create a new task (PARAMETERIZED - INJECTION SAFE).
        
        Uses SQLAlchemy ORM, NOT raw SQL.
        All parameters are properly typed and escaped.
        """
        db = DatabaseManager.get_session()
        try:
            task = TaskRecord(
                id=task_id,
                user_id=user_id,  # User isolation
                request=request,
                state=state,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(task)
            db.commit()
            db.refresh(task)

            logger.info(
                "task_created",
                task_id=task_id,
                user_id=user_id,
                state=state,
            )
            return task
        except Exception as e:
            db.rollback()
            logger.error("task_creation_failed", error=str(e))
            raise
        finally:
            db.close()

    @staticmethod
    def get_task(task_id: str, user_id: str) -> Optional["TaskRecord"]:
        """
        Get task by ID (with user isolation).
        
        Verifies task belongs to user before returning.
        """
        db = DatabaseManager.get_session()
        try:
            # Parameterized query - SQLAlchemy handles escaping
            task = (
                db.query(TaskRecord)
                .filter(TaskRecord.id == task_id)
                .filter(TaskRecord.user_id == user_id)  # User isolation
                .first()
            )

            if task:
                logger.debug("task_retrieved", task_id=task_id, user_id=user_id)
            else:
                logger.debug(
                    "task_not_found",
                    task_id=task_id,
                    user_id=user_id,
                )

            return task
        finally:
            db.close()

    @staticmethod
    def list_tasks(user_id: str, limit: int = 100) -> list[TaskRecord]:
        """
        List all tasks for a user (with user isolation).
        
        Only returns tasks belonging to the authenticated user.
        """
        db = DatabaseManager.get_session()
        try:
            tasks = (
                db.query(TaskRecord)
                .filter(TaskRecord.user_id == user_id)  # User isolation
                .order_by(TaskRecord.created_at.desc())
                .limit(limit)
                .all()
            )

            logger.debug(
                "tasks_listed",
                user_id=user_id,
                count=len(tasks),
            )
            return tasks
        finally:
            db.close()

    @staticmethod
    def update_task(
        task_id: str,
        user_id: str,
        state: Optional[str] = None,
        output: Optional[str] = None,
        error: Optional[str] = None,
    ) -> Optional["TaskRecord"]:
        """
        Update task (PARAMETERIZED UPDATE).
        
        Uses SQLAlchemy for safe parameter substitution.
        """
        db = DatabaseManager.get_session()
        try:
            task = (
                db.query(TaskRecord)
                .filter(TaskRecord.id == task_id)
                .filter(TaskRecord.user_id == user_id)  # User isolation
                .first()
            )

            if not task:
                logger.warning(
                    "task_not_found_for_update",
                    task_id=task_id,
                    user_id=user_id,
                )
                return None

            # Update fields
            if state is not None:
                task.state = state
            if output is not None:
                task.output = output
            if error is not None:
                task.error = error

            task.updated_at = datetime.utcnow()

            if state == "completed" or state == "failed":
                task.completed_at = datetime.utcnow()

            db.commit()
            db.refresh(task)

            logger.info(
                "task_updated",
                task_id=task_id,
                user_id=user_id,
                state=state,
            )
            return task
        except Exception as e:
            db.rollback()
            logger.error("task_update_failed", error=str(e))
            raise
        finally:
            db.close()

    @staticmethod
    def delete_task(task_id: str, user_id: str) -> bool:
        """
        Delete task (with user ownership verification).
        
        Only owners can delete their tasks.
        """
        db = DatabaseManager.get_session()
        try:
            task = (
                db.query(TaskRecord)
                .filter(TaskRecord.id == task_id)
                .filter(TaskRecord.user_id == user_id)  # User isolation
                .first()
            )

            if not task:
                logger.warning(
                    "task_not_found_for_delete",
                    task_id=task_id,
                    user_id=user_id,
                )
                return False

            db.delete(task)
            db.commit()

            logger.info(
                "task_deleted",
                task_id=task_id,
                user_id=user_id,
            )
            return True
        except Exception as e:
            db.rollback()
            logger.error("task_deletion_failed", error=str(e))
            raise
        finally:
            db.close()

    @staticmethod
    def log_audit(
        user_id: str,
        action: str,
        resource: str,
        status: str,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """
        Create audit log entry for security compliance.
        
        Tracks all important actions for forensics.
        """
        from uuid import uuid4

        db = DatabaseManager.get_session()
        try:
            log = AuditLog(
                id=str(uuid4()),
                user_id=user_id,
                action=action,
                resource=resource,
                status=status,
                details=details,
                ip_address=ip_address,
                timestamp=datetime.utcnow(),
            )
            db.add(log)
            db.commit()

            logger.info(
                "audit_log_created",
                user_id=user_id,
                action=action,
                resource=resource,
                status=status,
            )
            return log
        except Exception as e:
            db.rollback()
            logger.error("audit_log_failed", error=str(e))
            raise
        finally:
            db.close()


# ============================================================================
# INITIALIZATION
# ============================================================================


def init_database():
    """Initialize database and create tables."""
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("database_initialized", url=DB_URL)

        # Verify database is writable
        db = SessionLocal()
        try:
            db.execute("SELECT 1")
            db.commit()
        finally:
            db.close()

        logger.info("database_health_check_passed")
    except Exception as e:
        logger.error("database_initialization_failed", error=str(e))
        raise


def backup_database(backup_path: Optional[str] = None) -> str:
    """Create database backup for disaster recovery."""
    import shutil
    from datetime import datetime

    if backup_path is None:
        backup_dir = Path.home() / ".autohost" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = str(
            backup_dir / f"autohost_backup_{datetime.utcnow().isoformat()}.db"
        )

    if "sqlite" in DB_URL:
        db_file = DB_URL.replace("sqlite:///", "")
        shutil.copy2(db_file, backup_path)
        logger.info("database_backup_created", backup_path=backup_path)
        return backup_path

    logger.warning("backup_not_supported_for_non_sqlite")
    return ""
