"""
Gemini API-based embedding engine for semantic similarity matching.
Replaces sentence-transformers with cloud-based embeddings.
"""
import logging
import hashlib
from typing import List, Optional, Dict
import numpy as np
from functools import lru_cache
import google.generativeai as genai

logger = logging.getLogger(__name__)


class GeminiEmbeddingEngine:
    """
    Embedding engine using Google Gemini API for semantic embeddings.
    Much smaller than sentence-transformers (no local models).
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Gemini embedding engine."""
        pass
    
    def initialize(self, api_key: str, model_name: str = "models/gemini-embedding-001"):
        """
        Initialize the Gemini embedding engine.
        
        Args:
            api_key: Google AI API key
            model_name: Gemini embedding model name
        """
        if not self._initialized:
            logger.info(f"Initializing GeminiEmbeddingEngine with model: {model_name}")
            try:
                # Configure Gemini API
                genai.configure(api_key=api_key)
                self.model_name = model_name
                
                # Test the connection
                test_embedding = self._generate_embedding("test")
                self.embedding_dim = len(test_embedding)
                
                self._initialized = True
                logger.info(f"✅ Gemini embedding engine initialized (dim: {self.embedding_dim})")
                
            except Exception as e:
                logger.error(f"Failed to initialize Gemini embedding engine: {e}")
                raise
    
    def _generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding using Gemini API."""
        try:
            logger.debug(f"Generating Gemini embedding for: {text[:100]}...")
            result = genai.embed_content(
                model=self.model_name,
                content=text,
                task_type="retrieval_document"
            )
            embedding = np.array(result['embedding'])
            logger.debug(f"✅ Generated embedding with {len(embedding)} dimensions")
            return embedding
        except Exception as e:
            logger.error(f"❌ Gemini API failed for text '{text[:50]}...': {type(e).__name__}: {e}")
            # Check if it's an API key issue
            if "API_KEY" in str(e).upper() or "AUTHENTICATION" in str(e).upper():
                logger.error("🔑 Gemini API key issue detected. Check GEMINI_API_KEY environment variable.")
            elif "QUOTA" in str(e).upper() or "LIMIT" in str(e).upper():
                logger.error("📊 Gemini API quota/rate limit exceeded.")
            elif "NETWORK" in str(e).upper() or "CONNECTION" in str(e).upper():
                logger.error("🌐 Network connection issue with Gemini API.")
            
            # Return zeros with correct Gemini dimension (3072)
            return np.zeros(self.embedding_dim if hasattr(self, 'embedding_dim') else 3072)
    
    @lru_cache(maxsize=1000)
    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for text with caching.
        
        Args:
            text: Input text to embed
            
        Returns:
            Numpy array of embedding vector
        """
        if not text or not text.strip():
            return np.zeros(self.embedding_dim)
        
        # Clean text
        cleaned_text = self._clean_text(text)
        
        # Generate embedding via API
        return self._generate_embedding(cleaned_text)
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 10) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process at once
            
        Returns:
            List of embedding arrays
        """
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = []
            
            for text in batch:
                embedding = self.generate_embedding(text)
                batch_embeddings.append(embedding)
            
            embeddings.extend(batch_embeddings)
            
            # Small delay to respect rate limits
            import time
            time.sleep(0.1)
        
        return embeddings
    
    def calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings."""
        try:
            # Normalize vectors
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # Calculate cosine similarity
            similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
            
            # Clamp to [0, 1] range
            return max(0.0, min(1.0, similarity))
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for embedding."""
        import re
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep important punctuation
        text = re.sub(r'[^\w\s\.\,\!\?]', ' ', text)
        
        # Truncate to reasonable length (Gemini has token limits)
        words = text.split()
        if len(words) > 200:  # ~800 tokens
            text = ' '.join(words[:200])
        
        return text.strip()
    
    def test_api_connection(self) -> bool:
        """Test if Gemini API is working properly."""
        try:
            logger.info("🧪 Testing Gemini API connection...")
            test_embedding = self._generate_embedding("test connection")
            
            # Check if we got a valid embedding (not all zeros)
            if np.any(test_embedding):
                logger.info("✅ Gemini API connection successful!")
                return True
            else:
                logger.error("❌ Gemini API returned zero embedding - API may be failing")
                return False
                
        except Exception as e:
            logger.error(f"❌ Gemini API connection test failed: {e}")
            return False
    
    def get_cache_info(self) -> Dict:
        """Get embedding cache statistics."""
        return {
            "cache_info": self.generate_embedding.cache_info(),
            "model_name": getattr(self, 'model_name', 'Not initialized'),
            "embedding_dim": getattr(self, 'embedding_dim', 'Unknown'),
            "initialized": self._initialized
        }