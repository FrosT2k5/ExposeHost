from fastapi import FastAPI
from pydantic import BaseModel
from sqlmodel import Field, Relationship, SQLModel, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncAttrs
from sqlmodel.ext.asyncio.session import AsyncSession
import asyncio
import bcrypt

app = FastAPI()
DATABASE_URL = "sqlite+aiosqlite:///./data.db"
engine = create_async_engine(DATABASE_URL, echo=True)

# SQL Model of users DB
class User(SQLModel, AsyncAttrs, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    email: str = Field(unique=True)
    password: str = Field()

    # Each user can have multiple list of subdomains
    subdomains: list["Subdomain"] = Relationship(back_populates="user")

# SQL Model for subdomain
class Subdomain(SQLModel, AsyncAttrs, table=True):
    subdomain: str = Field(primary_key=True)
    owner_user_id: int = Field(foreign_key="user.id", index=True)
    user: User = Relationship(back_populates="subdomains")


async def create_db_and_tables():  
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all) 


async def add_new_user(username: str, email:str , password: str):
    # Add new user to the db
    
    # Hash the password
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    async with AsyncSession(engine) as session:
        user = User(username=username, email=email, password=hashed)
        session.add(user)

        await session.commit()

async def validate_user(username: str, password: str) -> bool:
    async with AsyncSession(engine) as session:
        query = select(User).where( User.username == username )
        result = await session.exec(query)
        result_user = result.first()
        
        if not result_user:
            return False

        if bcrypt.checkpw(password.encode(), result_user.password.encode()):
            return True
        
        return False

async def add_subdomain_for_user(username: str, subdomain: str):
    async with AsyncSession(engine) as session:
        query = select(User).where( User.username == username )
        result = await session.exec(query)
        result_user = result.first()

        if not result_user:
            return False
        
        subdomain_entity = Subdomain(subdomain=subdomain, owner_user_id=result_user.id)
        session.add(subdomain_entity)
        await session.commit()

        result_user.subdomains.append(subdomain_entity)
        print(result_user)
        return True

async def get_subdomain_for_user(username: str) -> list[str]:
    async with AsyncSession(engine) as session:
        query = select(User).where( User.username == username )
        result = await session.exec(query)
        result_user = result.first()

        if not result_user:
            return []

        subdomain_list = []
        print(result_user)
        # for subdomain in result_user.subdomains:
        #     subdomain_list.append(subdomain.subdomain)
        
        return subdomain_list

"""
Functions for:
- X Adding new user
- Adding subdomain for a user
- Get list of subdomain for a user
- Remove a subdomain for a user
- Function to check if username and password is valid (for auth)
- Check if username exists
- Check if email exists
"""

# Request Input Pydantic Model, contains email and password
class UserInput(BaseModel):
    email: str
    password: str

# Response of auth token, contains token 
class TokenResponse(BaseModel):
    token: str



# @app.post("/register/")
# async def create_item(credentials: UserInput) -> TokenResponse:
    
asyncio.run(create_db_and_tables())
asyncio.run(add_new_user("yash", "yash@eg.co","1234"))
print(asyncio.run(validate_user("yash", "1234")))


print(asyncio.run(add_subdomain_for_user("yash", "example")))
# print(asyncio.run(get_subdomain_for_user("yash")))