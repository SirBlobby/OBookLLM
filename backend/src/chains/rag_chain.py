"""
RAG Chain using LangChain.
Provides improved retrieval and generation with citations.
"""

import os
from typing import List, Dict, Any, Optional, AsyncGenerator, Tuple
from dataclasses import dataclass

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..providers.registry import get_registry


@dataclass
class CitationInfo:
    """Information about a citation."""
    id: int
    source_name: str
    excerpts: List[str]


class RAGChain:
    """
    RAG Chain that uses LangChain for improved retrieval and generation.
    Supports multiple providers and maintains citation tracking.
    """
    
    SYSTEM_PROMPT = """You are a helpful AI assistant. Answer the user's question using ONLY the provided context.

STRICT CITATION RULES:
- The context below contains data from sources marked with IDs like [1], [2].
- You must cite every statement using the corresponding [ID].
- Look for `--- BEGIN SOURCE [ID] ---`. Content from that block MUST be cited as [ID].
- NEVER write the source name or filename in your text.
- INCORRECT: "According to video.mp3 [1], vectors are arrows."
- CORRECT: "Vectors are defined as arrows in space [1]."

FORMATTING RULES:
- Use Markdown formatting.
- Use **bold** for key concepts.
- Use bullet points for lists.
- Keep output clean and professional.

Context with Citation IDs:
{context}

Remember: [1], [2] only. No filenames."""

    def __init__(
        self,
        chroma_host: str = "localhost",
        chroma_port: int = 8000,
        collection_name: str = "notebook_docs"
    ):
        self.registry = get_registry()
        self.collection_name = collection_name
        
        # Initialize ChromaDB with LangChain
        self._vectorstore: Optional[Chroma] = None
        self._chroma_host = chroma_host
        self._chroma_port = chroma_port
        
        # Text splitter for document processing
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len,
        )
    
    def _get_vectorstore(self) -> Chroma:
        """Get or create the Chroma vectorstore."""
        if self._vectorstore is None:
            import chromadb
            
            # Get embedding function from provider
            embedding_provider = self.registry.get_embedding_provider()
            embeddings = embedding_provider.get_embeddings()
            
            # Connect to ChromaDB
            chroma_client = chromadb.HttpClient(
                host=self._chroma_host,
                port=self._chroma_port
            )
            
            self._vectorstore = Chroma(
                client=chroma_client,
                collection_name=self.collection_name,
                embedding_function=embeddings,
            )
        
        return self._vectorstore
    
    def add_documents(
        self,
        notebook_id: str,
        source_name: str,
        source_type: str,
        content: str
    ) -> int:
        """
        Add documents to the vector store.
        
        Args:
            notebook_id: The notebook ID
            source_name: Name of the source
            source_type: Type of source (pdf, audio, text)
            content: The text content
            
        Returns:
            Number of chunks added.
        """
        # Split content into chunks
        chunks = self.text_splitter.split_text(content)
        
        # Create Document objects with metadata
        documents = []
        ids = []
        for i, chunk in enumerate(chunks):
            doc = Document(
                page_content=chunk,
                metadata={
                    "notebook_id": notebook_id,
                    "source_name": source_name,
                    "source_type": source_type,
                    "chunk_index": i,
                }
            )
            documents.append(doc)
            ids.append(f"{notebook_id}_{source_name}_{i}")
        
        # Add to vectorstore
        vectorstore = self._get_vectorstore()
        vectorstore.add_documents(documents, ids=ids)
        
        return len(documents)
    
    def delete_source(self, notebook_id: str, source_name: str):
        """Delete all documents for a source."""
        vectorstore = self._get_vectorstore()
        
        # ChromaDB delete with filter
        vectorstore._collection.delete(
            where={
                "$and": [
                    {"notebook_id": notebook_id},
                    {"source_name": source_name}
                ]
            }
        )
    
    def retrieve_context(
        self,
        notebook_id: str,
        query: str,
        selected_sources: Optional[List[str]] = None,
        n_results: int = 5
    ) -> Tuple[str, Dict[int, CitationInfo]]:
        """
        Retrieve relevant context for a query.
        
        Args:
            notebook_id: The notebook ID
            query: The user's query
            selected_sources: Optional list of source names to filter by
            n_results: Number of documents to retrieve
            
        Returns:
            Tuple of (formatted context string, citation info dict)
        """
        vectorstore = self._get_vectorstore()
        
        # Build filter
        filter_dict = {"notebook_id": notebook_id}
        if selected_sources:
            filter_dict = {
                "$and": [
                    {"notebook_id": notebook_id},
                    {"source_name": {"$in": selected_sources}}
                ]
            }
        
        if selected_sources and len(selected_sources) <= 5:
            # Balanced Retrieval Strategy
            # When specific sources are selected, ensure we get context from EACH of them.
            # This prevents one document from dominating the 'k' results.
            results = []
            per_source_k = max(3, int(n_results / len(selected_sources)) + 1)
            
            
            for source in selected_sources:
                source_filter = {
                    "$and": [
                        {"notebook_id": notebook_id},
                        {"source_name": source}
                    ]
                }
                try:
                    source_docs = vectorstore.similarity_search(
                        query,
                        k=per_source_k,
                        filter=source_filter
                    )
                    results.extend(source_docs)
                except Exception as e:
                    print(f"Error retrieving for source {source}: {e}")
        else:
            # Standard Global Retrieval
            # Used when no specific sources selected (search all) or too many sources selected.
            results = vectorstore.similarity_search(
                query,
                k=n_results,
                filter=filter_dict
            )
        
        
        # Build context and citations
        context_parts = []
        source_map: Dict[str, int] = {}  # source_name -> citation_id
        citation_info: Dict[int, CitationInfo] = {}
        citation_counter = 1
        
        for doc in results:
            source_name = doc.metadata.get("source_name", "Unknown")
            
            # Assign citation ID
            if source_name not in source_map:
                source_map[source_name] = citation_counter
                citation_info[citation_counter] = CitationInfo(
                    id=citation_counter,
                    source_name=source_name,
                    excerpts=[]
                )
                citation_counter += 1
            
            cid = source_map[source_name]
            
            # Add excerpt to citation
            excerpt = doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content
            citation_info[cid].excerpts.append(excerpt)
            
            # Format context
            context_parts.append(
                f"--- BEGIN SOURCE [{cid}] ({source_name}) ---\n"
                f"{doc.page_content}\n"
                f"--- END SOURCE [{cid}] ---"
            )
        
        context = "\n\n".join(context_parts)
        return context, citation_info
    
    async def stream_response(
        self,
        notebook_id: str,
        messages: List[Dict[str, str]],
        selected_sources: Optional[List[str]] = None,
        full_source_content: Optional[List[Dict[str, str]]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream a RAG response.
        
        Args:
            notebook_id: The notebook ID
            messages: List of message dicts
            selected_sources: Optional list of source names to filter by
            full_source_content: Optional list of {name, content} for full context mode
            
        Yields:
            Text chunks as they are generated.
        """
        # Get the user's latest message
        user_message = messages[-1]["content"]
        
        citation_info = {}
        
        if full_source_content:
            # Full Context Mode
            # Full Context Mode
            context_parts = []
            for i, src in enumerate(full_source_content):
                cid = i + 1
                content = src.get('content', '')
                name = src.get('name', 'Unknown')
                
                context_parts.append(
                    f"--- BEGIN SOURCE [{cid}] ({name}) ---\n"
                    f"{content}\n"
                    f"--- END SOURCE [{cid}] ---"
                )
                
                # Mock citation info for UI
                citation_info[cid] = CitationInfo(
                    id=cid, 
                    source_name=name, 
                    excerpts=["(Full document context used)"]
                )
            context = "\n\n".join(context_parts)
        else:
            # Retrieve context via RAG
            context, citation_info = self.retrieve_context(
                notebook_id,
                user_message,
                selected_sources,
                n_results=10
            )
        
        # Build messages for the model
        system_prompt = self.SYSTEM_PROMPT.format(context=context)
        
        augmented_messages = [
            {"role": "system", "content": system_prompt}
        ] + messages
        
        # Get chat provider and stream
        chat_provider = self.registry.get_chat_provider()
        
        async for chunk in chat_provider.stream_chat(augmented_messages):
            yield chunk
        
        # Yield citation data at the end
        if citation_info:
            import json
            citation_data = {
                str(cid): {
                    "name": info.source_name,
                    "excerpts": info.excerpts
                }
                for cid, info in citation_info.items()
            }
            yield "\n\n---CITATIONS---\n"
            yield json.dumps(citation_data)
    
    def get_chain(self):
        """
        Get a LangChain LCEL chain for RAG.
        This can be used with LangGraph for more complex workflows.
        """
        # Get chat model from provider
        chat_provider = self.registry.get_chat_provider()
        llm = chat_provider.get_chat_model()
        
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="messages"),
        ])
        
        # Build chain
        chain = prompt | llm | StrOutputParser()
        
        return chain


def create_rag_chain(
    chroma_host: str = "localhost",
    chroma_port: int = 8000,
) -> RAGChain:
    """Factory function to create a RAG chain."""
    return RAGChain(
        chroma_host=chroma_host,
        chroma_port=chroma_port,
    )
