from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AppState:
    IMAGE_PATH: str = ""
    VIEW_WIDTH: int = 0
    VIEW_HEIGHT: int = 0
    PAN_SPEED: int = 0
    ZOOM_LEVELS: list[float] = field(default_factory=list)
    zoom_index: int = 0
    FONT_SIZE: int = 0

    x_min: int = 0
    x_max: int = 0
    y_min: int = 0
    y_max: int = 0

    field_width: int = 0
    field_height: int = 0
    raw_field: Any = None
    scalar_field: Any = None
    colored: Any = None
    heatmap_mode: int = 0

    edge_desirability: dict[Any, Any] = field(default_factory=dict)
    edges_from: dict[Any, Any] = field(default_factory=dict)
    grid_nodes: list[Any] = field(default_factory=list)
    grid_edges: list[Any] = field(default_factory=list)
    grid_size: int = 0
    spacing_x: float = 0.0
    spacing_y: float = 0.0
    node_data: dict[Any, Any] = field(default_factory=dict)
    top_seeds: list[Any] = field(default_factory=list)
    DIST_THRESH: int = 0
    active_nodes: set[Any] = field(default_factory=set)
    active_edges: set[Any] = field(default_factory=set)
    tegu_sources: list[Any] = field(default_factory=list)
    total_tegus: int = 0
    tegu_field: Any = None
    tegu_colored: Any = None

    agents: list[Any] = field(default_factory=list)
    new_agents: list[Any] = field(default_factory=list)
    tegus_born: int = 0
    tegus_died: int = 0
