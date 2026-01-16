from dotenv import load_dotenv
from pathlib import Path
from contextlib import asynccontextmanager

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from tqdm import tqdm
import shutil
import os
import uuid
from motor.motor_asyncio import AsyncIOMotorClient
from src import rag


MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")


client = AsyncIOMotorClient(MONGODB_URI)
db = client.notebook_llm


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager - load API keys and settings from database on startup."""
    try:
        settings = await db.settings.find_one({"_id": "global"})
        if settings:
            registry = rag.get_registry()
            

            api_keys = settings.get("api_keys", {})
            for provider_name, api_key in api_keys.items():
                if api_key and provider_name in ["openai", "anthropic", "gemini"]:
                    try:
                        provider = registry.get_provider(provider_name)
                        provider.api_key = api_key
                        print(f"Loaded API key for {provider_name} from database")
                    except Exception as e:
                        print(f"Error loading API key for {provider_name}: {e}")
            

            ollama_url = settings.get("ollama_url")
            if ollama_url:
                ollama_provider = registry.get_provider("ollama")
                ollama_provider.base_url = ollama_url
                print(f"Loaded Ollama URL from database: {ollama_url}")
            

            chat_provider = settings.get("chat_provider", "ollama")
            chat_model = settings.get("chat_model")
            registry.set_chat_provider(chat_provider, chat_model)
            
            embedding_provider = settings.get("embedding_provider", "ollama")
            embedding_model = settings.get("embedding_model")
            try:
                registry.set_embedding_provider(embedding_provider, embedding_model)
            except ValueError:
                registry.set_embedding_provider("ollama", embedding_model)
            
            print(f"Loaded provider settings: chat={chat_provider}, embedding={embedding_provider}")
    except Exception as e:
        print(f"Error loading settings on startup: {e}")
    
    yield  # App runs here
    

    print("Shutting down...")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request, call_next):
    import time
    start_time = time.time()
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {request.method} {request.url}")
    
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {request.method} {request.url} {response.status_code} - {process_time:.2f}ms")
    return response



class ChatRequest(BaseModel):
    notebook_id: str
    messages: List[dict]
    selected_sources: List[str] = None


async def process_file_task(notebook_id: str, file_path: str, filename: str):
    try:
        from src.loaders import load_document, get_file_type
        

        file_type = get_file_type(file_path)
        print(f"Processing file: {filename} (type: {file_type})")
        

        if file_type == "audio":
            content = rag.transcribe_audio(file_path)
            source_type = "audio"
        else:

            result = load_document(file_path)
            
            if not result["success"]:
                raise ValueError(f"Failed to load document: {result.get('error', 'Unknown error')}")
            
            content = result["text"]
            source_type = result["file_type"]
            

            if source_type == "pdf" and (not content or len(content) < 50):
                print("PDF has no text, attempting OCR...")
                try:
                    from pdf2image import convert_from_path
                    import pytesseract
                    
                    images = convert_from_path(file_path, dpi=300)
                    print(f"Converted {len(images)} pages for OCR")
                    
                    ocr_content = ""
                    for i, image in tqdm(enumerate(images), total=len(images), desc="OCR", unit="page"):
                        ocr_content += pytesseract.image_to_string(image) + "\n"
                    
                    content = ocr_content.strip()
                    print(f"OCR extracted {len(content)} characters")
                except Exception as e:
                    print(f"OCR failed: {e}")
            
            if not content:
                raise ValueError(f"No text extracted from {filename}")
        
        print(f"Extracted {len(content)} characters from {filename}")


        rag.process_document(notebook_id, file_path, content, source_type, filename)
        

        from bson import ObjectId
        print(f"DEBUG: Processing complete for {filename}. Content length: {len(content)}")
        
        try:
            result = await db.notebooks.update_one(
                {"_id": ObjectId(notebook_id), "sources.name": filename},
                {"$set": {"sources.$.status": "ready", "sources.$.content": content, "sources.$.type": source_type}}
            )
            print(f"DEBUG: DB Update (ObjectId) matched={result.matched_count} modified={result.modified_count}")
        except Exception as e:
            print(f"DEBUG: Retry with string ID due to: {e}")
            result = await db.notebooks.update_one(
                {"_id": notebook_id, "sources.name": filename},
                {"$set": {"sources.$.status": "ready", "sources.$.content": content, "sources.$.type": source_type}}
            )
            print(f"DEBUG: DB Update (String ID) matched={result.matched_count} modified={result.modified_count}")
        
    except Exception as e:
        print(f"Error processing file: {e}")
        from bson import ObjectId
        try:
            await db.notebooks.update_one(
                {"_id": ObjectId(notebook_id), "sources.name": filename},
                {"$set": {"sources.$.status": "error", "sources.$.error": str(e)}}
            )
        except:
             await db.notebooks.update_one(
                {"_id": notebook_id, "sources.name": filename},
                {"$set": {"sources.$.status": "error", "sources.$.error": str(e)}}
            )
    # Note: File is kept in uploads/ for viewing via /raw endpoint

@app.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    notebook_id: str = Form(...)
):
    # Save file to persistent storage
    upload_dir = os.path.join(os.getcwd(), "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{uuid.uuid4()}_{file.filename}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        

    from src.loaders import get_file_type
    detected_type = get_file_type(file.filename)
    source_type = detected_type if detected_type else "text"
        
    source_item = {
        "name": file.filename,
        "type": source_type,
        "status": "processing",
        "file_path": file_path
    }


    from bson import ObjectId
    try:
        await db.notebooks.update_one(
            {"_id": ObjectId(notebook_id)},
            {
                "$push": {"sources": source_item},
                "$inc": {"source_count": 1}
            }
        )
    except:
        await db.notebooks.update_one(
            {"_id": notebook_id},
            {
                "$push": {"sources": source_item},
                "$inc": {"source_count": 1}
            }
        )
    
    background_tasks.add_task(process_file_task, notebook_id, file_path, file.filename)
    
    return {"status": "processing", "notebook_id": notebook_id}


class UrlUploadRequest(BaseModel):
    notebook_id: str
    url: str

async def process_url_task(notebook_id: str, url: str):
    try:
        from src.loaders import load_url, download_youtube_audio
        import os
        
        print(f"Processing URL: {url}")
        

        is_youtube = any(x in url for x in ["youtube.com", "youtu.be"])
        file_path = url # Default for web
        
        if is_youtube:
            print(f"Detected YouTube URL, downloading audio...")
            upload_dir = os.path.join(os.getcwd(), "uploads")

            file_path = download_youtube_audio(url, upload_dir)
            
            print(f"Transcribing YouTube audio: {file_path}")
            content = rag.transcribe_audio(file_path)
            source_type = "audio"
            source_name = url
        else:

            content = load_url(url)
            source_type = "web"
            source_name = url
        
        if not content:
            raise ValueError(f"No content extracted from {url}")
            
        print(f"Extracted {len(content)} characters from {url}")
        

        rag.process_document(notebook_id, file_path, content, source_type, source_name)
        

        from bson import ObjectId
        print(f"Processing complete for {url}")
        
        update_fields = {
            "sources.$.status": "ready", 
            "sources.$.content": content, 
            "sources.$.type": source_type
        }
        
        if is_youtube:
            # Update file_path so the raw endpoint serves the MP3
            update_fields["sources.$.file_path"] = file_path
        
        try:
            result = await db.notebooks.update_one(
                {"_id": ObjectId(notebook_id), "sources.name": url},
                {"$set": update_fields}
            )
        except Exception:
            await db.notebooks.update_one(
                {"_id": notebook_id, "sources.name": url},
                {"$set": update_fields}
            )
            
    except Exception as e:
        print(f"Error processing URL {url}: {e}")
        # Update status to error
        from bson import ObjectId
        try:
            await db.notebooks.update_one(
                {"_id": ObjectId(notebook_id), "sources.name": url},
                {"$set": {"sources.$.status": "error", "sources.$.error": str(e)}}
            )
        except Exception:
             await db.notebooks.update_one(
                {"_id": notebook_id, "sources.name": url},
                {"$set": {"sources.$.status": "error", "sources.$.error": str(e)}}
            )


@app.post("/upload/url")
async def upload_url(request: UrlUploadRequest, background_tasks: BackgroundTasks):
    notebook_id = request.notebook_id
    url = request.url
    
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    source_item = {
        "name": url,
        "type": "web",
        "status": "processing",
        "file_path": url # URL serves as path
    }


    from bson import ObjectId
    try:
        await db.notebooks.update_one(
            {"_id": ObjectId(notebook_id)},
            {
                "$push": {"sources": source_item},
                "$inc": {"source_count": 1}
            }
        )
    except:
        await db.notebooks.update_one(
            {"_id": notebook_id},
            {
                "$push": {"sources": source_item},
                "$inc": {"source_count": 1}
            }
        )
    
    background_tasks.add_task(process_url_task, notebook_id, url)
    
    return {"status": "processing", "notebook_id": notebook_id}


from fastapi.responses import FileResponse

@app.get("/notebooks/{notebook_id}/sources/{raw_path:path}")
async def get_source_file(notebook_id: str, raw_path: str):
    """Serve the raw source file."""
    if not raw_path.endswith("/raw"):
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    source_name = raw_path[:-4]
    pass
    from bson import ObjectId
    try:
        notebook = await db.notebooks.find_one({"_id": ObjectId(notebook_id)})
    except:
        notebook = await db.notebooks.find_one({"_id": notebook_id})
        
    if not notebook or "sources" not in notebook:
        raise HTTPException(status_code=404, detail="Notebook or source not found")
        
    source = next((s for s in notebook["sources"] if s["name"] == source_name), None)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
        
    file_path = source.get("file_path")
    
    # Fallback: legacy files might not have file_path stored.
    # Search in uploads dir for a file ending with _{source_name}
    if not file_path or not os.path.exists(file_path):
        import glob
        # Check both /tmp/uploads (legacy) and new uploads dir
        potential_dirs = ["/tmp/uploads", os.path.join(os.getcwd(), "uploads")]
        
        matches = []
        for d in potential_dirs:
            if os.path.exists(d):
                pattern = os.path.join(d, f"*_{source_name}")
                matches.extend(glob.glob(pattern))
        
        if matches:
            # Use the most recent one if duplicates (unlikely with UUIDs but possible if re-uploaded)
            file_path = max(matches, key=os.path.getctime)
            
            # Update DB to store this path for future
            try:
                if notebook.get("_id"):
                    filter_q = {"_id": notebook["_id"], "sources.name": source_name}
                else:
                    filter_q = {"_id": notebook_id, "sources.name": source_name}
                    
                await db.notebooks.update_one(
                    filter_q,
                    {"$set": {"sources.$.file_path": file_path}}
                )
            except Exception as e:
                print(f"Failed to update file_path in DB: {e}")
        else:
             raise HTTPException(status_code=404, detail="Source file not found on server")

    return FileResponse(file_path, filename=source_name)

@app.post("/chat")
async def chat(request: ChatRequest):

    user_msg = request.messages[-1]
    if user_msg["role"] == "user":
        from bson import ObjectId
        try:
            await db.notebooks.update_one(
                {"_id": ObjectId(request.notebook_id)},
                {"$push": {"messages": user_msg}}
            )
        except:
             await db.notebooks.update_one(
                {"_id": request.notebook_id},
                {"$push": {"messages": user_msg}}
            )

    async def stream_and_save():

        full_source_content = []
        if request.selected_sources:
            try:
                from bson import ObjectId
                try: 
                    nb_id_obj = ObjectId(request.notebook_id)
                    nb = await db.notebooks.find_one({"_id": nb_id_obj})
                except:
                    nb = await db.notebooks.find_one({"_id": request.notebook_id})
                
                if nb and "sources" in nb:
                    total_chars = 0
                    temp_content = []
                    
                    for s in nb["sources"]:
                        if s["name"] in request.selected_sources:
                            c = s.get("content", "")
                            if c:
                                temp_content.append({"name": s["name"], "content": c})
                                total_chars += len(c)
                    
                    if 0 < total_chars < MAX_FULL_CONTEXT:
                        full_source_content = temp_content
            except Exception as e:
                print(f"Error loading full context: {e}")

        full_response = ""

        async for chunk in rag.stream_chat_response(
            request.notebook_id, 
            request.messages, 
            selected_sources=request.selected_sources, 
            full_source_content=full_source_content
        ):
            full_response += chunk
            yield chunk
            

        assistant_msg = {"role": "assistant", "content": full_response}
        from bson import ObjectId
        try:
            await db.notebooks.update_one(
                {"_id": ObjectId(request.notebook_id)},
                {"$push": {"messages": assistant_msg}}
            )
        except:
             await db.notebooks.update_one(
                {"_id": request.notebook_id},
                {"$push": {"messages": assistant_msg}}
            )

    return StreamingResponse(
        stream_and_save(),
        media_type="text/plain"
    )

@app.get("/notebooks")
async def list_notebooks():
    notebooks = await db.notebooks.find().to_list(100)

    for n in notebooks:
        n["id"] = str(n["_id"])
        del n["_id"]
    return notebooks

class CreateNotebookRequest(BaseModel):
    title: str

@app.post("/notebooks/create")
async def create_notebook(request: CreateNotebookRequest):
    new_notebook = {
        "title": request.title,
        "source_count": 0,
        "updated": "Just now",
        "status": "ready",
        "sources": [],
        "messages": [
            {"role": "assistant", "content": "Hello! Upload a document to get started or ask me anything about your existing sources."}
        ]
    }
    result = await db.notebooks.insert_one(new_notebook)
    return {"id": str(result.inserted_id), "title": request.title}

# Notebook data endpoints
@app.get("/notebooks/{notebook_id}")
async def get_notebook(notebook_id: str):
    """Get notebook with sources and messages."""
    from bson import ObjectId
    try:
        notebook = await db.notebooks.find_one({"_id": ObjectId(notebook_id)})
    except:
        notebook = await db.notebooks.find_one({"_id": notebook_id})
    
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")
    
    notebook["id"] = str(notebook["_id"])
    del notebook["_id"]
    return notebook

class RenameNotebookRequest(BaseModel):
    title: str

@app.put("/notebooks/{notebook_id}/rename")
async def rename_notebook(notebook_id: str, request: RenameNotebookRequest):
    from bson import ObjectId
    try:
        result = await db.notebooks.update_one(
            {"_id": ObjectId(notebook_id)},
            {"$set": {"title": request.title}}
        )
    except:
        result = await db.notebooks.update_one(
            {"_id": notebook_id},
            {"$set": {"title": request.title}}
        )
    return {"status": "ok", "title": request.title}

@app.delete("/notebooks/{notebook_id}")
async def delete_notebook(notebook_id: str):
    from bson import ObjectId
    try:
        result = await db.notebooks.delete_one({"_id": ObjectId(notebook_id)})
    except:
        result = await db.notebooks.delete_one({"_id": notebook_id})
    return {"status": "ok"}

class SourceItem(BaseModel):
    name: str
    type: str
    status: str
    content: Optional[str] = None

@app.post("/notebooks/{notebook_id}/sources")
async def add_source(notebook_id: str, source: SourceItem):
    """Add a source to the notebook."""
    
    # Process text sources immediately
    if source.type == 'text' and source.content:
        try:
            rag.process_document(notebook_id, "", source.content, source.type, source.name)
            source.status = 'ready'
        except Exception as e:
            print(f"Error indexing text source: {e}")
            source.status = 'error'

    from bson import ObjectId
    try:
        result = await db.notebooks.update_one(
            {"_id": ObjectId(notebook_id)},
            {
                "$push": {"sources": source.dict()},
                "$inc": {"source_count": 1}
            }
        )
    except:
        result = await db.notebooks.update_one(
            {"_id": notebook_id},
            {
                "$push": {"sources": source.dict()},
                "$inc": {"source_count": 1}
            }
        )
    return {"status": "ok"}

@app.put("/notebooks/{notebook_id}/sources/{source_name}/status")
async def update_source_status(notebook_id: str, source_name: str, status: str = Form(...)):
    """Update source status."""
    from bson import ObjectId
    try:
        await db.notebooks.update_one(
            {"_id": ObjectId(notebook_id), "sources.name": source_name},
            {"$set": {"sources.$.status": status}}
        )
    except:
        await db.notebooks.update_one(
            {"_id": notebook_id, "sources.name": source_name},
            {"$set": {"sources.$.status": status}}
        )
    return {"status": "ok"}

@app.delete("/notebooks/{notebook_id}/sources/{source_name:path}")
async def delete_source(notebook_id: str, source_name: str):
    """Remove a source from the notebook."""
    from bson import ObjectId
    try:

        await db.notebooks.update_one(
            {"_id": ObjectId(notebook_id)},
            {
                "$pull": {"sources": {"name": source_name}},
                "$inc": {"source_count": -1}
            }
        )
    except:
         await db.notebooks.update_one(
            {"_id": notebook_id},
            {
                 "$pull": {"sources": {"name": source_name}},
                 "$inc": {"source_count": -1}
            }
        )
    

    rag.delete_source_documents(notebook_id, source_name)
    
    return {"status": "ok"}



class MessageItem(BaseModel):
    role: str
    content: str

@app.post("/notebooks/{notebook_id}/messages")
async def add_message(notebook_id: str, message: MessageItem):
    """Add a message to the notebook."""
    from bson import ObjectId
    try:
        await db.notebooks.update_one(
            {"_id": ObjectId(notebook_id)},
            {"$push": {"messages": message.dict()}}
        )
    except:
        await db.notebooks.update_one(
            {"_id": notebook_id},
            {"$push": {"messages": message.dict()}}
        )
    return {"status": "ok"}

@app.put("/notebooks/{notebook_id}/messages")
async def update_messages(notebook_id: str, messages: List[MessageItem]):
    """Replace all messages in the notebook."""
    from bson import ObjectId
    try:
        await db.notebooks.update_one(
            {"_id": ObjectId(notebook_id)},
            {"$set": {"messages": [m.dict() for m in messages]}}
        )
    except:
        await db.notebooks.update_one(
            {"_id": notebook_id},
            {"$set": {"messages": [m.dict() for m in messages]}}
        )
    return {"status": "ok"}


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

@app.post("/auth/register")
async def register_user(request: RegisterRequest):
    import bcrypt
    

    existing_user = await db.users.find_one({"email": request.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password with bcrypt
    password_hash = bcrypt.hashpw(request.password.encode(), bcrypt.gensalt(12)).decode()
    
    new_user = {
        "name": request.name,
        "email": request.email,
        "password": password_hash,
        "emailVerified": None,
        "image": None
    }
    
    result = await db.users.insert_one(new_user)
    return {"id": str(result.inserted_id), "name": request.name, "email": request.email}

@app.get("/stats")
async def get_stats():
    # 1. Totals (Notebooks)
    notebook_count = await db.notebooks.count_documents({})
    
    # 2. Count sources & messages aggregation
    # We'll do a single pass to get totals and history approximation
    pipeline = [
        {
            "$project": {
                "date": { "$dateToString": { "format": "%Y-%m-%d", "date": { "$toDate": "$_id" } } },
                "s_count": { "$size": { "$ifNull": ["$sources", []] } },
                "m_count": { "$size": { "$ifNull": ["$messages", []] } },
                "assistant_m_count": {
                    "$size": {
                        "$filter": {
                            "input": { "$ifNull": ["$messages", []] },
                            "as": "m",
                            "cond": { "$eq": ["$$m.role", "assistant"] }
                        }
                    }
                }
            }
        },
        {
            "$group": {
                "_id": "$date",
                "notebooks": { "$sum": 1 },
                "sources": { "$sum": "$s_count" },
                "messages": { "$sum": "$m_count" },
                "api_requests": { "$sum": "$assistant_m_count" }
            }
        },
        { "$sort": { "_id": 1 } }
    ]
    
    history_data = []
    try:
        history_data = await db.notebooks.aggregate(pipeline).to_list(100)
    except Exception as e:
        print(f"Stats aggregation error: {e}")

    # Compute totals from history aggregation OR fallback
    if history_data:
        total_sources = sum(d["sources"] for d in history_data)
        total_messages = sum(d["messages"] for d in history_data)
        total_api_requests = sum(d["api_requests"] for d in history_data)
    else:
        # Fallback totals if aggregation failed
        # Just use separate simple counts
        s_res = await db.notebooks.aggregate([{"$group": {"_id": None, "c": {"$sum": {"$size": {"$ifNull": ["$sources", []]}}}}} ]).to_list(1)
        total_sources = s_res[0]["c"] if s_res else 0
        total_api_requests = 0 # Difficult to count without unwind
        total_messages = 0

    # Fallback History if empty but we have notebooks (e.g. non-ObjectId IDs)
    if not history_data and notebook_count > 0:
        from datetime import datetime
        history_data = [{
            "_id": datetime.now().strftime("%Y-%m-%d"),
            "notebooks": notebook_count,
            "sources": total_sources,
            "api_requests": total_api_requests
        }]

    # Ensure at least 2 points for Line Chart aesthetics
    if len(history_data) == 1:
        history_data.insert(0, {
            "_id": "Start",
            "notebooks": 0,
            "sources": 0,
            "api_requests": 0
        })

    # Format history for frontend
    # history: { labels: [dates], notebooks: [counts], sources: [counts], ... }
    labels = [str(d.get("_id") or "Unknown") for d in history_data]
    
    # 4. Storage Used
    storage_bytes = 0
    uploads_dir = Path("uploads")
    if uploads_dir.exists():
        for f in uploads_dir.glob("**/*"):
            if f.is_file():
                storage_bytes += f.stat().st_size
            
    return {
        "notebooks": notebook_count,
        "sources": total_sources,
        "api_requests": total_api_requests,
        "storage_bytes": storage_bytes,
        "tokens": total_api_requests * 350, # Approximation
        "history": {
            "labels": labels,
            "notebooks": [d["notebooks"] for d in history_data],
            "sources": [d["sources"] for d in history_data],
            "api_requests": [d["api_requests"] for d in history_data]
        }
    }

class UpdateProfileRequest(BaseModel):
    email: str
    name: Optional[str] = None

@app.put("/auth/profile")
async def update_profile(request: UpdateProfileRequest):
    update_data = {}
    if request.name:
        update_data["name"] = request.name
        
    if not update_data:
        return {"status": "no changes"}
        
    result = await db.users.update_one(
        {"email": request.email},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
        
    return {"status": "ok"}

# Password Management
class ChangePasswordRequest(BaseModel):
    email: str
    current_password: str
    new_password: str

@app.post("/auth/password")
async def change_password(request: ChangePasswordRequest):
    import bcrypt
    
    user = await db.users.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify current password with bcrypt
    if not bcrypt.checkpw(request.current_password.encode(), user.get("password", "").encode()):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    
    # Hash new password with bcrypt
    new_hash = bcrypt.hashpw(request.new_password.encode(), bcrypt.gensalt(12)).decode()
    await db.users.update_one({"email": request.email}, {"$set": {"password": new_hash}})
    
    return {"status": "ok"}

# API Keys
class CreateApiKeyRequest(BaseModel):
    email: str
    name: str

@app.get("/auth/api-keys")
async def list_api_keys(email: str):
    keys = await db.api_keys.find({"user_email": email}).to_list(length=100)
    return {"keys": [{"id": str(k["_id"]), "name": k["name"], "created_at": k.get("created_at"), "prefix": k["key"][:8] + "..."} for k in keys]}

@app.post("/auth/api-keys")
async def create_api_key(request: CreateApiKeyRequest):
    from datetime import datetime
    key = f"sk-{uuid.uuid4().hex}"
    
    new_key = {
        "user_email": request.email,
        "name": request.name,
        "key": key,
        "created_at": datetime.utcnow()
    }
    
    result = await db.api_keys.insert_one(new_key)
    return {"status": "ok", "key": key, "id": str(result.inserted_id)}

@app.delete("/auth/api-keys/{key_id}")
async def delete_api_key(key_id: str):
    from bson import ObjectId
    await db.api_keys.delete_one({"_id": ObjectId(key_id)})
    return {"status": "ok"}

# Webhooks
class CreateWebhookRequest(BaseModel):
    email: str
    url: str
    events: List[str]

@app.get("/auth/webhooks")
async def list_webhooks(email: str):
    hooks = await db.webhooks.find({"user_email": email}).to_list(length=100)
    return {"webhooks": [{"id": str(h["_id"]), "url": h["url"], "events": h["events"]} for h in hooks]}

@app.post("/auth/webhooks")
async def create_webhook(request: CreateWebhookRequest):
    from datetime import datetime
    new_hook = {
        "user_email": request.email,
        "url": request.url,
        "events": request.events,
        "created_at": datetime.utcnow()
    }
    result = await db.webhooks.insert_one(new_hook)
    return {"status": "ok", "id": str(result.inserted_id)}

@app.delete("/auth/webhooks/{hook_id}")
async def delete_webhook(hook_id: str):
    from bson import ObjectId
    await db.webhooks.delete_one({"_id": ObjectId(hook_id)})
    return {"status": "ok"}

@app.get("/health")
def health():
    return {"status": "ok"}


# Settings Endpoints
@app.get("/settings/models")
async def list_available_models():
    """List all available models from Ollama."""
    try:
        # Use the provider registry to get Ollama provider
        registry = rag.get_registry()
        ollama_provider = registry.get_provider("ollama")
        
        # Try to list models via httpx
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{ollama_provider.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models_list = data.get("models", [])
                return {
                    "models": [
                        {
                            "name": m.get("name", str(m)),
                            "size": m.get("size", 0),
                            "modified_at": str(m.get("modified_at", ""))
                        }
                        for m in models_list
                    ]
                }
            else:
                return {"models": []}
    except Exception as e:
        print(f"Error listing Ollama models: {e}")
        # Return empty list instead of error so frontend doesn't break
        return {"models": []}

@app.get("/settings")
async def get_settings():
    """Get current settings including provider configuration."""
    settings = await db.settings.find_one({"_id": "global"})
    
    # Get provider info
    providers = rag.get_available_providers()
    
    if not settings:
        # Return defaults
        return {
            "chat_provider": "ollama",
            "chat_model": "llama3",
            "embedding_provider": "ollama",
            "embedding_model": "nomic-embed-text",
            "providers": providers
        }
    return {
        "chat_provider": settings.get("chat_provider", "ollama"),
        "chat_model": settings.get("chat_model", "llama3"),
        "embedding_provider": settings.get("embedding_provider", "ollama"),
        "embedding_model": settings.get("embedding_model", "nomic-embed-text"),
        "ollama_url": settings.get("ollama_url", "http://ollama:11434"),
        "providers": providers,
        "api_keys_configured": {
            provider: bool(settings.get("api_keys", {}).get(provider))
            for provider in ["openai", "anthropic", "gemini"]
        }
    }


class SettingsRequest(BaseModel):
    chat_provider: str = "ollama"
    chat_model: str = "llama3"
    embedding_provider: str = "ollama"
    embedding_model: str = "nomic-embed-text"
    ollama_url: str = "http://ollama:11434"


@app.post("/settings")
async def update_settings(request: SettingsRequest):
    """Update settings with provider configuration."""
    # Configure Ollama URL if provided
    if request.ollama_url:
        registry = rag.get_registry()
        ollama_provider = registry.get_provider("ollama")
        ollama_provider.base_url = request.ollama_url
    
    # Configure providers in RAG module
    rag.set_chat_provider(request.chat_provider, request.chat_model)
    
    try:
        rag.set_embedding_provider(request.embedding_provider, request.embedding_model)
    except ValueError as e:
        # Provider doesn't support embeddings, fallback to Ollama
        rag.set_embedding_provider("ollama", request.embedding_model)
    
    # Save to database
    await db.settings.update_one(
        {"_id": "global"},
        {"$set": {
            "chat_provider": request.chat_provider,
            "chat_model": request.chat_model,
            "embedding_provider": request.embedding_provider,
            "embedding_model": request.embedding_model,
            "ollama_url": request.ollama_url
        }},
        upsert=True
    )
    
    return {
        "status": "ok",
        "chat_provider": request.chat_provider,
        "chat_model": request.chat_model,
        "embedding_provider": request.embedding_provider,
        "embedding_model": request.embedding_model
    }


class ApiKeyRequest(BaseModel):
    provider: str
    api_key: str


@app.post("/settings/api-keys")
async def set_api_key(request: ApiKeyRequest):
    """Set an API key for a provider."""
    if request.provider not in ["openai", "anthropic", "gemini"]:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {request.provider}")
    
    # Store in database (encrypted in production)
    await db.settings.update_one(
        {"_id": "global"},
        {"$set": {f"api_keys.{request.provider}": request.api_key}},
        upsert=True
    )
    
    # Update provider registry
    registry = rag.get_registry()
    provider = registry.get_provider(request.provider)
    provider.api_key = request.api_key
    
    return {"status": "ok", "provider": request.provider}


@app.delete("/settings/api-keys/{provider}")
async def delete_api_key(provider: str):
    """Remove an API key for a provider."""
    await db.settings.update_one(
        {"_id": "global"},
        {"$unset": {f"api_keys.{provider}": ""}}
    )
    return {"status": "ok"}


@app.get("/providers/health")
async def check_providers_health():
    """Check health of all configured providers."""
    registry = rag.get_registry()
    results = {}
    
    for provider_name in ["ollama", "openai", "gemini", "anthropic"]:
        try:
            provider = registry.get_provider(provider_name)
            results[provider_name] = await provider.health_check()
        except Exception as e:
             results[provider_name] = {
                "status": "error",
                "message": str(e),
                "code": "system_error"
             }
    
    return results


@app.get("/providers")
async def list_providers():
    """List all available AI providers and their capabilities."""
    return rag.get_available_providers()


@app.get("/providers/{provider_name}/models")
async def get_provider_models(provider_name: str):
    """Get available models for a specific provider."""
    try:
        models = await rag.list_provider_models(provider_name)
        return {"models": models}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8008, reload=True)

