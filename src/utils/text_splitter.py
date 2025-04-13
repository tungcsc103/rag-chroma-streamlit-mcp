from typing import List, Dict, Optional
import re
from langchain.text_splitter import RecursiveCharacterTextSplitter

class TextChunker:
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        length_function: callable = len,
        separators: List[str] = None
    ):
        """
        Initialize the text chunker with configurable parameters.
        
        Args:
            chunk_size: Maximum size of each chunk
            chunk_overlap: Number of characters to overlap between chunks
            length_function: Function to measure text length
            separators: List of separators to use for splitting, in order of preference
        """
        if separators is None:
            separators = ["\n\n", "\n", ". ", " ", ""]
            
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=length_function,
            separators=separators
        )

    def split_text(
        self,
        text: str,
        metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Split text into chunks while preserving metadata and adding chunk information.
        
        Args:
            text: Text content to split
            metadata: Original document metadata
            
        Returns:
            List of dictionaries containing chunks and their metadata
        """
        if metadata is None:
            metadata = {}
            
        # Clean and normalize text
        text = self._normalize_text(text)
        
        # Split text into chunks
        chunks = self.text_splitter.split_text(text)
        
        # Prepare chunks with metadata
        chunk_documents = []
        for i, chunk in enumerate(chunks):
            # Flatten metadata and add chunk information
            chunk_metadata = {}
            
            # Add original metadata with flattened structure
            for key, value in metadata.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, (str, int, float, bool)):
                            chunk_metadata[f"{key}_{sub_key}"] = sub_value
                elif isinstance(value, (str, int, float, bool)):
                    chunk_metadata[key] = value
            
            # Add chunk information
            chunk_metadata.update({
                "chunk_index": i,
                "chunk_total": len(chunks),
                "chunk_is_first": i == 0,
                "chunk_is_last": i == len(chunks) - 1,
                "chunk_length": len(chunk)
            })
            
            chunk_documents.append({
                "text": chunk,
                "metadata": chunk_metadata
            })
            
        return chunk_documents

    def _normalize_text(self, text: str) -> str:
        """
        Clean and normalize text before splitting.
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove excessive newlines while preserving paragraph breaks
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Ensure proper sentence spacing
        text = re.sub(r'([.!?])\s*(\w)', r'\1 \2', text)
        
        return text.strip()

    @staticmethod
    def get_default_params() -> Dict:
        """
        Get default chunking parameters.
        
        Returns:
            Dictionary of default parameters
        """
        return {
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "separators": ["\n\n", "\n", ". ", " ", ""]
        } 