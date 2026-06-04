"""
YOLOv8 Person Detection Module

Handles person detection in video frames using Ultralytics YOLOv8.
Supports both CPU and GPU inference with configurable parameters.
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import numpy as np
from ultralytics import YOLO
import torch
from loguru import logger

# Configure loguru to integrate with standard logging
logger.remove()
logger.add(lambda msg: logging.getLogger(__name__).info(msg.strip()), format="{message}")


@dataclass
class Detection:
    """Detection result with bounding box and confidence."""
    
    bbox: List[float]  # [x1, y1, x2, y2] in pixel coordinates
    confidence: float  # 0.0 to 1.0
    class_id: int = 0  # Class ID (always 0 for person)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert detection to dictionary."""
        return {
            "bbox": self.bbox,
            "confidence": self.confidence,
            "class_id": self.class_id
        }


class PersonDetector:
    """
    YOLOv8 Person Detector.
    
    Detects people in video frames using Ultralytics YOLOv8.
    Supports configurable model size, confidence threshold, and device.
    
    Attributes:
        model_size: Size of model (nano, small, medium, large)
        confidence_threshold: Minimum confidence for detection
        imgsz: Input image size for model
        device: Device to run inference on (cpu, cuda, mps)
    """
    
    VALID_SIZES = {"nano", "small", "medium", "large", "xlarge"}
    PERSON_CLASS_ID = 0
    
    def __init__(
        self,
        model_size: str = "nano",
        confidence_threshold: float = 0.4,
        imgsz: int = 640,
        device: Optional[str] = None,
        half: bool = False
    ):
        """
        Initialize PersonDetector.
        
        Args:
            model_size: YOLOv8 model size (nano, small, medium, large)
            confidence_threshold: Minimum confidence threshold
            imgsz: Input image size
            device: Device for inference (auto, cpu, cuda, mps). None = auto
            half: Use half precision (FP16) for faster inference
            
        Raises:
            ValueError: If model_size is invalid
        """
        if model_size not in self.VALID_SIZES:
            raise ValueError(f"model_size must be one of {self.VALID_SIZES}")
        
        if not 0 <= confidence_threshold <= 1:
            raise ValueError(f"confidence_threshold must be in [0, 1], got {confidence_threshold}")
        
        self.model_size = model_size
        self.confidence_threshold = confidence_threshold
        self.imgsz = imgsz
        self.half = half
        
        # Auto-detect device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        logger.info(
            f"PersonDetector init: model_size={model_size}, device={self.device}, "
            f"confidence_threshold={confidence_threshold}, imgsz={imgsz}, half={half}"
        )
        
        self.model = self._load_model()
        logger.info(f"PersonDetector initialized successfully on {self.device}")
    
    def _load_model(self) -> YOLO:
        """
        Load YOLOv8 model.
        
        Returns:
            Loaded YOLO model
            
        Raises:
            RuntimeError: If model loading fails
        """
        try:
            model_name = f"yolov8{self.model_size[0]}.pt"  # 'n', 's', 'm', 'l', 'x'
            logger.info(f"Loading YOLOv8 model: {model_name}")
            
            model = YOLO(model_name)
            model.to(self.device)
            
            if self.half and self.device != "cpu":
                model.half()
                logger.info("Half precision (FP16) enabled")
            
            logger.info(f"Model {model_name} loaded successfully on {self.device}")
            return model
        except Exception as e:
            logger.error(f"Failed to load YOLOv8 model: {e}")
            raise RuntimeError(f"Model loading failed: {e}") from e
    
    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Detect persons in a single frame.
        
        Args:
            frame: Input image as numpy array (BGR format)
            
        Returns:
            List of Detection objects with bbox and confidence
            
        Raises:
            ValueError: If frame is invalid
            RuntimeError: If detection fails
        """
        if frame is None or not isinstance(frame, np.ndarray):
            raise ValueError("frame must be a valid numpy array")
        
        if len(frame.shape) != 3 or frame.shape[2] != 3:
            raise ValueError("frame must be a 3-channel BGR image")
        
        try:
            # Run inference
            results = self.model(
                frame,
                conf=self.confidence_threshold,
                imgsz=self.imgsz,
                verbose=False
            )
            
            detections = []
            
            # Extract detections
            if results and len(results) > 0:
                result = results[0]
                
                if result.boxes is not None:
                    for box in result.boxes:
                        # Only keep person detections (class_id=0)
                        if int(box.cls[0]) == self.PERSON_CLASS_ID:
                            # Get bounding box [x1, y1, x2, y2]
                            bbox = box.xyxy[0].cpu().numpy().tolist()
                            confidence = float(box.conf[0])
                            
                            detection = Detection(
                                bbox=bbox,
                                confidence=confidence,
                                class_id=self.PERSON_CLASS_ID
                            )
                            detections.append(detection)
            
            logger.debug(f"Detected {len(detections)} persons in frame")
            return detections
            
        except Exception as e:
            logger.error(f"Detection failed: {e}")
            raise RuntimeError(f"Detection failed: {e}") from e
    
    def batch_detect(self, frames: List[np.ndarray]) -> List[List[Detection]]:
        """
        Detect persons in multiple frames.
        
        Args:
            frames: List of input images as numpy arrays
            
        Returns:
            List of detection lists, one per frame
            
        Raises:
            ValueError: If frames list is empty or invalid
        """
        if not frames or not isinstance(frames, list):
            raise ValueError("frames must be a non-empty list")
        
        detections_per_frame = []
        
        for i, frame in enumerate(frames):
            try:
                detections = self.detect(frame)
                detections_per_frame.append(detections)
            except Exception as e:
                logger.warning(f"Detection failed for frame {i}: {e}")
                detections_per_frame.append([])
        
        logger.debug(f"Batch detected {len(frames)} frames")
        return detections_per_frame
    
    def get_device_info(self) -> Dict[str, str]:
        """
        Get device and model information.
        
        Returns:
            Dictionary with device and model details
        """
        return {
            "device": self.device,
            "model_size": self.model_size,
            "model_name": f"yolov8{self.model_size}.pt",
            "half_precision": self.half
        }


def create_detector(
    model_size: str = "nano",
    confidence_threshold: float = 0.4,
    device: Optional[str] = None
) -> PersonDetector:
    """
    Factory function to create PersonDetector.
    
    Args:
        model_size: YOLOv8 model size
        confidence_threshold: Confidence threshold
        device: Device for inference
        
    Returns:
        Configured PersonDetector instance
    """
    return PersonDetector(
        model_size=model_size,
        confidence_threshold=confidence_threshold,
        device=device
    )
