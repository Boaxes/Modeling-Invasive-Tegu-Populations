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

    img: Any = None
    img_width: int = 0
    img_height: int = 0
    image_surface: Any = None
    PREVIEW_WIDTH: int = 0
    PREVIEW_HEIGHT: int = 0
    preview_surface: Any = None

    field_width: int = 0
    field_height: int = 0
    raw_field: Any = None
    scalar_field: Any = None
    cmap: Any = None
    colored: Any = None
    scalar_surface: Any = None
    heatmap_mode: int = 0

    edge_desirability: dict[Any, Any] = field(default_factory=dict)
    grid_nodes: list[Any] = field(default_factory=list)
    grid_edges: list[Any] = field(default_factory=list)
    grid_size: int = 0
    spacing_x: float = 0.0
    spacing_y: float = 0.0
    node_data: dict[Any, Any] = field(default_factory=dict)
    used_quadrants: set[Any] = field(default_factory=set)
    top_seeds: list[Any] = field(default_factory=list)
    DIST_THRESH: int = 0
    active_nodes: set[Any] = field(default_factory=set)
    active_edges: set[Any] = field(default_factory=set)
    tegu_sources: list[Any] = field(default_factory=list)
    total_tegus: int = 0
    tegu_field: Any = None
    tegu_colored: Any = None
    tegu_surface: Any = None

    screen: Any = None
    clock: Any = None
    font: Any = None
    x_offset: float = 0.0
    y_offset: float = 0.0
    cached_view: Any = None
    cached_zoom: Any = None
    cached_offset: Any = None
    needs_redraw: bool = True
    selected_node: Any = None

    timestep: int = 0
    used_edges: set[Any] = field(default_factory=set)
    used_nodes: set[Any] = field(default_factory=set)
    FRAME_DIR: str = ""
    agents: list[Any] = field(default_factory=list)
    new_agents: list[Any] = field(default_factory=list)
    previous_agents: list[Any] = field(default_factory=list)
    tegus_born: int = 0
    tegus_died: int = 0
