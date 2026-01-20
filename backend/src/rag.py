"""
RAG Module for OBookLLM.
Integrates with the Provider system and LangChain for advanced RAG.
Maintains backward compatibility with existing API.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

import torch
import chromadb
import json
from tqdm import tqdm
from faster_whisper import WhisperModel
from typing import List, Dict, Any, Generator, Optional, Tuple, AsyncGenerator


from .providers.registry import get_registry, ProviderRegistry
from .chains.rag_chain import RAGChain, create_rag_chain


__all__ = ['get_registry', 'get_rag_chain', 'process_document', 'transcribe_audio', 
           'stream_chat_response', 'get_available_providers', 'set_chat_provider',
           'set_embedding_provider', 'list_provider_models', 'delete_source_documents']


CHROMA_HOST = os.getenv("CHROMA_HOST", "chromadb")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8000))


chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
collection = chroma_client.get_or_create_collection(name="notebook_docs")


device = "cuda" if torch.cuda.is_available() else "cpu"
compute_type = "float16" if device == "cuda" else "int8"
whisper_model = None


_rag_chain: Optional[RAGChain] = None


def get_rag_chain() -> RAGChain:
    """Get or create the global RAG chain."""
    global _rag_chain
    if _rag_chain is None:
        _rag_chain = create_rag_chain(
            chroma_host=CHROMA_HOST,
            chroma_port=CHROMA_PORT,
        )
    return _rag_chain


def get_whisper_model():
    """Lazy load Whisper model."""
    global whisper_model
    if whisper_model is None:
        print(f"Loading Whisper model on {device}...")
        whisper_model = WhisperModel("small", device=device, compute_type=compute_type)
    return whisper_model


def get_embeddings(text: str) -> List[float]:
    """
    Generate embeddings using the configured provider.
    Falls back to Ollama if provider not available.
    """
    try:
        registry = get_registry()
        embedding_provider = registry.get_embedding_provider()
        embeddings = embedding_provider.get_embeddings()
        # Use sync embed via run_in_executor or direct call
        return embeddings.embed_query(text)
    except Exception as e:
        print(f"Error generating embeddings via provider: {e}")
        # Fallback to direct Ollama call
        try:
            import ollama
            OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
            client = ollama.Client(host=OLLAMA_HOST)
            response = client.embeddings(model="nomic-embed-text", prompt=text)
            return response["embedding"]
        except Exception as e2:
            print(f"Fallback embedding also failed: {e2}")
            return []


def transcribe_audio(file_path: str) -> str:
    model = get_whisper_model()
    
    # Get audio duration for progress bar
    import subprocess
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
             "-of", "default=noprint_wrappers=1:nokey=1", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        duration = float(result.stdout)
    except:
        duration = None

    segments, info = model.transcribe(file_path, beam_size=5)
    
    formatted_text = ""
    last_pos = 0
    
    with tqdm(total=info.duration, unit="s", desc="Transcribing", 
              bar_format="{l_bar}{bar}| {n:.1f}/{total:.1f}s [{elapsed}<{remaining}]") as pbar:
        for segment in segments:
            start = format_timestamp(segment.start)
            end = format_timestamp(segment.end)
            formatted_text += f"\n[{start} - {end}] {segment.text.strip()}\n"
            pbar.update(segment.end - last_pos)
            last_pos = segment.end
            
    return formatted_text


def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS format."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


def process_document(notebook_id: str, file_path: str, content: str, source_type: str, source_name: str):
    """
    Chunk and store document in ChromaDB.
    Uses the new RAG chain for LangChain-based processing.
    """

    try:
        rag_chain = get_rag_chain()
        num_chunks = rag_chain.add_documents(
            notebook_id=notebook_id,
            source_name=source_name,
            source_type=source_type,
            content=content
        )
        print(f"Processed {num_chunks} chunks for notebook {notebook_id}")
    except Exception as e:
        print(f"Error processing with RAG chain: {e}")
        # Fallback to legacy processing
        _legacy_process_document(notebook_id, file_path, content, source_type, source_name)


def _legacy_process_document(notebook_id: str, file_path: str, content: str, source_type: str, source_name: str):
    """Legacy document processing using direct ChromaDB."""
    chunk_size = 500
    overlap = 50
    chunks = []
    
    for i in range(0, len(content), chunk_size - overlap):
        chunks.append(content[i:i + chunk_size])
        
    print(f"[Legacy] Processing {len(chunks)} chunks for notebook {notebook_id}")
    
    for i, chunk in enumerate(chunks):
        embedding = get_embeddings(chunk)
        if embedding:
            collection.add(
                ids=[f"{notebook_id}_{source_name}_{i}"],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{
                    "notebook_id": notebook_id,
                    "source_name": source_name,
                    "source_type": source_type,
                    "chunk_index": i
                }]
            )


def delete_source_documents(notebook_id: str, source_name: str):
    try:
        rag_chain = get_rag_chain()
        rag_chain.delete_source(notebook_id, source_name)
    except Exception as e:
        print(f"RAG chain delete failed, using legacy: {e}")
        # Fallback to legacy
        try:
            collection.delete(
                where={
                    "$and": [
                        {"notebook_id": notebook_id},
                        {"source_name": source_name}
                    ]
                }
            )
        except Exception as e2:
            print(f"Error deleting document: {e2}")


def query_rag_context(
    notebook_id: str, 
    query: str, 
    n_results: int = 5, 
    selected_sources: List[str] = None
) -> Tuple[str, Dict[str, int], Dict[int, Dict]]:
    """
    Retrieve context relevant to the query for a specific notebook.
    Uses the new RAG chain.
    
    Returns:
        Tuple of (context_string, source_map, citation_details)
    """
    try:
        rag_chain = get_rag_chain()
        context, citation_info = rag_chain.retrieve_context(
            notebook_id=notebook_id,
            query=query,
            selected_sources=selected_sources,
            n_results=n_results
        )
        
        # Convert to legacy format
        source_map = {info.source_name: info.id for info in citation_info.values()}
        citation_details = {
            cid: {
                "name": info.source_name,
                "excerpts": info.excerpts
            }
            for cid, info in citation_info.items()
        }
        
        return context, source_map, citation_details
    except Exception as e:
        print(f"RAG chain query failed, using legacy: {e}")
        return _legacy_query_rag_context(notebook_id, query, n_results, selected_sources)


def _legacy_query_rag_context(
    notebook_id: str, 
    query: str, 
    n_results: int = 5, 
    selected_sources: List[str] = None
) -> Tuple[str, Dict[str, int], Dict[int, Dict]]:
    """Legacy RAG context retrieval."""
    query_vector = get_embeddings(query)
    
    where_filter = {"notebook_id": notebook_id}
    if selected_sources:
        where_filter = {
            "$and": [
                {"notebook_id": notebook_id},
                {"source_name": {"$in": selected_sources}}
            ]
        }

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=n_results,
        where=where_filter
    )
    
    context = ""
    source_map = {}
    citation_details = {}
    source_counter = 1
    
    if results['documents'] and results['metadatas']:
        for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
            source_name = meta.get('source_name', 'Unknown')
            
            if source_name not in source_map:
                source_map[source_name] = source_counter
                citation_details[source_counter] = {
                    "name": source_name,
                    "excerpts": []
                }
                source_counter += 1
            
            citation_num = source_map[source_name]
            excerpt = doc[:300] + "..." if len(doc) > 300 else doc
            citation_details[citation_num]["excerpts"].append(excerpt)
            
            context += f"--- BEGIN SOURCE [{citation_num}] ({source_name}) ---\n{doc}\n--- END SOURCE [{citation_num}] ---\n\n"
    
    return context, source_map, citation_details


async def stream_chat_response(
    notebook_id: str, 
    messages: List[Dict[str, str]], 
    selected_sources: List[str] = None,
    full_source_content: List[Dict[str, str]] = None
) -> AsyncGenerator[str, None]:
    """
    Stream chat response with RAG context.
    Delegates to the RAGChain for better context handling and LangChain compatibility.
    """
    rag_chain = get_rag_chain()
    
    try:
        async for chunk in rag_chain.stream_response(
            notebook_id=notebook_id,
            messages=messages,
            selected_sources=selected_sources,
            full_source_content=full_source_content
        ):
            yield chunk
    except Exception as e:
        print(f"Streaming error: {e}")
        yield f"Error generating response: {str(e)}"




def configure_providers(settings: dict):
    """Configure the provider registry from settings."""
    registry = get_registry()
    registry.configure_from_settings(settings)


def get_available_providers() -> Dict[str, dict]:
    """Get list of available providers with their status."""
    registry = get_registry()
    return registry.list_providers()


def set_chat_provider(provider_name: str, model_name: Optional[str] = None):
    """Set the active chat provider."""
    registry = get_registry()
    registry.set_chat_provider(provider_name, model_name)


def set_embedding_provider(provider_name: str, model_name: Optional[str] = None):
    """Set the active embedding provider."""
    registry = get_registry()
    registry.set_embedding_provider(provider_name, model_name)


async def list_provider_models(provider_name: str) -> List[str]:
    """List available models for a provider."""
    registry = get_registry()
    provider = registry.get_provider(provider_name)
    return await provider.list_models()
