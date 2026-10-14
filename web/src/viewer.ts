// TypeScript port of the V1 pygame viewer (Archive/tegu_sim/viewer.py)

import * as pygame from "./pygame.js";

import { draw_chart } from "./chart.js";
import { build_environment, build_graph, initialize_agents, update_tegu_field } from "./core.js";
import { AppState, key, same, Node } from "./state.js";

// Posted by the "Save frame" button (replaces the per-step frames/ capture)
export const SAVE_FRAME = pygame.USEREVENT;


// Writes text into a panel element outside the canvas
function set_text(id: string, text: string): void {
    const el = document.getElementById(id)!;
    if (el.textContent !== text) el.textContent = text;
}


export function get_zoom(state: AppState): number {
    return state.ZOOM_LEVELS[state.zoom_index];
}


export function draw_mini_preview(state: AppState): void {
    const screen = state.minimap;
    const preview_surface = state.preview_surface;
    const VIEW_WIDTH = state.VIEW_WIDTH;
    const VIEW_HEIGHT = state.VIEW_HEIGHT;
    const PREVIEW_WIDTH = state.PREVIEW_WIDTH;
    const PREVIEW_HEIGHT = state.PREVIEW_HEIGHT;
    const img_width = state.img_width;
    const img_height = state.img_height;
    const x_min = state.x_min;
    const x_max = state.x_max;
    const y_min = state.y_min;
    const y_max = state.y_max;
    const x_offset = state.x_offset;
    const y_offset = state.y_offset;

    screen.blit(preview_surface, [0, 0]);
    const scale_x = PREVIEW_WIDTH / img_width;
    const scale_y = PREVIEW_HEIGHT / img_height;

    const mini_box = new pygame.Rect(
        x_min * scale_x,
        y_min * scale_y,
        (x_max - x_min) * scale_x,
        (y_max - y_min) * scale_y,
    );
    pygame.draw.rect(screen, [0, 255, 0], mini_box, 1);

    const zoom = get_zoom(state);
    const vw = VIEW_WIDTH / zoom;
    const vh = VIEW_HEIGHT / zoom;
    const view_rect = new pygame.Rect(
        x_offset * scale_x,
        y_offset * scale_y,
        vw * scale_x,
        vh * scale_y,
    );
    pygame.draw.rect(screen, [255, 255, 255], view_rect, 2);
}


export function draw_node_info(state: AppState, i: number, j: number): void {
    const node_data = state.node_data;

    const node = node_data.get(key(i, j))!;
    const text_lines = [
        `Node (${i}, ${j})`,
        `Initial Tegus: ${node["initial_tegus"]}`,
        `Current Tegus: ${node["current_tegus"]}`,
        `Desirability: ${node["desirability"].toFixed(2)}`,
    ];
    set_text("node-info", text_lines.join("\n"));
}


export async function load_surfaces(state: AppState): Promise<void> {
    // === Load image ===
    const img = new Image();
    img.src = new URL("../" + state.IMAGE_PATH, document.baseURI).href;
    await img.decode();
    const [img_width, img_height] = [img.naturalWidth, img.naturalHeight];
    const image_surface = new pygame.Surface(img);

    // Precompute preview surface
    const PREVIEW_WIDTH = 200;
    const PREVIEW_HEIGHT = Math.trunc(PREVIEW_WIDTH * img_height / img_width);
    const preview_surface = pygame.transform.scale(
        image_surface, [PREVIEW_WIDTH, PREVIEW_HEIGHT]
    );

    const scalar_surface = pygame.image.frombuffer(state.colored, [state.field_width, state.field_height], "RGBA");

    state.img = img;
    state.img_width = img_width;
    state.img_height = img_height;
    state.image_surface = image_surface;
    state.PREVIEW_WIDTH = PREVIEW_WIDTH;
    state.PREVIEW_HEIGHT = PREVIEW_HEIGHT;
    state.preview_surface = preview_surface;
    state.scalar_surface = scalar_surface;

    // Minimap is drawn on its own canvas next to the view
    const minimap_canvas = document.getElementById("minimap") as HTMLCanvasElement;
    [minimap_canvas.width, minimap_canvas.height] = [PREVIEW_WIDTH, PREVIEW_HEIGHT];
    state.minimap = new pygame.Surface(minimap_canvas);
}


export function update_tegu_surface(state: AppState): void {
    state.tegu_surface = pygame.image.frombuffer(
        state.tegu_colored, [state.field_width, state.field_height], "RGBA"
    );
}


function record_history(state: AppState): void {
    state.history_total.push(state.agents.length);
    state.history_occupied.push([...state.node_data.values()].filter((v) => v["current_tegus"] > 0).length);
    draw_chart(document.getElementById("chart-total") as unknown as SVGSVGElement, state.history_total);
    draw_chart(document.getElementById("chart-occupied") as unknown as SVGSVGElement, state.history_occupied);
}


export async function run(seed: number | null, on_ready: () => void = () => {}): Promise<void> {
    let state = await build_environment(seed);
    await load_surfaces(state);
    state = await build_graph(state);
    update_tegu_surface(state);

    // === Initialize pygame ===
    pygame.init();
    state.screen = pygame.display.set_mode([state.VIEW_WIDTH, state.VIEW_HEIGHT]);
    pygame.display.set_caption("Everglades Viewer");
    state.clock = new pygame.time.Clock();
    state.font = pygame.font.SysFont("arial", state.FONT_SIZE);

    // View state
    [state.x_offset, state.y_offset] = [1200, 1200];
    [state.cached_view, state.cached_zoom, state.cached_offset] = [null, null, null];
    state.needs_redraw = true;
    state.selected_node = null;

    // === Main Loop ===
    state.timestep = 0;
    state.used_edges = new Set();
    state.used_nodes = new Set();

    // === Frame Capture ===
    state.FRAME_DIR = "frames";

    await initialize_agents(state);
    record_history(state);

    on_ready();

    let running = true;
    while (running) {
        await state.clock.tick(60);
        const zoom = get_zoom(state);
        const move_amt = Math.trunc(state.PAN_SPEED / zoom);

        for (const event of pygame.event.get()) {
            if (event.type === pygame.KEYDOWN) {
                if (event.key === pygame.K_SPACE) {
                    state.timestep += 1;
                    state.previous_agents = state.agents.slice();
                    [
                        state.agents,
                        state.used_edges,
                        state.used_nodes,
                        state.tegus_born,
                        state.tegus_died,
                    ] = await update_tegu_field(state, state.previous_agents);
                    update_tegu_surface(state);
                    record_history(state);
                    state.needs_redraw = true;
                }
            }

            if (event.type === SAVE_FRAME) {
                // --- Capture frame (tegu + desirability heatmap only) ---
                const frame_surface = new pygame.Surface([state.field_width, state.field_height]);
                frame_surface.blit(state.scalar_surface, [0, 0]);
                frame_surface.blit(
                    state.tegu_surface, [0, 0], null, pygame.BLEND_RGB_ADD
                );
                pygame.image.save(
                    frame_surface,
                    `frame_${String(state.timestep).padStart(3, "0")}.png`,
                );
            }

            if (event.type === pygame.QUIT) {
                running = false;
            }

            else if (event.type === pygame.MOUSEBUTTONDOWN) {
                if ([4, 5].includes(event.button!)) {
                    const [mouse_x, mouse_y] = event.pos!;
                    const world_x = state.x_offset + mouse_x / zoom;
                    const world_y = state.y_offset + mouse_y / zoom;

                    if (event.button === 4 && state.zoom_index < state.ZOOM_LEVELS.length - 1) {
                        state.zoom_index += 1;
                    } else if (event.button === 5 && state.zoom_index > 0) {
                        state.zoom_index -= 1;
                    }

                    const new_zoom = get_zoom(state);
                    state.x_offset = world_x - mouse_x / new_zoom;
                    state.y_offset = world_y - mouse_y / new_zoom;
                    state.x_offset = Math.max(
                        0, Math.min(state.x_offset, state.img_width - state.VIEW_WIDTH / new_zoom)
                    );
                    state.y_offset = Math.max(
                        0, Math.min(state.y_offset, state.img_height - state.VIEW_HEIGHT / new_zoom)
                    );
                    state.needs_redraw = true;
                }

                else if (event.button === 1) {
                    const [mx, my] = event.pos!;
                    let found: Node | null = null;
                    for (const [i, row] of state.grid_nodes.entries()) {
                        for (const [j, item] of row.entries()) {
                            if (item === null) {
                                continue;
                            }
                            const [x, y] = item;
                            const [sx, sy] = [(x - state.x_offset) * zoom, (y - state.y_offset) * zoom];
                            if ((mx - sx) ** 2 + (my - sy) ** 2 <= 4 ** 2) {
                                found = [i, j];
                                break;
                            }
                        }
                        if (found) {
                            break;
                        }
                    }
                    state.selected_node = found;
                }
            }

            else if (event.type === pygame.KEYDOWN) {
                if (event.key === pygame.K_h) {
                    state.heatmap_mode = (state.heatmap_mode + 1) % 3;
                }
            }
        }

        const keys = pygame.key.get_pressed();
        let moved: boolean | number = false;
        if (keys[pygame.K_w]) {
            state.y_offset = Math.max(0, state.y_offset - move_amt);
            moved = true;
        }
        if (keys[pygame.K_s]) {
            state.y_offset = Math.min(state.img_height - state.VIEW_HEIGHT / zoom, state.y_offset + move_amt);
            moved = true;
        }
        if (keys[pygame.K_a]) {
            state.x_offset = Math.max(0, state.x_offset - move_amt);
            moved = true;
        }
        if (keys[pygame.K_d]) {
            state.x_offset = Math.min(state.img_width - state.VIEW_WIDTH / zoom, state.x_offset + move_amt);
            moved = true;
        }

        if (moved) {
            state.needs_redraw = true;
        }

        if (
            state.needs_redraw
            || zoom !== state.cached_zoom
            || !same([state.x_offset, state.y_offset], state.cached_offset)
        ) {
            let vw = Math.trunc(state.VIEW_WIDTH / zoom);
            let vh = Math.trunc(state.VIEW_HEIGHT / zoom);
            vw = Math.min(vw, state.img_width - Math.trunc(state.x_offset));
            vh = Math.min(vh, state.img_height - Math.trunc(state.y_offset));
            const view_rect = new pygame.Rect(Math.trunc(state.x_offset), Math.trunc(state.y_offset), vw, vh);
            const visible = state.image_surface.subsurface(view_rect).copy();
            state.cached_view = pygame.transform.scale(
                visible, [state.VIEW_WIDTH, state.VIEW_HEIGHT]
            );
            state.cached_zoom = zoom;
            state.cached_offset = [state.x_offset, state.y_offset];
            state.needs_redraw = false;
        }

        state.screen.blit(state.cached_view!, [0, 0]);

        if (state.heatmap_mode === 1 || state.heatmap_mode === 2) {
            const view_x1 = Math.max(state.x_min, Math.trunc(state.x_offset));
            const view_y1 = Math.max(state.y_min, Math.trunc(state.y_offset));
            const view_x2 = Math.min(state.x_max, Math.trunc(state.x_offset + state.VIEW_WIDTH / zoom));
            const view_y2 = Math.min(state.y_max, Math.trunc(state.y_offset + state.VIEW_HEIGHT / zoom));

            if (view_x2 > view_x1 && view_y2 > view_y1) {
                const src_x = view_x1 - state.x_min;
                const src_y = view_y1 - state.y_min;
                const src_w = view_x2 - view_x1;
                const src_h = view_y2 - view_y1;

                let visible_heat;
                if (state.heatmap_mode === 1) {
                    visible_heat = state.scalar_surface.subsurface(
                        new pygame.Rect(src_x, src_y, src_w, src_h)
                    );
                } else {
                    visible_heat = state.tegu_surface.subsurface(
                        new pygame.Rect(src_x, src_y, src_w, src_h)
                    );
                }

                const scaled_heat = pygame.transform.scale(
                    visible_heat, [Math.trunc(src_w * zoom), Math.trunc(src_h * zoom)]
                );
                state.screen.blit(
                    scaled_heat,
                    [(view_x1 - state.x_offset) * zoom, (view_y1 - state.y_offset) * zoom],
                    null,
                    pygame.BLEND_RGB_ADD,
                );
            }
        }

        pygame.draw.rect(
            state.screen,
            [0, 255, 0],
            new pygame.Rect(
                Math.trunc((state.x_min - state.x_offset) * zoom),
                Math.trunc((state.y_min - state.y_offset) * zoom),
                Math.trunc((state.x_max - state.x_min) * zoom),
                Math.trunc((state.y_max - state.y_min) * zoom),
            ),
            2,
        );

        for (const [[i1, j1], [i2, j2]] of state.grid_edges) {
            const [x1, y1] = state.grid_nodes[i1][j1]!;
            const [x2, y2] = state.grid_nodes[i2][j2]!;
            const [sx1, sy1] = [(x1 - state.x_offset) * zoom, (y1 - state.y_offset) * zoom];
            const [sx2, sy2] = [(x2 - state.x_offset) * zoom, (y2 - state.y_offset) * zoom];
            const color: pygame.Color = (
                state.used_edges.has(key(i1, j1, i2, j2))
                || state.used_edges.has(key(i2, j2, i1, j1))
                    ? [0, 255, 0]
                    : [255, 255, 0]
            );
            pygame.draw.line(state.screen, color, [sx1, sy1], [sx2, sy2], 3);

            if (same(state.selected_node, [i1, j1]) || same(state.selected_node, [i2, j2])) {
                const [mx, my] = [(sx1 + sx2) / 2, (sy1 + sy2) / 2];
                const desirability = state.edge_desirability.get(key(i1, j1, i2, j2))!;
                const label = state.font.render(desirability.toFixed(2), true, [255, 255, 255]);
                state.screen.blit(label, [mx + 3, my - 10]);
            }
        }

        for (const [i, row] of state.grid_nodes.entries()) {
            for (const [j, item] of row.entries()) {
                if (item === null) {
                    continue;
                }
                const [x, y] = item;
                const screen_x = Math.trunc((x - state.x_offset) * zoom);
                const screen_y = Math.trunc((y - state.y_offset) * zoom);

                let color: pygame.Color;
                if (
                    state.timestep > 0
                    && state.used_nodes.has(key(i, j))
                    && !state.tegu_sources.has(key(i, j))
                ) {
                    color = [0, 255, 0];
                } else if (state.tegu_sources.has(key(i, j))) {
                    color = [255, 100, 0];
                } else {
                    color = !same(state.selected_node, [i, j]) ? [255, 0, 0] : [0, 255, 255];
                }

                const radius = 4;
                pygame.draw.circle(state.screen, color, [screen_x, screen_y], radius);
            }
        }

        draw_mini_preview(state);

        if (state.selected_node !== null) {
            draw_node_info(state, ...state.selected_node);
        } else {
            set_text("node-info", "");
        }

        const heatmap_text = ["None", "Desirability", "Tegu Count"][state.heatmap_mode];
        const label = `Heatmap: ${heatmap_text}`;

        const timestep_label = `Timestep: ${state.timestep}`;

        // Debug info
        const total_tegus = state.agents.length;

        let stayed;
        if (state.timestep > 0) {
            moved = zip(state.previous_agents, state.agents).filter(
                ([a, b]) => !same(a["pos"], b["pos"])
            ).length;
            stayed = total_tegus - moved;
        } else {
            moved = stayed = 0;
        }

        const occupied_nodes = [...state.node_data.values()].filter((v) => v["current_tegus"] > 0).length;

        const debug_lines = [
            `Tegus Born: ${state.tegus_born}`,
            `Tegus Died: ${state.tegus_died}`,
            `Total Tegus: ${total_tegus}`,
            `Tegus Moved: ${moved}`,
            `Tegus Stayed: ${stayed}`,
            `Nodes with Tegus: ${occupied_nodes}`,
            `Total Nodes: ${state.node_data.size}`,
        ];

        set_text("hud", [label, timestep_label, ...debug_lines].join("\n"));

        pygame.display.flip();
    }

    pygame.quit();
}


// Python's zip(): pairs items up to the shorter list
function zip<A, B>(a: A[], b: B[]): [A, B][] {
    return a.slice(0, Math.min(a.length, b.length)).map((x, idx) => [x, b[idx]]);
}
