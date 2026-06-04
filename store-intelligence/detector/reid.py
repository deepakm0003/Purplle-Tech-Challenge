"""
Re-Identification Module for Visitor Matching.

Uses torchreid OSNet model to extract embeddings and match visitors
across multiple visits using cosine similarity.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from datetime import datetime
import threading
import torch
import torch.nn.functional as F
from loguru import logger

# Configure loguru
logger.remove()
logger.add(lambda msg: logging.getLogger(__name__).info(msg.strip()), format="{message}")

try:
    import torchreid
except ImportError:
    torchreid = None
    logger.warning("torchreid not installed, ReID functionality will be limited")


class VisitorEmbedding:
    """Stores embedding and metadata for a visitor."""
    
    def __init__(self, visitor_id: str, embedding: np.ndarray, timestamp: datetime = None):
        """
        Initialize visitor embedding.
        
        Args:
            visitor_id: Unique visitor identifier
            embedding: Feature vector from model
            timestamp: When embedding was created
        """
        self.visitor_id = visitor_id
        self.embedding = embedding
        self.timestamp = timestamp or datetime.utcnow()
        self.match_count = 0
        self.last_matched = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'visitor_id': self.visitor_id,
            'embedding_shape': self.embedding.shape,
            'timestamp': self.timestamp.isoformat(),
            'match_count': self.match_count
        }


class ReIDManager:
    """
    Re-Identification Manager using OSNet embeddings.
    
    Manages visitor embeddings and handles matching of returning visitors
    based on appearance similarity.
    
    Attributes:
        model: Torchreid model (OSNet)
        device: torch device
        embeddings: Dict of visitor_id -> VisitorEmbedding
        similarity_threshold: Threshold for matching (0-1)
        embedding_dim: Dimension of embeddings
    """
    
    def __init__(
        self,
        model_name: str = "osnet_x1_0",
        pretrained: bool = True,
        similarity_threshold: float = 0.7,
        device: Optional[str] = None,
        max_embeddings: int = 10000
    ):
        """
        Initialize ReIDManager.
        
        Args:
            model_name: Torchreid model to use (osnet_x1_0, osnet_x0_5, etc.)
            pretrained: Whether to use pretrained weights
            similarity_threshold: Threshold for visitor matching (0-1)
            device: torch device (auto-detected if None)
            max_embeddings: Maximum embeddings to keep in memory
            
        Raises:
            ImportError: If torchreid not available
            ValueError: If similarity_threshold not in [0, 1]
        """
        if torchreid is None:
            raise ImportError("torchreid required for ReID functionality")
        
        if not 0 <= similarity_threshold <= 1:
            raise ValueError(f"similarity_threshold must be in [0, 1], got {similarity_threshold}")
        
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold
        self.max_embeddings = max_embeddings
        
        # Auto-detect device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        logger.info(
            f"ReIDManager init: model={model_name}, threshold={similarity_threshold}, "
            f"device={self.device}, max_embeddings={max_embeddings}"
        )
        
        # Load model
        self.model = self._load_model(model_name, pretrained)
        self.embedding_dim = 512  # OSNet output dimension
        
        # Storage
        self.embeddings: Dict[str, VisitorEmbedding] = {}
        self.visitor_last_seen: Dict[str, datetime] = {}
        self._lock = threading.RLock()
        
        logger.info("ReIDManager initialized successfully")
    
    def _load_model(self, model_name: str, pretrained: bool):
        """
        Load torchreid model.
        
        Args:
            model_name: Model identifier
            pretrained: Use pretrained weights
            
        Returns:
            Loaded model in eval mode
        """
        try:
            model = torchreid.models.build_model(
                name=model_name,
                num_classes=1000,
                loss='softmax',
                pretrained=pretrained
            )
            
            model.eval()
            model.to(self.device)
            
            logger.info(f"Loaded model {model_name} on {self.device}")
            return model
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise RuntimeError(f"Model loading failed: {e}") from e
    
    def extract_embedding(
        self,
        person_crop: np.ndarray
    ) -> Optional[np.ndarray]:
        """
        Extract embedding from person crop.
        
        Args:
            person_crop: Person image crop (BGR, HxWx3)
            
        Returns:
            Feature vector (embedding) or None if extraction failed
            
        Raises:
            ValueError: If image is invalid
        """
        if person_crop is None or person_crop.size == 0:
            logger.warning("Received empty person crop")
            return None
        
        if not isinstance(person_crop, np.ndarray):
            raise ValueError("person_crop must be ndarray")
        
        if len(person_crop.shape) != 3 or person_crop.shape[2] != 3:
            raise ValueError("person_crop must be HxWx3 BGR image")
        
        try:
            # Preprocess image
            image_tensor = self._preprocess_image(person_crop)
            
            # Extract embedding
            with torch.no_grad():
                embedding = self.model(image_tensor)
                
                # Normalize
                embedding = F.normalize(embedding, p=2, dim=1)
                embedding = embedding.cpu().numpy()[0]
            
            logger.debug(f"Extracted embedding: shape={embedding.shape}")
            return embedding
            
        except Exception as e:
            logger.error(f"Embedding extraction failed: {e}")
            return None
    
    def _preprocess_image(self, image: np.ndarray) -> torch.Tensor:
        """
        Preprocess image for model input.
        
        Args:
            image: BGR image (HxWx3)
            
        Returns:
            Preprocessed tensor (1xCxHxW)
        """
        # Resize to model input size (224x224)
        import cv2
        image = cv2.resize(image, (224, 224))
        
        # Convert BGR to RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Normalize (ImageNet normalization)
        image = image.astype(np.float32) / 255.0
        image = (image - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
        
        # Convert to tensor and add batch dimension
        image_tensor = torch.from_numpy(image).permute(2, 0, 1).unsqueeze(0)
        image_tensor = image_tensor.to(self.device)
        
        return image_tensor
    
    def compute_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Compute cosine similarity between embeddings.
        
        Args:
            embedding1: First feature vector
            embedding2: Second feature vector
            
        Returns:
            Similarity score (0-1)
        """
        if embedding1 is None or embedding2 is None:
            return 0.0
        
        # Ensure same shape
        if embedding1.shape != embedding2.shape:
            return 0.0
        
        # Cosine similarity
        similarity = np.dot(embedding1, embedding2) / (
            np.linalg.norm(embedding1) * np.linalg.norm(embedding2) + 1e-8
        )
        
        # Clamp to [0, 1]
        return float(np.clip(similarity, 0.0, 1.0))
    
    def match_existing_visitor(
        self,
        embedding: np.ndarray,
        top_k: int = 1
    ) -> List[Tuple[str, float]]:
        """
        Match embedding to existing visitors.
        
        Args:
            embedding: Query embedding
            top_k: Return top K matches
            
        Returns:
            List of (visitor_id, similarity) tuples sorted by similarity
        """
        with self._lock:
            if not self.embeddings:
                return []
            
            similarities = []
            
            for visitor_id, visitor_emb in self.embeddings.items():
                similarity = self.compute_similarity(embedding, visitor_emb.embedding)
                similarities.append((visitor_id, similarity))
            
            # Sort by similarity (descending)
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Filter by threshold and return top_k
            results = [
                (vid, sim) for vid, sim in similarities
                if sim >= self.similarity_threshold
            ][:top_k]
            
            logger.debug(f"Matched {len(results)} visitors, top match: {results[0] if results else 'None'}")
            
            return results
    
    def create_new_visitor(
        self,
        embedding: np.ndarray,
        visitor_id: str
    ) -> bool:
        """
        Create new visitor embedding.
        
        Args:
            embedding: Feature vector
            visitor_id: Visitor identifier
            
        Returns:
            True if created, False if ID already exists
        """
        with self._lock:
            if visitor_id in self.embeddings:
                logger.warning(f"Visitor {visitor_id} already exists")
                return False
            
            # Check memory limit
            if len(self.embeddings) >= self.max_embeddings:
                # Remove oldest embedding
                oldest_id = min(
                    self.embeddings.keys(),
                    key=lambda vid: self.embeddings[vid].timestamp
                )
                del self.embeddings[oldest_id]
                logger.info(f"Removed oldest visitor {oldest_id} to stay under limit")
            
            # Add embedding
            self.embeddings[visitor_id] = VisitorEmbedding(visitor_id, embedding)
            self.visitor_last_seen[visitor_id] = datetime.utcnow()
            
            logger.debug(f"Created embedding for visitor {visitor_id}")
            return True
    
    def update_embedding(
        self,
        visitor_id: str,
        embedding: np.ndarray
    ) -> bool:
        """
        Update visitor embedding (e.g., on re-entry).
        
        Args:
            visitor_id: Visitor identifier
            embedding: New feature vector
            
        Returns:
            True if updated, False if visitor not found
        """
        with self._lock:
            if visitor_id not in self.embeddings:
                logger.warning(f"Visitor {visitor_id} not found for update")
                return False
            
            # Average with existing embedding
            old_emb = self.embeddings[visitor_id].embedding
            new_emb = (old_emb + embedding) / 2.0
            new_emb = new_emb / (np.linalg.norm(new_emb) + 1e-8)
            
            self.embeddings[visitor_id].embedding = new_emb
            self.embeddings[visitor_id].timestamp = datetime.utcnow()
            self.embeddings[visitor_id].match_count += 1
            self.embeddings[visitor_id].last_matched = datetime.utcnow()
            
            self.visitor_last_seen[visitor_id] = datetime.utcnow()
            
            logger.debug(f"Updated embedding for visitor {visitor_id}")
            return True
    
    def get_embedding(self, visitor_id: str) -> Optional[np.ndarray]:
        """Get stored embedding for visitor."""
        with self._lock:
            if visitor_id in self.embeddings:
                return self.embeddings[visitor_id].embedding
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get ReID manager statistics."""
        with self._lock:
            return {
                'model_name': self.model_name,
                'device': self.device,
                'stored_embeddings': len(self.embeddings),
                'max_embeddings': self.max_embeddings,
                'similarity_threshold': self.similarity_threshold,
                'embedding_dimension': self.embedding_dim
            }
    
    def reset(self) -> None:
        """Reset all stored embeddings."""
        with self._lock:
            self.embeddings.clear()
            self.visitor_last_seen.clear()
            logger.info("ReID manager reset")


# Backward compatibility
class ReIdentificationEngine:
    """Legacy interface - redirects to ReIDManager."""
    
    def __init__(self):
        """Initialize legacy engine."""
        logger.warning("ReIdentificationEngine is deprecated, use ReIDManager instead")
        self._manager = None
    
    async def get_or_create_visitor_id(self, track_features, store_id):
        """Deprecated method."""
        import uuid
        return f"VIS_{store_id}_{uuid.uuid4().hex[:8]}"

