import os

import pygame

from .environment import build_environment
from .graph import build_graph
from .simulation import initialize_agents, update_tegu_field


def get_zoom(state):
    return state.ZOOM_LEVELS[state.zoom_index]


def draw_mini_preview(state):
    screen = state.screen
    preview_surface = state.preview_surface
    VIEW_WIDTH = state.VIEW_WIDTH
    PREVIEW_WIDTH = state.PREVIEW_WIDTH
    PREVIEW_HEIGHT = state.PREVIEW_HEIGHT
    img_width = state.img_width
    img_height = state.img_height
    x_min = state.x_min
    x_max = state.x_max
    y_min = state.y_min
    y_max = state.y_max
    x_offset = state.x_offset
    y_offset = state.y_offset

    screen.blit(preview_surface, (VIEW_WIDTH - PREVIEW_WIDTH - 10, 10))
    scale_x = PREVIEW_WIDTH / img_width
    scale_y = PREVIEW_HEIGHT / img_height

    mini_box = pygame.Rect(
        x_min * scale_x + VIEW_WIDTH - PREVIEW_WIDTH - 10,
        y_min * scale_y + 10,
        (x_max - x_min) * scale_x,
        (y_max - y_min) * scale_y,
    )
    pygame.draw.rect(screen, (0, 255, 0), mini_box, 1)

    zoom = get_zoom(state)
    vw = VIEW_WIDTH / zoom
    vh = VIEW_HEIGHT / zoom
    view_rect = pygame.Rect(
        x_offset * scale_x + VIEW_WIDTH - PREVIEW_WIDTH - 10,
        y_offset * scale_y + 10,
        vw * scale_x,
        vh * scale_y,
    )
    pygame.draw.rect(screen, (255, 255, 255), view_rect, 2)


def draw_node_info(state, i, j):
    node_data = state.node_data
    font = state.font
    screen = state.screen
    FONT_SIZE = state.FONT_SIZE
    VIEW_HEIGHT = state.VIEW_HEIGHT

    node = node_data[(i, j)]
    text_lines = [
        f"Node ({i}, {j})",
        f"Initial Tegus: {node['initial_tegus']}",
        f"Current Tegus: {node['current_tegus']}",
        f"Desirability: {node['desirability']:.2f}",
    ]
    box_width = max(font.size(line)[0] for line in text_lines) + 10
    box_height = len(text_lines) * (FONT_SIZE + 2) + 6
    pygame.draw.rect(
        screen, (0, 0, 0), (10, VIEW_HEIGHT - box_height - 10, box_width, box_height)
    )
    pygame.draw.rect(
        screen,
        (255, 255, 255),
        (10, VIEW_HEIGHT - box_height - 10, box_width, box_height),
        1,
    )
    for i, line in enumerate(text_lines):
        text = font.render(line, True, (255, 255, 255))
        screen.blit(text, (15, VIEW_HEIGHT - box_height + i * (FONT_SIZE + 2) - 5))


def run():
    state = build_environment()
    state = build_graph(state)

    # === Initialize pygame ===
    pygame.init()
    state.screen = pygame.display.set_mode((state.VIEW_WIDTH, state.VIEW_HEIGHT))
    pygame.display.set_caption("Everglades Viewer")
    state.clock = pygame.time.Clock()
    state.font = pygame.font.SysFont("arial", state.FONT_SIZE)

    # View state
    state.x_offset, state.y_offset = 1200, 1200
    state.cached_view, state.cached_zoom, state.cached_offset = None, None, None
    state.needs_redraw = True
    state.selected_node = None

    # === Main Loop ===
    state.timestep = 0
    state.used_edges = set()
    state.used_nodes = set()

    # === Frame Capture ===
    import os

    state.FRAME_DIR = "frames"
    os.makedirs(state.FRAME_DIR, exist_ok=True)

    initialize_agents(state)

    running = True
    while running:
        state.clock.tick(60)
        zoom = get_zoom(state)
        move_amt = int(state.PAN_SPEED / zoom)

        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    state.timestep += 1
                    state.previous_agents = state.agents.copy()
                    (
                        state.agents,
                        state.used_edges,
                        state.used_nodes,
                        state.tegus_born,
                        state.tegus_died,
                    ) = update_tegu_field(state, state.previous_agents)
                    state.needs_redraw = True

                    # --- Capture frame (tegu + desirability heatmap only) ---
                    frame_surface = pygame.Surface((state.field_width, state.field_height))
                    frame_surface.blit(state.scalar_surface, (0, 0))
                    frame_surface.blit(
                        state.tegu_surface, (0, 0), special_flags=pygame.BLEND_RGB_ADD
                    )
                    pygame.image.save(
                        frame_surface,
                        os.path.join(state.FRAME_DIR, f"frame_{state.timestep:03}.png"),
                    )

            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button in [4, 5]:
                    mouse_x, mouse_y = event.pos
                    world_x = state.x_offset + mouse_x / zoom
                    world_y = state.y_offset + mouse_y / zoom

                    if event.button == 4 and state.zoom_index < len(state.ZOOM_LEVELS) - 1:
                        state.zoom_index += 1
                    elif event.button == 5 and state.zoom_index > 0:
                        state.zoom_index -= 1

                    new_zoom = get_zoom(state)
                    state.x_offset = world_x - mouse_x / new_zoom
                    state.y_offset = world_y - mouse_y / new_zoom
                    state.x_offset = max(
                        0, min(state.x_offset, state.img_width - state.VIEW_WIDTH / new_zoom)
                    )
                    state.y_offset = max(
                        0, min(state.y_offset, state.img_height - state.VIEW_HEIGHT / new_zoom)
                    )
                    state.needs_redraw = True

                elif event.button == 1:
                    mx, my = event.pos
                    found = None
                    for i, row in enumerate(state.grid_nodes):
                        for j, item in enumerate(row):
                            if item is None:
                                continue
                            x, y = item
                            sx, sy = (x - state.x_offset) * zoom, (y - state.y_offset) * zoom
                            if (mx - sx) ** 2 + (my - sy) ** 2 <= 4**2:
                                found = (i, j)
                                break
                        if found:
                            break
                    state.selected_node = found

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_h:
                    state.heatmap_mode = (state.heatmap_mode + 1) % 3

        keys = pygame.key.get_pressed()
        moved = False
        if keys[pygame.K_w]:
            state.y_offset = max(0, state.y_offset - move_amt)
            moved = True
        if keys[pygame.K_s]:
            state.y_offset = min(state.img_height - state.VIEW_HEIGHT / zoom, state.y_offset + move_amt)
            moved = True
        if keys[pygame.K_a]:
            state.x_offset = max(0, state.x_offset - move_amt)
            moved = True
        if keys[pygame.K_d]:
            state.x_offset = min(state.img_width - state.VIEW_WIDTH / zoom, state.x_offset + move_amt)
            moved = True

        if moved:
            state.needs_redraw = True

        if (
            state.needs_redraw
            or zoom != state.cached_zoom
            or (state.x_offset, state.y_offset) != state.cached_offset
        ):
            vw = int(state.VIEW_WIDTH / zoom)
            vh = int(state.VIEW_HEIGHT / zoom)
            vw = min(vw, state.img_width - int(state.x_offset))
            vh = min(vh, state.img_height - int(state.y_offset))
            view_rect = pygame.Rect(int(state.x_offset), int(state.y_offset), vw, vh)
            visible = state.image_surface.subsurface(view_rect).copy()
            state.cached_view = pygame.transform.scale(
                visible, (state.VIEW_WIDTH, state.VIEW_HEIGHT)
            )
            state.cached_zoom = zoom
            state.cached_offset = (state.x_offset, state.y_offset)
            state.needs_redraw = False

        state.screen.blit(state.cached_view, (0, 0))

        if state.heatmap_mode == 1 or state.heatmap_mode == 2:
            view_x1 = max(state.x_min, int(state.x_offset))
            view_y1 = max(state.y_min, int(state.y_offset))
            view_x2 = min(state.x_max, int(state.x_offset + state.VIEW_WIDTH / zoom))
            view_y2 = min(state.y_max, int(state.y_offset + state.VIEW_HEIGHT / zoom))

            if view_x2 > view_x1 and view_y2 > view_y1:
                src_x = view_x1 - state.x_min
                src_y = view_y1 - state.y_min
                src_w = view_x2 - view_x1
                src_h = view_y2 - view_y1

                if state.heatmap_mode == 1:
                    visible_heat = state.scalar_surface.subsurface(
                        pygame.Rect(src_x, src_y, src_w, src_h)
                    )
                else:
                    visible_heat = state.tegu_surface.subsurface(
                        pygame.Rect(src_x, src_y, src_w, src_h)
                    )

                scaled_heat = pygame.transform.scale(
                    visible_heat, (int(src_w * zoom), int(src_h * zoom))
                )
                state.screen.blit(
                    scaled_heat,
                    ((view_x1 - state.x_offset) * zoom, (view_y1 - state.y_offset) * zoom),
                    special_flags=pygame.BLEND_RGB_ADD,
                )

        pygame.draw.rect(
            state.screen,
            (0, 255, 0),
            pygame.Rect(
                int((state.x_min - state.x_offset) * zoom),
                int((state.y_min - state.y_offset) * zoom),
                int((state.x_max - state.x_min) * zoom),
                int((state.y_max - state.y_min) * zoom),
            ),
            2,
        )

        for (i1, j1), (i2, j2) in state.grid_edges:
            x1, y1 = state.grid_nodes[i1][j1]
            x2, y2 = state.grid_nodes[i2][j2]
            sx1, sy1 = (x1 - state.x_offset) * zoom, (y1 - state.y_offset) * zoom
            sx2, sy2 = (x2 - state.x_offset) * zoom, (y2 - state.y_offset) * zoom
            color = (
                (0, 255, 0)
                if ((i1, j1), (i2, j2)) in state.used_edges
                or ((i2, j2), (i1, j1)) in state.used_edges
                else (255, 255, 0)
            )
            pygame.draw.line(state.screen, color, (sx1, sy1), (sx2, sy2), 3)

            if state.selected_node in [(i1, j1), (i2, j2)]:
                mx, my = (sx1 + sx2) / 2, (sy1 + sy2) / 2
                desirability = state.edge_desirability[((i1, j1), (i2, j2))]
                label = state.font.render(f"{desirability:.2f}", True, (255, 255, 255))
                state.screen.blit(label, (mx + 3, my - 10))

        for i, row in enumerate(state.grid_nodes):
            for j, item in enumerate(row):
                if item is None:
                    continue
                x, y = item
                screen_x = int((x - state.x_offset) * zoom)
                screen_y = int((y - state.y_offset) * zoom)

                if (
                    state.timestep > 0
                    and (i, j) in state.used_nodes
                    and (i, j) not in state.tegu_sources
                ):
                    color = (0, 255, 0)
                elif (i, j) in state.tegu_sources:
                    color = (255, 100, 0)
                else:
                    color = (255, 0, 0) if state.selected_node != (i, j) else (0, 255, 255)

                radius = 4
                pygame.draw.circle(state.screen, color, (screen_x, screen_y), radius)

        draw_mini_preview(state)

        if state.selected_node is not None:
            draw_node_info(state, *state.selected_node)

        heatmap_text = ["None", "Desirability", "Tegu Count"][state.heatmap_mode]
        label = state.font.render(f"Heatmap: {heatmap_text}", True, (255, 255, 255))
        state.screen.blit(label, (10, 10))

        timestep_label = state.font.render(f"Timestep: {state.timestep}", True, (255, 255, 255))
        state.screen.blit(timestep_label, (10, 35))

        # Debug info
        total_tegus = sum(1 for _ in state.agents)

        if state.timestep > 0:
            moved = sum(
                1
                for a, b in zip(state.previous_agents, state.agents)
                if a["pos"] != b["pos"]
            )
            stayed = total_tegus - moved
        else:
            moved = stayed = 0

        occupied_nodes = sum(1 for v in state.node_data.values() if v["current_tegus"] > 0)

        debug_lines = [
            f"Tegus Born: {state.tegus_born}",
            f"Tegus Died: {state.tegus_died}",
            f"Total Tegus: {total_tegus}",
            f"Tegus Moved: {moved}",
            f"Tegus Stayed: {stayed}",
            f"Nodes with Tegus: {occupied_nodes}",
            f"Total Nodes: {len(state.node_data)}",
        ]

        for idx, line in enumerate(debug_lines):
            dbg_label = state.font.render(line, True, (255, 255, 255))
            state.screen.blit(dbg_label, (10, 60 + idx * 20))

        pygame.display.flip()

    pygame.quit()
