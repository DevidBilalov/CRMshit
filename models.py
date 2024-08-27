from sqlalchemy import create_engine, MetaData, Column, Integer, String, DateTime, Connection
from sqlalchemy.orm import sessionmaker, declarative_base, base
from datetime import datetime

engine = create_engine('sqlite:///customers.db')

metadata = MetaData()
Base = declarative_base(metadata=metadata)

class Customer(Base):
    __tablename__ = 'customers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, unique=True, nullable=False)
    info = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

metadata.reflect(bind=engine)

Session = sessionmaker(bind=engine)
session = Session()