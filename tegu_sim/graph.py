import time
import random

import numpy as np
import pygame
from scipy.ndimage import gaussian_filter


def build_graph(state):
    x_min = state.x_min
    x_max = state.x_max
    y_min = state.y_min
    y_max = state.y_max
    scalar_field = state.scalar_field
    field_width = state.field_width
    field_height = state.field_height

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

    state.edge_desirability = edge_desirability
    state.grid_nodes = grid_nodes
    state.grid_edges = grid_edges
    state.grid_size = grid_size
    state.spacing_x = spacing_x
    state.spacing_y = spacing_y
    state.node_data = node_data
    state.used_quadrants = used_quadrants
    state.top_seeds = top_seeds
    state.DIST_THRESH = DIST_THRESH
    state.active_nodes = active_nodes
    state.active_edges = active_edges
    state.tegu_sources = tegu_sources
    state.total_tegus = total_tegus
    state.tegu_field = tegu_field
    state.tegu_colored = tegu_colored
    state.tegu_surface = tegu_surface

    return state
