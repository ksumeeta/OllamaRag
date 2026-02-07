from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# MS SQL Server connection
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    echo=False,
    fast_executemany=True 
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Vector Database (PostgreSQL) connection
if settings.VECTOR_DB_URL:
    vector_engine = create_engine(
        settings.VECTOR_DB_URL,
        echo=False
    )
    VectorSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=vector_engine)
else:
    vector_engine = None
    VectorSessionLocal = None

Base = declarative_base()

# Dependency to get MS SQL Session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency to get Vector DB Session
def get_vector_db():
    if VectorSessionLocal is None:
        yield None
        return
    db = VectorSessionLocal()
    try:
        yield db
    finally:
        db.close()
