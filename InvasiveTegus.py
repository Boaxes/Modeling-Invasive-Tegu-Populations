import os
import time
import random

import numpy as np
import pygame

from tegu_sim.environment import build_environment
from tegu_sim.graph import build_graph
from tegu_sim.simulation import initialize_agents, update_tegu_field

state = build_environment()
state = build_graph(state)

IMAGE_PATH = state.IMAGE_PATH
VIEW_WIDTH, VIEW_HEIGHT = state.VIEW_WIDTH, state.VIEW_HEIGHT
PAN_SPEED = state.PAN_SPEED
ZOOM_LEVELS = state.ZOOM_LEVELS
zoom_index = state.zoom_index
FONT_SIZE = state.FONT_SIZE

x_min, x_max = state.x_min, state.x_max
y_min, y_max = state.y_min, state.y_max

img = state.img
img_width, img_height = state.img_width, state.img_height
image_surface = state.image_surface

PREVIEW_WIDTH = state.PREVIEW_WIDTH
PREVIEW_HEIGHT = state.PREVIEW_HEIGHT
preview_surface = state.preview_surface

field_width = state.field_width
field_height = state.field_height
raw_field = state.raw_field
scalar_field = state.scalar_field
cmap = state.cmap
colored = state.colored
scalar_surface = state.scalar_surface
heatmap_mode = state.heatmap_mode

edge_desirability = state.edge_desirability
grid_nodes = state.grid_nodes
grid_edges = state.grid_edges
grid_size = state.grid_size
spacing_x = state.spacing_x
spacing_y = state.spacing_y
node_data = state.node_data
used_quadrants = state.used_quadrants
top_seeds = state.top_seeds
DIST_THRESH = state.DIST_THRESH
active_nodes = state.active_nodes
active_edges = state.active_edges
tegu_sources = state.tegu_sources
total_tegus = state.total_tegus
tegu_field = state.tegu_field
tegu_colored = state.tegu_colored
tegu_surface = state.tegu_surface

# === Initialize pygame ===
pygame.init()
screen = pygame.display.set_mode((VIEW_WIDTH, VIEW_HEIGHT))
pygame.display.set_caption("Everglades Viewer")
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", FONT_SIZE)

# View state
x_offset, y_offset = 1200, 1200
cached_view, cached_zoom, cached_offset = None, None, None
needs_redraw = True
selected_node = None

# === Helper Functions ===
def get_zoom():
    return ZOOM_LEVELS[zoom_index]


def draw_mini_preview():
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

    zoom = get_zoom()
    vw = VIEW_WIDTH / zoom
    vh = VIEW_HEIGHT / zoom
    view_rect = pygame.Rect(
        x_offset * scale_x + VIEW_WIDTH - PREVIEW_WIDTH - 10,
        y_offset * scale_y + 10,
        vw * scale_x,
        vh * scale_y,
    )
    pygame.draw.rect(screen, (255, 255, 255), view_rect, 2)


def draw_node_info(i, j):
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


# === Main Loop ===
timestep = 0
used_edges = set()
used_nodes = set()

# === Frame Capture ===
import os

FRAME_DIR = "frames"
os.makedirs(FRAME_DIR, exist_ok=True)
state.FRAME_DIR = FRAME_DIR

initialize_agents(state)
agents = state.agents
new_agents = state.new_agents
tegus_born = state.tegus_born
tegus_died = state.tegus_died

running = True
while running:
    clock.tick(60)
    zoom = get_zoom()
    move_amt = int(PAN_SPEED / zoom)

    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                timestep += 1
                previous_agents = agents.copy()
                state.previous_agents = previous_agents
                state.agents = agents
                agents, used_edges, used_nodes, tegus_born, tegus_died = update_tegu_field(
                    state, previous_agents
                )
                tegu_surface = state.tegu_surface
                needs_redraw = True

                # --- Capture frame (tegu + desirability heatmap only) ---
                frame_surface = pygame.Surface((field_width, field_height))
                frame_surface.blit(scalar_surface, (0, 0))
                frame_surface.blit(
                    tegu_surface, (0, 0), special_flags=pygame.BLEND_RGB_ADD
                )
                pygame.image.save(
                    frame_surface, os.path.join(FRAME_DIR, f"frame_{timestep:03}.png")
                )

        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button in [4, 5]:
                mouse_x, mouse_y = event.pos
                world_x = x_offset + mouse_x / zoom
                world_y = y_offset + mouse_y / zoom

                if event.button == 4 and zoom_index < len(ZOOM_LEVELS) - 1:
                    zoom_index += 1
                elif event.button == 5 and zoom_index > 0:
                    zoom_index -= 1

                new_zoom = get_zoom()
                x_offset = world_x - mouse_x / new_zoom
                y_offset = world_y - mouse_y / new_zoom
                x_offset = max(0, min(x_offset, img_width - VIEW_WIDTH / new_zoom))
                y_offset = max(0, min(y_offset, img_height - VIEW_HEIGHT / new_zoom))
                needs_redraw = True

            elif event.button == 1:
                mx, my = event.pos
                found = None
                for i, row in enumerate(grid_nodes):
                    for j, item in enumerate(row):
                        if item is None:
                            continue
                        x, y = item
                        sx, sy = (x - x_offset) * zoom, (y - y_offset) * zoom
                        if (mx - sx) ** 2 + (my - sy) ** 2 <= 4**2:
                            found = (i, j)
                            break
                    if found:
                        break
                selected_node = found

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_h:
                heatmap_mode = (heatmap_mode + 1) % 3

    keys = pygame.key.get_pressed()
    moved = False
    if keys[pygame.K_w]:
        y_offset = max(0, y_offset - move_amt)
        moved = True
    if keys[pygame.K_s]:
        y_offset = min(img_height - VIEW_HEIGHT / zoom, y_offset + move_amt)
        moved = True
    if keys[pygame.K_a]:
        x_offset = max(0, x_offset - move_amt)
        moved = True
    if keys[pygame.K_d]:
        x_offset = min(img_width - VIEW_WIDTH / zoom, x_offset + move_amt)
        moved = True

    if moved:
        needs_redraw = True

    if needs_redraw or zoom != cached_zoom or (x_offset, y_offset) != cached_offset:
        vw = int(VIEW_WIDTH / zoom)
        vh = int(VIEW_HEIGHT / zoom)
        vw = min(vw, img_width - int(x_offset))
        vh = min(vh, img_height - int(y_offset))
        view_rect = pygame.Rect(int(x_offset), int(y_offset), vw, vh)
        visible = image_surface.subsurface(view_rect).copy()
        cached_view = pygame.transform.scale(visible, (VIEW_WIDTH, VIEW_HEIGHT))
        cached_zoom = zoom
        cached_offset = (x_offset, y_offset)
        needs_redraw = False

    screen.blit(cached_view, (0, 0))

    if heatmap_mode == 1 or heatmap_mode == 2:
        view_x1 = max(x_min, int(x_offset))
        view_y1 = max(y_min, int(y_offset))
        view_x2 = min(x_max, int(x_offset + VIEW_WIDTH / zoom))
        view_y2 = min(y_max, int(y_offset + VIEW_HEIGHT / zoom))

        if view_x2 > view_x1 and view_y2 > view_y1:
            src_x = view_x1 - x_min
            src_y = view_y1 - y_min
            src_w = view_x2 - view_x1
            src_h = view_y2 - view_y1

            if heatmap_mode == 1:
                visible_heat = scalar_surface.subsurface(
                    pygame.Rect(src_x, src_y, src_w, src_h)
                )
            else:
                visible_heat = tegu_surface.subsurface(
                    pygame.Rect(src_x, src_y, src_w, src_h)
                )

            scaled_heat = pygame.transform.scale(
                visible_heat, (int(src_w * zoom), int(src_h * zoom))
            )
            screen.blit(
                scaled_heat,
                ((view_x1 - x_offset) * zoom, (view_y1 - y_offset) * zoom),
                special_flags=pygame.BLEND_RGB_ADD,
            )

    pygame.draw.rect(
        screen,
        (0, 255, 0),
        pygame.Rect(
            int((x_min - x_offset) * zoom),
            int((y_min - y_offset) * zoom),
            int((x_max - x_min) * zoom),
            int((y_max - y_min) * zoom),
        ),
        2,
    )

    for (i1, j1), (i2, j2) in grid_edges:
        x1, y1 = grid_nodes[i1][j1]
        x2, y2 = grid_nodes[i2][j2]
        sx1, sy1 = (x1 - x_offset) * zoom, (y1 - y_offset) * zoom
        sx2, sy2 = (x2 - x_offset) * zoom, (y2 - y_offset) * zoom
        color = (
            (0, 255, 0)
            if ((i1, j1), (i2, j2)) in used_edges
            or ((i2, j2), (i1, j1)) in used_edges
            else (255, 255, 0)
        )
        pygame.draw.line(screen, color, (sx1, sy1), (sx2, sy2), 3)

        if selected_node in [(i1, j1), (i2, j2)]:
            mx, my = (sx1 + sx2) / 2, (sy1 + sy2) / 2
            desirability = edge_desirability[((i1, j1), (i2, j2))]
            label = font.render(f"{desirability:.2f}", True, (255, 255, 255))
            screen.blit(label, (mx + 3, my - 10))

    for i, row in enumerate(grid_nodes):
        for j, item in enumerate(row):
            if item is None:
                continue
            x, y = item
            screen_x = int((x - x_offset) * zoom)
            screen_y = int((y - y_offset) * zoom)

            if timestep > 0 and (i, j) in used_nodes and (i, j) not in tegu_sources:
                color = (0, 255, 0)
            elif (i, j) in tegu_sources:
                color = (255, 100, 0)
            else:
                color = (255, 0, 0) if selected_node != (i, j) else (0, 255, 255)

            radius = 4
            pygame.draw.circle(screen, color, (screen_x, screen_y), radius)

    draw_mini_preview()

    if selected_node is not None:
        draw_node_info(*selected_node)

    heatmap_text = ["None", "Desirability", "Tegu Count"][heatmap_mode]
    label = font.render(f"Heatmap: {heatmap_text}", True, (255, 255, 255))
    screen.blit(label, (10, 10))

    timestep_label = font.render(f"Timestep: {timestep}", True, (255, 255, 255))
    screen.blit(timestep_label, (10, 35))

    # Debug info
    total_tegus = sum(1 for _ in agents)

    if timestep > 0:
        moved = sum(1 for a, b in zip(previous_agents, agents) if a["pos"] != b["pos"])
        stayed = total_tegus - moved
    else:
        moved = stayed = 0

    occupied_nodes = sum(1 for v in node_data.values() if v["current_tegus"] > 0)

    debug_lines = [
        f"Tegus Born: {tegus_born}",
        f"Tegus Died: {tegus_died}",
        f"Total Tegus: {total_tegus}",
        f"Tegus Moved: {moved}",
        f"Tegus Stayed: {stayed}",
        f"Nodes with Tegus: {occupied_nodes}",
        f"Total Nodes: {len(node_data)}",
    ]

    for idx, line in enumerate(debug_lines):
        dbg_label = font.render(line, True, (255, 255, 255))
        screen.blit(dbg_label, (10, 60 + idx * 20))

    pygame.display.flip()

pygame.quit()
