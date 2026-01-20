"""
Custom tools for LangChain/LangGraph agents.
Provides tools for searching sources, querying MongoDB, etc.
"""

from typing import List, Optional, Dict, Any
from langchain_core.tools import tool
from langchain_chroma import Chroma


@tool
def search_sources(query: str, notebook_id: str, n_results: int = 5) -> str:
    """
    Search through uploaded sources for relevant information.
    
    Args:
        query: The search query
        notebook_id: The notebook ID to search within
        n_results: Number of results to return
        
    Returns:
        Relevant excerpts from sources with citations.
    """
    # This will be connected to the actual vector store in the RAG chain
    return f"[Tool would search for: {query} in notebook {notebook_id}]"


@tool
def get_source_info(source_name: str, notebook_id: str) -> str:
    """
    Get detailed information about a specific source.
    
    Args:
        source_name: Name of the source file
        notebook_id: The notebook ID
        
    Returns:
        Information about the source including type and summary.
    """
    return f"[Tool would get info for source: {source_name}]"


@tool
def summarize_sources(notebook_id: str) -> str:
    """
    Get a summary of all sources in a notebook.
    
    Args:
        notebook_id: The notebook ID
        
    Returns:
        A summary of all available sources.
    """
    return f"[Tool would summarize sources for notebook: {notebook_id}]"


def get_tools(vectorstore: Optional[Chroma] = None, notebook_id: Optional[str] = None) -> List:
    """
    Get the list of available tools.
    
    Args:
        vectorstore: Optional Chroma vectorstore instance
        notebook_id: Optional notebook context
        
    Returns:
        List of tools for the agent.
    """
    # For now, return the basic tools
    # These can be enhanced based on the vectorstore and context
    return [
        search_sources,
        get_source_info,
        summarize_sources,
    ]


# Advanced tool factory for creating context-aware tools
def create_search_tool(vectorstore: Chroma, notebook_id: str):
    """Create a search tool bound to a specific vectorstore and notebook."""
    
    @tool
    def search_notebook_sources(query: str, n_results: int = 5) -> str:
        """
        Search through the notebook's sources for relevant information.
        
        Args:
            query: The search query
            n_results: Number of results to return
            
        Returns:
            Relevant excerpts from sources with citations.
        """
        results = vectorstore.similarity_search(
            query,
            k=n_results,
            filter={"notebook_id": notebook_id}
        )
        
        if not results:
            return "No relevant information found in the sources."
        
        output = []
        for i, doc in enumerate(results, 1):
            source = doc.metadata.get("source_name", "Unknown")
            output.append(f"[{i}] From {source}:\n{doc.page_content[:500]}...")
        
        return "\n\n".join(output)
    
    return search_notebook_sources
