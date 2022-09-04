import os
import sys

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
sys.path.append("Drivogram")
import asyncio
import random
from io import BytesIO

import uvicorn
from Database.db import database
from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from fastapi.security.api_key import APIKey
from Functions.functions import chunk_stream, convert_bytes, data_key
from pyrogram import Client

import auth

data_object = database()
import nest_asyncio
from Config.config import config
from pyrogram import idle
from Telegram.client import app1, app2, app3, app4

chat_id = config.chat_id
choose = [app1, app2, app3, app4]
nest_asyncio.apply()
web = FastAPI()


@web.on_event("startup")
async def startup():
    async def client_start():
        await app1.start()
        await app2.start()
        await app3.start()
        await app4.start()
        await idle()

    asyncio.create_task(client_start())


@web.post("/api/upload")
async def home(
    IN_FILE: UploadFile, X_API_KEY: APIKey = Depends(auth.apikey)
):
    content = await IN_FILE.read()
    b = BytesIO(content)
    b.name = IN_FILE.filename
    random_client = random.choice(choose)
    data_object.create_file_table(table_name="FileData")
    key_file = data_key(type="FILE-", len=7)
    doc = await random_client.send_document(
        chat_id, b, force_document=True, caption=f"{key_file}"
    )
    data_object.insert_file_data(
        filename=IN_FILE.filename,
        fileSize=convert_bytes(doc.document.file_size),
        MessageID=doc.id,
        FileKey=key_file,
        UserID=X_API_KEY,
        Content=IN_FILE.content_type,
        Time=doc.date,
    )
    return {
        "status": 200,
        "msg": "file uploaded successfully",
        "file_key": key_file,
        "user": X_API_KEY,
    }


@web.post("/api/signup")
async def data(Name: str | None = Header(default=None)):
    data_object.create_user_table("UserData")
    if Name == None or Name == "":
        raise HTTPException(
            status_code=422,
            detail="missing parameter 'name',provide a name",
        )
    return {"X-API-KEY": data_object.add_user(Name)}


@web.post("/api/logincheck")
async def login(X_API_KEY: str | None = Header(default=None)):
    if X_API_KEY == None:
        return {
            "status": 422,
            "error": "missing parameter 'X-API-KEY',provide key to login",
        }
    x = data_object.login_check(X_API_KEY)
    if x == None:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized Login, Please signup",
        )
    return {
        "status": 200,
        "message": f"Logged in Successfully as {x}",
    }


@web.get("/api/uploads")
async def uploads(X_API_KEY: APIKey = Depends(auth.apikey)):
    return {
        "User": X_API_KEY,
        "Uploads": data_object.get_uploads(X_API_KEY),
    }


@web.delete("/api/delete")
async def delete(
    FILE_KEY: str | None = Header(default=None),
    X_API_KEY: APIKey = Depends(auth.apikey),
):
    data_object.deleteFile(FILE_KEY)
    return {
        "user": X_API_KEY,
        "status": 200,
        "message": "Deleted the file successfully",
    }


@web.get("/api/download")
async def download(
    FILE_KEY: str | None = Header(default=None),
    X_API_KEY: APIKey = Depends(auth.apikey),
):
    if FILE_KEY == None or FILE_KEY == "":
        raise HTTPException(
            status_code=404, detail="Invalid file Key"
        )

    message_id, content_type = data_object.getFile(
        file_key=FILE_KEY, User_id=X_API_KEY
    )
    if message_id == None:
        raise HTTPException(status_code=404, detail="Not Found")
    else:
        random_client = random.choice(choose)
        msg = await random_client.get_messages(chat_id, message_id)
        file_id = msg.document.file_id
        stream_data = chunk_stream(
            client=random_client, fileID=file_id
        )
    return StreamingResponse(
        stream_data, status_code=200, media_type=content_type
    )


uvicorn.run(web, port=config.web_port)
