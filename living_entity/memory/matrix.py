"""
MemoryMatrix - Vector memory with ChromaDB for RAG.
"""

import hashlib
import os
from datetime import datetime
from typing import Optional

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

from pydantic import BaseModel, Field

from living_entity.utils.logging import get_logger


class MemoryEntry(BaseModel):
    """A single memory entry."""
    id: str
    text: str
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str = "unknown"
    importance: float = 0.5
    metadata: dict = Field(default_factory=dict)


class MemorySearchResult(BaseModel):
    """Result from a memory search."""
    entry: MemoryEntry
    distance: float
    relevance: float


class MemoryMatrix:
    """
    Vector memory implementation using ChromaDB.
    
    Features:
    - Automatic vectorization and storage
    - Similarity search with threshold
    - Automatic associative search
    - Persistence to disk
    """
    
    COLLECTION_NAME = "living_entity_memory"
    
    def __init__(
        self,
        persist_path: str = "./memory_db",
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        """
        Initialize the memory matrix.
        
        :param persist_path: Path for persistent storage
        :param embedding_model: Sentence transformer model for embeddings
        """
        self.persist_path = persist_path
        self.embedding_model = embedding_model
        self.logger = get_logger()
        
        if not CHROMADB_AVAILABLE:
            self.logger.warning(
                "ChromaDB not available. Memory will be in-memory only.",
                module="memory"
            )
            self._client = None
            self._collection = None
            self._fallback_memory: list[MemoryEntry] = []
            return
        
        # Ensure directory exists
        os.makedirs(persist_path, exist_ok=True)
        
        # Initialize ChromaDB client with new API
        try:
            # Try new PersistentClient API (chromadb >= 0.4.0)
            self._client = chromadb.PersistentClient(path=persist_path)
        except (TypeError, AttributeError):
            # Fallback to older Client API
            try:
                self._client = chromadb.Client(chromadb.Settings(
                    persist_directory=persist_path,
                    anonymized_telemetry=False,
                ))
            except Exception:
                # Final fallback - ephemeral client
                self._client = chromadb.Client()
        
        # Get or create collection
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Daily cleanup tracking
        self._last_cleanup: Optional[datetime] = None
        self._cleanup_interval_hours: int = 24  # Cleanup every 24 hours
        self._max_memories_before_cleanup: int = 1000  # Max memories before forced cleanup
        
        self.logger.memory(f"Initialized memory at {persist_path}")
    
    def check_and_cleanup(self) -> bool:
        """
        Check if daily cleanup is needed and perform it.
        
        Removes old, low-importance memories that are not foundational.
        
        :return: True if cleanup was performed
        """
        now = datetime.now()
        
        # Check if cleanup is needed
        needs_cleanup = False
        
        if self._last_cleanup is None:
            # First run - check memory count
            if self.count() > self._max_memories_before_cleanup:
                needs_cleanup = True
        else:
            # Check if 24 hours passed
            hours_since_cleanup = (now - self._last_cleanup).total_seconds() / 3600
            if hours_since_cleanup >= self._cleanup_interval_hours:
                needs_cleanup = True
        
        if not needs_cleanup:
            return False
        
        self.logger.info("Starting daily memory cleanup...", module="memory")
        self._perform_cleanup()
        self._last_cleanup = now
        return True
    
    def _perform_cleanup(self) -> None:
        """
        Perform memory cleanup - remove old, low-importance memories.
        
        Keeps:
        - Foundational (personality) memories
        - High importance memories (importance >= 0.7)
        - Recent memories (last 7 days)
        """
        if self._collection is None:
            # Fallback cleanup
            now = datetime.now()
            week_ago = now.replace(day=now.day - 7) if now.day > 7 else now
            
            self._fallback_memory = [
                m for m in self._fallback_memory
                if (m.source == "personality" or 
                    m.metadata.get("type") == "foundational" or
                    m.importance >= 0.7 or
                    m.timestamp > week_ago)
            ]
            self.logger.info(f"Cleanup complete. Remaining: {len(self._fallback_memory)} memories", module="memory")
            return
        
        try:
            # Get all memories
            all_memories = self.get_all_memories(limit=2000)
            now = datetime.now()
            week_ago = now.replace(day=now.day - 7) if now.day > 7 else now
            
            memories_to_delete = []
            
            for memory in all_memories:
                # Keep foundational memories
                if memory.source == "personality":
                    continue
                if memory.metadata.get("type") == "foundational":
                    continue
                    
                # Keep high importance
                if memory.importance >= 0.7:
                    continue
                    
                # Keep recent (last 7 days)
                if memory.timestamp > week_ago:
                    continue
                
                # Mark for deletion
                memories_to_delete.append(memory.id)
            
            # Delete old memories
            if memories_to_delete:
                for memory_id in memories_to_delete:
                    self._collection.delete(ids=[memory_id])
                
                self.logger.info(
                    f"Cleanup complete. Removed {len(memories_to_delete)} old memories. Remaining: {self.count()}",
                    module="memory"
                )
            else:
                self.logger.info("Cleanup complete. No memories needed removal.", module="memory")
                
        except Exception as e:
            self.logger.error(f"Memory cleanup failed: {e}", module="memory")
    
    def _generate_id(self, text: str) -> str:
        """Generate a unique ID for a memory entry."""
        timestamp = datetime.now().isoformat()
        content = f"{timestamp}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def save_memory(
        self,
        text: str,
        source: str = "unknown",
        importance: float = 0.5,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Save a memory to the vector database.
        Automatically prevents duplicates by checking similarity.
        
        :param text: Text content to remember
        :param source: Source of the memory (e.g., "user", "spirit", "brain")
        :param importance: Importance score (0.0-1.0)
        :param metadata: Additional metadata
        :return: Memory ID (empty string if duplicate was skipped)
        """
        # Check for duplicates first (text similarity > 0.9)
        if self._collection is not None:
            try:
                existing = self._collection.query(
                    query_texts=[text],
                    n_results=1,
                )
                if existing["distances"] and existing["distances"][0]:
                    distance = existing["distances"][0][0]
                    similarity = 1.0 - (distance / 2.0)
                    if similarity > 0.9:
                        # Very similar memory exists, skip
                        self.logger.debug(f"Duplicate memory skipped: {text[:30]}... (similarity: {similarity:.2f})", module="memory")
                        return ""
            except Exception as e:
                self.logger.debug(f"Duplicate check failed: {e}", module="memory")
        
        memory_id = self._generate_id(text)
        entry = MemoryEntry(
            id=memory_id,
            text=text,
            source=source,
            importance=importance,
            metadata=metadata or {},
        )
        
        if self._collection is None:
            # Fallback to in-memory storage with deduplication
            for existing in self._fallback_memory:
                if existing.text.lower() == text.lower():
                    return ""  # Skip duplicate
            self._fallback_memory.append(entry)
            self.logger.memory(f"Saved memory (fallback): {text[:50]}...")
            return memory_id
        
        # Prepare metadata for ChromaDB
        chroma_metadata = {
            "source": source,
            "importance": importance,
            "timestamp": entry.timestamp.isoformat(),
            **{k: str(v) for k, v in (metadata or {}).items()}
        }
        
        # Add to collection
        self._collection.add(
            ids=[memory_id],
            documents=[text],
            metadatas=[chroma_metadata],
        )
        
        self.logger.memory(f"Saved memory: {text[:50]}...")
        return memory_id
    
    def retrieve(
        self,
        query: str,
        threshold: float = 0.7,
        max_results: int = 5,
    ) -> list[MemorySearchResult]:
        """
        Search for similar memories.
        
        :param query: Search query
        :param threshold: Minimum relevance threshold (0.0-1.0)
        :param max_results: Maximum number of results
        :return: List of matching memories with relevance scores
        """
        if self._collection is None:
            # Fallback: simple substring matching
            results = []
            query_lower = query.lower()
            for entry in self._fallback_memory:
                if query_lower in entry.text.lower():
                    results.append(MemorySearchResult(
                        entry=entry,
                        distance=0.5,
                        relevance=0.8,
                    ))
            return results[:max_results]
        
        # Query ChromaDB
        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=max_results,
            )
        except Exception as e:
            self.logger.error(f"Memory search failed: {e}", module="memory")
            return []
        
        if not results["ids"] or not results["ids"][0]:
            return []
        
        # Convert to MemorySearchResult
        search_results = []
        for i, doc_id in enumerate(results["ids"][0]):
            document = results["documents"][0][i] if results["documents"] else ""
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            distance = results["distances"][0][i] if results["distances"] else 0.0
            
            # Convert distance to relevance (assuming cosine distance)
            # Cosine distance ranges from 0 (identical) to 2 (opposite)
            relevance = 1.0 - (distance / 2.0)
            
            if relevance < threshold:
                continue
            
            entry = MemoryEntry(
                id=doc_id,
                text=document,
                source=metadata.get("source", "unknown"),
                importance=float(metadata.get("importance", 0.5)),
                timestamp=datetime.fromisoformat(metadata["timestamp"]) 
                    if "timestamp" in metadata else datetime.now(),
                metadata={k: v for k, v in metadata.items() 
                         if k not in ["source", "importance", "timestamp"]},
            )
            
            search_results.append(MemorySearchResult(
                entry=entry,
                distance=distance,
                relevance=relevance,
            ))
        
        return search_results
    
    def auto_associative_search(
        self,
        context: str,
        max_results: int = 3,
    ) -> list[MemorySearchResult]:
        """
        Automatic associative search based on current context.
        
        Extracts key concepts from context and retrieves related memories.
        
        :param context: Current context text
        :param max_results: Maximum number of results
        :return: List of associated memories
        """
        # For automatic search, use a lower threshold
        return self.retrieve(
            query=context,
            threshold=0.5,
            max_results=max_results,
        )
    
    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory by ID.
        
        :param memory_id: Memory ID to delete
        :return: True if deleted, False otherwise
        """
        if self._collection is None:
            self._fallback_memory = [
                m for m in self._fallback_memory if m.id != memory_id
            ]
            return True
        
        try:
            self._collection.delete(ids=[memory_id])
            self.logger.memory(f"Deleted memory: {memory_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete memory: {e}", module="memory")
            return False
    
    def get_all_memories(self, limit: int = 100) -> list[MemoryEntry]:
        """
        Get all memories (up to limit).
        
        :param limit: Maximum number of memories to return
        :return: List of memory entries
        """
        if self._collection is None:
            return self._fallback_memory[:limit]
        
        try:
            results = self._collection.get(limit=limit)
        except Exception as e:
            self.logger.error(f"Failed to get memories: {e}", module="memory")
            return []
        
        entries = []
        for i, doc_id in enumerate(results["ids"]):
            document = results["documents"][i] if results["documents"] else ""
            metadata = results["metadatas"][i] if results["metadatas"] else {}
            
            entries.append(MemoryEntry(
                id=doc_id,
                text=document,
                source=metadata.get("source", "unknown"),
                importance=float(metadata.get("importance", 0.5)),
                timestamp=datetime.fromisoformat(metadata["timestamp"])
                    if "timestamp" in metadata else datetime.now(),
                metadata={k: v for k, v in metadata.items()
                         if k not in ["source", "importance", "timestamp"]},
            ))
        
        return entries
    
    def count(self) -> int:
        """Get the total number of memories."""
        if self._collection is None:
            return len(self._fallback_memory)
        
        try:
            return self._collection.count()
        except Exception:
            return 0
    
    def clear(self) -> None:
        """Clear all memories."""
        if self._collection is None:
            self._fallback_memory.clear()
            return
        
        try:
            # Delete and recreate collection
            self._client.delete_collection(self.COLLECTION_NAME)
            self._collection = self._client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
            self.logger.memory("Cleared all memories")
        except Exception as e:
            self.logger.error(f"Failed to clear memories: {e}", module="memory")
    
    def persist(self) -> None:
        """Persist changes to disk (automatic in new ChromaDB API)."""
        if self._client is not None:
            # New PersistentClient auto-persists, but try persist() for older versions
            if hasattr(self._client, 'persist'):
                try:
                    self._client.persist()
                    self.logger.memory("Persisted memory to disk")
                except Exception as e:
                    self.logger.debug(f"Persist not needed: {e}", module="memory")
            else:
                self.logger.memory("Memory auto-persisted (PersistentClient)")
