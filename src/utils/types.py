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

