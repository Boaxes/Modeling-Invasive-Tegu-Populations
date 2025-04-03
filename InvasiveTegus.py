import os
import time
import random

import numpy as np
import pygame
from PIL import Image
from scipy.ndimage import gaussian_filter
from matplotlib import colormaps

# === Configuration ===
IMAGE_PATH = "everglades_tm5_1985306_lrg.jpg"
VIEW_WIDTH, VIEW_HEIGHT = 800, 600
PAN_SPEED = 20
ZOOM_LEVELS = [0.25, 0.5, 1.0, 2.0, 4.0]
zoom_index = 2
FONT_SIZE = 18

# Everglades bounding box
x_min, x_max = 1445, 2817
y_min, y_max = 1389, 3233

# === Load image ===
img = Image.open(IMAGE_PATH).convert("RGB")
img_width, img_height = img.size
image_surface = pygame.image.fromstring(img.tobytes(), img.size, img.mode)

# Precompute preview surface
PREVIEW_WIDTH = 200
PREVIEW_HEIGHT = int(PREVIEW_WIDTH * img_height / img_width)
preview_surface = pygame.transform.scale(
    image_surface, (PREVIEW_WIDTH, PREVIEW_HEIGHT)
)

# === Scalar Field Generation ===
np.random.seed(44)
field_width = x_max - x_min
field_height = y_max - y_min
raw_field = np.random.rand(field_height, field_width)
raw_field = gaussian_filter(raw_field, sigma=40)

# Histogram equalization
hist, bins = np.histogram(raw_field.flatten(), bins=1000, density=True)
cdf = hist.cumsum()
cdf = cdf / cdf[-1]
scalar_field = np.interp(raw_field.flatten(), bins[:-1], cdf).reshape(raw_field.shape)
scalar_field = (scalar_field - scalar_field.min()) / np.ptp(scalar_field)

from matplotlib import colormaps

cmap = colormaps.get_cmap("coolwarm")
colored = np.zeros((field_height, field_width, 3), dtype=np.uint8)

cold_mask = scalar_field < 0.35
cold_strength = (0.35 - scalar_field[cold_mask]) / 0.35
colored[cold_mask, 2] = (cold_strength * 255).astype(np.uint8)

hot_mask = scalar_field > 0.75
hot_strength = (scalar_field[hot_mask] - 0.75) / 0.25
colored[hot_mask, 0] = (hot_strength * 255).astype(np.uint8)

scalar_surface = pygame.surfarray.make_surface(np.transpose(colored, (1, 0, 2)))
heatmap_mode = 0  # 0=None, 1=Desirability, 2=Tegu Count

# === Create 100x100 Grid Graph ===
edge_desirability = {}
grid_nodes = []
grid_edges = []
grid_size = 100
spacing_x = (x_max - x_min) / (grid_size - 1)
spacing_y = (y_max - y_min) / (grid_size - 1)
node_data = {}

# Create node grid
for i in range(grid_size):
    row = []
    for j in range(grid_size):
        x = x_min + j * spacing_x
        y = y_min + i * spacing_y
        row.append((x, y))
        node_data[(i, j)] = {
            "initial_tegus": 0,
            "current_tegus": 0,
            "desirability": 0.0,
        }
    grid_nodes.append(row)

# Create edges and compute edge desirability
for i in range(grid_size):
    for j in range(grid_size):
        neighbors = []
        if j < grid_size - 1:
            neighbors.append((i, j + 1))
        if i < grid_size - 1:
            neighbors.append((i + 1, j))
        if i > 0:
            neighbors.append((i - 1, j))
        if j > 0:
            neighbors.append((i, j - 1))

        for ni, nj in neighbors:
            grid_edges.append(((i, j), (ni, nj)))
            x1, y1 = grid_nodes[i][j]
            x2, y2 = grid_nodes[ni][nj]
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            fx, fy = int(mx - x_min), int(my - y_min)
            fx = min(max(fx, 0), scalar_field.shape[1] - 1)
            fy = min(max(fy, 0), scalar_field.shape[0] - 1)
            desirability = (
                scalar_field[fy, fx]
                if 0 <= fy < scalar_field.shape[0] and 0 <= fx < scalar_field.shape[1]
                else 0.0
            )
            edge_desirability[((i, j), (ni, nj))] = desirability

# Compute node desirability from edge desirability
for i in range(grid_size):
    for j in range(grid_size):
        connected = [
            d
            for ((i1, j1), (i2, j2)), d in edge_desirability.items()
            if (i1, j1) == (i, j)
        ]
        desirability = sum(connected) / len(connected) if connected else 0.0
        node_data[(i, j)]["desirability"] = desirability

print("Step 1: Grid and edge desirabilities computed.")
print(f"Nodes: {len(node_data)}, Edges: {len(grid_edges)}")

# === Select 8 most desirable nodes with quadrant coverage ===
all_nodes = list(node_data.items())
all_nodes.sort(key=lambda x: x[1]["desirability"], reverse=True)
quadrant = lambda i, j: (i >= grid_size // 2) * 2 + (j >= grid_size // 2)  # 0=TL, 1=TR, 2=BL, 3=BR

used_quadrants = set()
top_seeds = []

for k, v in all_nodes:
    q = quadrant(*k)
    if q not in used_quadrants:
        used_quadrants.add(q)
        top_seeds.append(k)
    elif len(top_seeds) < 8:
        top_seeds.append(k)
    if len(top_seeds) >= 8 and len(used_quadrants) == 4:
        break

all_nodes = list(node_data.items())
all_nodes.sort(key=lambda x: x[1]["desirability"], reverse=True)
top_seeds = []
DIST_THRESH = 30  # minimum grid distance between seeds

for k, _ in all_nodes:
    if not top_seeds:
        top_seeds.append(k)
    else:
        keep = True
        for si, sj in top_seeds:
            if abs(k[0] - si) + abs(k[1] - sj) < DIST_THRESH:
                keep = False
                break
        if keep:
            top_seeds.append(k)
    if len(top_seeds) == 5:
        break

# === Random walk expansion ===
import time

active_nodes = set(top_seeds)
active_edges = set()

for seed in top_seeds:
    current = seed
    visited = set([current])
    queue = [current]

    while len(visited) < 101:  # 1 seed + 100 additional unique nodes
        if not queue:
            break
        i, j = queue.pop(0)
        neighbors = [
            (i + di, j + dj)
            for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]
            if 0 <= i + di < grid_size and 0 <= j + dj < grid_size
        ]
        random.shuffle(neighbors)
        for ni, nj in neighbors:
            if (ni, nj) not in visited:
                visited.add((ni, nj))
                active_nodes.add((ni, nj))
                active_edges.add(((i, j), (ni, nj)))
                queue.append((ni, nj))
                break

print("Step 2: Random walk expansion from 5 seed nodes complete.")
print(f"Nodes: {len(active_nodes)}, Edges: {len(active_edges)}")

# === Connect clusters with randomized walks ===
# (connection logic will now be step 4)
tegu_sources = random.sample(list(active_nodes), 20)
total_tegus = 1000

for node in tegu_sources:
    tegus = min(int(random.gauss(50, 10)), 100)
    node_data[node]["current_tegus"] = tegus
    node_data[node]["initial_tegus"] = tegus

total_assigned = sum(node_data[n]["current_tegus"] for n in tegu_sources)
scaling_factor = total_tegus / total_assigned

for node in tegu_sources:
    scaled = round(node_data[node]["current_tegus"] * scaling_factor)
    node_data[node]["current_tegus"] = min(scaled, 100)
    node_data[node]["initial_tegus"] = node_data[node]["current_tegus"]

# === Tegu random walk expansions ===
print("Step 3: Tegu sources initialized and walks expanded.")
print(f"Nodes: {len(active_nodes)}, Edges: {len(active_edges)}")

for source in tegu_sources:
    visited = set([source])
    queue = [source]
    while len(visited) < 11:
        if not queue:
            break
        i, j = queue.pop(0)
        neighbors = [
            (i + di, j + dj)
            for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]
            if 0 <= i + di < grid_size and 0 <= j + dj < grid_size
        ]
        random.shuffle(neighbors)
        for ni, nj in neighbors:
            if (ni, nj) not in visited:
                visited.add((ni, nj))
                active_nodes.add((ni, nj))
                active_edges.add(((i, j), (ni, nj)))
                queue.append((ni, nj))
                break

print("Step 4: Cluster connection complete.")
print(f"Nodes: {len(active_nodes)}, Edges: {len(active_edges)}")

for i in range(len(top_seeds)):
    for j in range(i + 1, len(top_seeds)):
        a, b = top_seeds[i], top_seeds[j]
        current = a
        visited = set()
        path = [current]

        while current != b and len(path) < 1000:
            visited.add(current)
            i1, j1 = current
            neighbors = [
                (i1 + di, j1 + dj)
                for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                if 0 <= i1 + di < grid_size
                and 0 <= j1 + dj < grid_size
                and (i1 + di, j1 + dj) not in visited
            ]
            if not neighbors:
                break

            # Score by distance to target + noise
            def score(n):
                return abs(n[0] - b[0]) + abs(n[1] - b[1]) + random.uniform(0, 5)

            next_node = min(neighbors, key=score)
            path.append(next_node)
            current = next_node

        for u, v in zip(path[:-1], path[1:]):
            active_nodes.add(v)
            active_edges.add((u, v))

# Reduce node_data and grid_nodes
node_data = {k: v for k, v in node_data.items() if k in active_nodes}
grid_edges = list(active_edges)
grid_nodes = [
    [grid_nodes[i][j] if (i, j) in active_nodes else None for j in range(grid_size)]
    for i in range(grid_size)
]

connected_nodes = set()
for a, b in grid_edges:
    connected_nodes.add(a)
    connected_nodes.add(b)

node_data = {k: v for k, v in node_data.items() if k in connected_nodes}
grid_edges = [
    edge
    for edge in grid_edges
    if edge[0] in connected_nodes
    and edge[1] in connected_nodes
    and grid_nodes[edge[0][0]][edge[0][1]] is not None
    and grid_nodes[edge[1][0]][edge[1][1]] is not None
]

# === Generate Tegu Heatmap Surface ===
tegu_field = np.zeros_like(scalar_field)

for (i, j), data in node_data.items():
    x, y = grid_nodes[i][j]
    fx = min(max(int(x - x_min), 0), tegu_field.shape[1] - 1)
    fy = min(max(int(y - y_min), 0), tegu_field.shape[0] - 1)
    tegu_field[fy, fx] += data["current_tegus"]

tegu_field = gaussian_filter(tegu_field, sigma=20)
tegu_field = (tegu_field - tegu_field.min()) / np.ptp(tegu_field + 1e-5)

tegu_colored = np.zeros((field_height, field_width, 3), dtype=np.uint8)
tegu_colored[..., 1] = (tegu_field * 255).astype(np.uint8)  # Green channel
tegu_surface = pygame.surfarray.make_surface(np.transpose(tegu_colored, (1, 0, 2)))

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

# Initialize agents
agents = []
tegus_born = 0
tegus_died = 0

for (i, j), data in node_data.items():
    count = data["current_tegus"]
    for _ in range(count):
        lifespan = random.randint(15, 20)
        age = random.randint(1, 10)
        agents.append({"pos": (i, j), "age": age, "lifespan": lifespan})

new_agents = agents.copy()

# Ensure availability for debug display
def update_tegu_field(previous_agents):
    tegus_born = 0
    tegus_died = 0
    global agents, new_agents
    new_agents = []
    active_edges_this_step = set()
    active_nodes_this_step = set()

    # Reset node counts
    for v in node_data.values():
        v["current_tegus"] = 0

    # Prepare tegu_field for heatmap update
    global tegu_surface
    tegu_field = np.zeros_like(scalar_field)

    for agent in previous_agents:
        (i, j) = agent["pos"]
        agent["age"] += 1

        if agent["age"] >= agent["lifespan"]:
            tegus_died += 1
            continue  # Mortality

        neighbors = [
            (ni, nj)
            for ((i1, j1), (ni, nj)), desir in edge_desirability.items()
            if (i1, j1) == (i, j) and (ni, nj) in node_data
        ]

        stay_score = node_data[(i, j)]["desirability"]

        # remove movement encouragement modifier
        # stronger encouragement to move
        # lower stay incentive to encourage movement
        # boost stay incentive slightly
        options = [(i, j, stay_score)]

        for n in neighbors:
            edge_key = ((i, j), n)
            if n in node_data:
                population_factor = max(
                    0.01, (100 - node_data[n]["current_tegus"]) / 20
                )  # stronger overcrowding penalty
                # Favor emptier nodes
                desirability = edge_desirability[edge_key] * (1 + population_factor)
                options.append((n[0], n[1], desirability))
            if edge_key in edge_desirability:
                desirability = edge_desirability[edge_key]
                options.append((n[0], n[1], desirability))

        total = sum(d for _, _, d in options)

        if total == 0:
            choice = (i, j)
        else:
            r = random.uniform(0, total)
            acc = 0
            for ni, nj, desir in options:
                acc += desir
                if r <= acc:
                    choice = (ni, nj)
                    break

        if node_data[choice]["current_tegus"] < 100:
            node_data[choice]["current_tegus"] += 1
            x, y = grid_nodes[choice[0]][choice[1]]
            fx = min(max(int(x - x_min), 0), tegu_field.shape[1] - 1)
            fy = min(max(int(y - y_min), 0), tegu_field.shape[0] - 1)
            tegu_field[fy, fx] += 1
            new_agents.append(
                {"pos": choice, "age": agent["age"], "lifespan": agent["lifespan"]}
            )

            if choice != (i, j):
                active_edges_this_step.add(((i, j), choice))
                active_nodes_this_step.add(choice)
            else:
                active_nodes_this_step.add((i, j))
        else:
            node_data[(i, j)]["current_tegus"] += 1
            x, y = grid_nodes[i][j]
            fx = min(max(int(x - x_min), 0), tegu_field.shape[1] - 1)
            fy = min(max(int(y - y_min), 0), tegu_field.shape[0] - 1)
            tegu_field[fy, fx] += 1
            new_agents.append(
                {"pos": (i, j), "age": agent["age"], "lifespan": agent["lifespan"]}
            )

    agents = new_agents

    # === Reproduction ===
    local_counts = {}
    for agent in agents:
        (i, j) = agent["pos"]
        for di in range(-1, 2):
            for dj in range(-1, 2):
                ni, nj = i + di, j + dj
                if (ni, nj) in node_data:
                    local_counts[(ni, nj)] = local_counts.get((ni, nj), 0) + 1

    for (i, j), count in local_counts.items():
        if (i, j) in node_data and node_data[(i, j)]["current_tegus"] >= 2:
            chance = max(0.05, 1.0 - count / 20.0)  # discouraged by local density
            if random.random() < chance:
                lifespan = random.randint(15, 20)
                agents.append({"pos": (i, j), "age": 0, "lifespan": lifespan})
                tegus_born += 1
                node_data[(i, j)]["current_tegus"] += 1
                x, y = grid_nodes[i][j]
                fx = min(max(int(x - x_min), 0), tegu_field.shape[1] - 1)
                fy = min(max(int(y - y_min), 0), tegu_field.shape[0] - 1)
                tegu_field[fy, fx] += 1

    # Update tegu heatmap surface dynamically
    tegu_field = gaussian_filter(tegu_field, sigma=20)
    tegu_field = (tegu_field - tegu_field.min()) / np.ptp(tegu_field + 1e-5)
    tegu_colored = np.zeros((field_height, field_width, 3), dtype=np.uint8)
    tegu_colored[..., 1] = (tegu_field * 255).astype(np.uint8)
    tegu_surface = pygame.surfarray.make_surface(np.transpose(tegu_colored, (1, 0, 2)))

    return (
        new_agents,
        active_edges_this_step,
        active_nodes_this_step,
        tegus_born,
        tegus_died,
    )


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
                agents, used_edges, used_nodes, tegus_born, tegus_died = update_tegu_field(
                    previous_agents
                )
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
