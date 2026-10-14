import type { Font, Surface, time } from "./pygame.js";

// Python tuples become arrays; tuple-keyed dicts/sets use key() strings.
export type Node = [number, number];
export type Edge = [Node, Node];

export interface NodeData {
    initial_tegus: number;
    current_tegus: number;
    desirability: number;
}

export interface Agent {
    pos: Node;
    age: number;
    lifespan: number;
}

export function key(...parts: (number | Node)[]): string {
    return parts.flat().join(",");
}

export function same(a: Node | null, b: Node | null): boolean {
    return a !== null && b !== null && a[0] === b[0] && a[1] === b[1];
}

// Mirrors tegu_sim/state.py, plus the viewer fields from V1 (Archive/tegu_sim/state.py)
export class AppState {
    IMAGE_PATH = "";
    VIEW_WIDTH = 0;
    VIEW_HEIGHT = 0;
    PAN_SPEED = 0;
    ZOOM_LEVELS: number[] = [];
    zoom_index = 0;
    FONT_SIZE = 0;

    x_min = 0;
    x_max = 0;
    y_min = 0;
    y_max = 0;

    img: HTMLImageElement | null = null;
    img_width = 0;
    img_height = 0;
    image_surface!: Surface;
    PREVIEW_WIDTH = 0;
    PREVIEW_HEIGHT = 0;
    preview_surface!: Surface;
    minimap!: Surface;

    field_width = 0;
    field_height = 0;
    colored: Uint8Array = new Uint8Array();
    scalar_surface!: Surface;
    heatmap_mode = 0;

    edge_desirability = new Map<string, number>();
    grid_nodes: ([number, number] | null)[][] = [];
    grid_edges: Edge[] = [];
    grid_size = 0;
    node_data = new Map<string, NodeData>();
    tegu_sources = new Set<string>();
    tegu_colored: Uint8Array = new Uint8Array();
    tegu_surface!: Surface;

    screen!: Surface;
    clock!: InstanceType<typeof time.Clock>;
    font!: Font;
    x_offset = 0;
    y_offset = 0;
    cached_view: Surface | null = null;
    cached_zoom: number | null = null;
    cached_offset: [number, number] | null = null;
    needs_redraw = true;
    selected_node: Node | null = null;

    timestep = 0;
    used_edges = new Set<string>();
    used_nodes = new Set<string>();
    FRAME_DIR = "";
    agents: Agent[] = [];
    previous_agents: Agent[] = [];
    tegus_born = 0;
    tegus_died = 0;

    // Chart history, one value per timestep
    history_total: number[] = [];
    history_occupied: number[] = [];
}
