from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

Base = declarative_base()

class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True)
    role = Column(String)
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)


#creation
engine = create_engine(f"sqlite:///{os.getenv('DATABASE_URL', 'app/db/locus.db')}")
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)


def save_message(role, content):
    session = Session()
    try:
        newMessage = Message(role=role, content=content)
        session.add(newMessage)
        session.commit()
    except Exception as e:
        print(f"Error saving message: {e}")
        session.rollback()
    finally:
        session.close()

#testing with dummy prompt + init db from above
if __name__ == "__main__":
    save_message("user", "testing locus sqlite setup")
    print("message saved successfully")