"""Shared type definitions using Pydantic."""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class Reference(BaseModel):
    """Reference to an article or source."""
    id: str
    url: str
    title: str
    text: str
    published_date: Optional[str] = None
    author: Optional[str] = None


class Concept(BaseModel):
    """A concept extracted from text."""
    id: str
    name: str
    type: str  # concept, entity, event, person
    description: str
    references: List[Reference] = []


class Cluster(BaseModel):
    """A cluster of related concepts."""
    id: str
    label: str
    conceptIds: List[str]
    concepts: List[Concept] = []


class GraphNode(BaseModel):
    """A node in the knowledge graph."""
    id: str
    type: str
    position: Dict[str, float]
    data: Dict[str, Any]


class GraphEdge(BaseModel):
    """An edge in the knowledge graph."""
    id: str
    source: str
    target: str
    type: Optional[str] = None
    weight: Optional[float] = None


class GraphData(BaseModel):
    """Complete graph structure."""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    clusters: Optional[List[Cluster]] = None


class Product(BaseModel):
    """Product information for shopping mode."""
    id: str
    name: str
    image_url: Optional[str] = None
    price: Optional[float] = None
    rating: Optional[float] = None
    retailer: Optional[str] = None
    url: Optional[str] = None
    specs: Optional[Dict[str, Any]] = None
    review_summary: Optional[str] = None
    references: List[Reference] = []


class StudyConcept(BaseModel):
    """Concept with study mode metadata."""
    id: str
    name: str
    description: str
    type: str
    level: int  # 1=Beginner, 2=Intermediate, 3=Advanced
    prerequisites: List[str] = []
    learning_path_position: Optional[int] = None
    references: List[Reference] = []

