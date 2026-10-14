// Main-thread side of the Python core: build_environment / build_graph /
// initialize_agents / update_tegu_field run in worker.ts, results land in AppState.

import { AppState, Agent, Edge, Node, NodeData, key } from "./state.js";

interface EnvironmentData {
    IMAGE_PATH: string;
    VIEW_WIDTH: number;
    VIEW_HEIGHT: number;
    PAN_SPEED: number;
    ZOOM_LEVELS: number[];
    zoom_index: number;
    FONT_SIZE: number;
    x_min: number;
    x_max: number;
    y_min: number;
    y_max: number;
    field_width: number;
    field_height: number;
    colored: Uint8Array;
    heatmap_mode: number;
}

interface GraphData {
    edge_desirability: [Edge, number][];
    grid_nodes: ([number, number] | undefined)[][];
    grid_edges: Edge[];
    grid_size: number;
    node_data: [Node, NodeData][];
    tegu_sources: Node[];
    tegu_colored: Uint8Array;
}

interface AgentsData {
    agents: Agent[];
    tegus_born: number;
    tegus_died: number;
}

interface StepData extends AgentsData {
    node_data: [Node, NodeData][];
    used_edges: Edge[];
    used_nodes: Node[];
    tegu_colored: Uint8Array;
}

let worker: Worker | null = null;
let next_id = 0;
const pending = new Map<number, { resolve: (d: unknown) => void; reject: (e: Error) => void }>();
let on_log: (line: string) => void = () => {};
let on_busy: (busy: boolean) => void = () => {};

export function set_log(fn: (line: string) => void): void {
    on_log = fn;
}

export function set_busy(fn: (busy: boolean) => void): void {
    on_busy = fn;
}

function call<T>(fn: string, ...args: unknown[]): Promise<T> {
    if (!worker) {
        worker = new Worker(new URL("./worker.js", import.meta.url), { type: "module" });
        worker.onmessage = (e: MessageEvent) => {
            const msg = e.data;
            if (msg.type === "log") {
                on_log(msg.line);
                return;
            }
            const p = pending.get(msg.id)!;
            pending.delete(msg.id);
            on_busy(pending.size > 0);
            if (msg.type === "error") p.reject(new Error(msg.message));
            else p.resolve(msg.data);
        };
        worker.onerror = (e) => {
            for (const p of pending.values()) p.reject(new Error(e.message || "Worker failed to start"));
            pending.clear();
        };
    }
    const id = next_id++;
    on_busy(true);
    return new Promise<T>((resolve, reject) => {
        pending.set(id, { resolve: resolve as (d: unknown) => void, reject });
        worker!.postMessage({ id, fn, args });
    });
}

export async function build_environment(seed: number | null): Promise<AppState> {
    const state = new AppState();
    const data = await call<EnvironmentData>("build_environment", seed);

    state.IMAGE_PATH = data.IMAGE_PATH;
    state.VIEW_WIDTH = data.VIEW_WIDTH;
    state.VIEW_HEIGHT = data.VIEW_HEIGHT;
    state.PAN_SPEED = data.PAN_SPEED;
    state.ZOOM_LEVELS = data.ZOOM_LEVELS;
    state.zoom_index = data.zoom_index;
    state.FONT_SIZE = data.FONT_SIZE;
    state.x_min = data.x_min;
    state.x_max = data.x_max;
    state.y_min = data.y_min;
    state.y_max = data.y_max;
    state.field_width = data.field_width;
    state.field_height = data.field_height;
    state.colored = data.colored;
    state.heatmap_mode = data.heatmap_mode;

    return state;
}

export async function build_graph(state: AppState): Promise<AppState> {
    const data = await call<GraphData>("build_graph");

    state.edge_desirability = new Map(data.edge_desirability.map(([e, d]) => [key(...e), d]));
    state.grid_nodes = data.grid_nodes.map((row) => row.map((item) => item ?? null));
    state.grid_edges = data.grid_edges;
    state.grid_size = data.grid_size;
    state.node_data = new Map(data.node_data.map(([k, v]) => [key(k), v]));
    state.tegu_sources = new Set(data.tegu_sources.map((n) => key(n)));
    state.tegu_colored = data.tegu_colored;

    return state;
}

export async function initialize_agents(state: AppState): Promise<void> {
    const data = await call<AgentsData>("initialize_agents");

    state.agents = data.agents;
    state.tegus_born = data.tegus_born;
    state.tegus_died = data.tegus_died;
}

export async function update_tegu_field(
    state: AppState,
    previous_agents: Agent[]
): Promise<[Agent[], Set<string>, Set<string>, number, number]> {
    // The worker keeps its own Python-side copy of previous_agents
    void previous_agents;
    const data = await call<StepData>("update_tegu_field");

    state.node_data = new Map(data.node_data.map(([k, v]) => [key(k), v]));
    state.tegu_colored = data.tegu_colored;

    return [
        data.agents,
        new Set(data.used_edges.map((e) => key(...e))),
        new Set(data.used_nodes.map((n) => key(n))),
        data.tegus_born,
        data.tegus_died,
    ];
}
