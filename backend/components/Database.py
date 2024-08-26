# components/Backend/Database.py

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Define the Base for our ORM models
Base = declarative_base()

# Define the Message model
class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True, index=True)
    user_message = Column(Text, nullable=False)
    response_message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Database connection setup
DATABASE_URL = "sqlite:///./test.db"  # Change this URL if you use another database
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the tables in the database
Base.metadata.create_all(bind=engine)

# Function to store messages in the database
def store_messages(user_message: str, response_message: str):
    session = SessionLocal()
    try:
        message = Message(user_message=user_message, response_message=response_message)
        session.add(message)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error storing message: {e}")
    finally:
        session.close()

# Function to get the most recent messages from the database
def get_recent_messages(limit: int = 10):
    session = SessionLocal()
    try:
        messages = session.query(Message).order_by(Message.timestamp.desc()).limit(limit).all()
        return messages
    except Exception as e:
        print(f"Error retrieving recent messages: {e}")
        return []
    finally:
        session.close()
