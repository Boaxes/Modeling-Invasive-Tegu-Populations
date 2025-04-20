import random

import numpy as np
import pygame
from scipy.ndimage import gaussian_filter


# Initialize agents
def initialize_agents(state):
    node_data = state.node_data

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

    state.agents = agents
    state.new_agents = new_agents
    state.tegus_born = tegus_born
    state.tegus_died = tegus_died


# Ensure availability for debug display
def update_tegu_field(state, previous_agents):
    edge_desirability = state.edge_desirability
    node_data = state.node_data
    grid_nodes = state.grid_nodes
    scalar_field = state.scalar_field
    x_min = state.x_min
    y_min = state.y_min
    field_height = state.field_height
    field_width = state.field_width

    tegus_born = 0
    tegus_died = 0
    agents = state.agents
    new_agents = []
    active_edges_this_step = set()
    active_nodes_this_step = set()

    # Reset node counts
    for v in node_data.values():
        v["current_tegus"] = 0

    # Prepare tegu_field for heatmap update
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

    state.agents = agents
    state.new_agents = new_agents
    state.tegu_field = tegu_field
    state.tegu_colored = tegu_colored
    state.tegu_surface = tegu_surface
    state.tegus_born = tegus_born
    state.tegus_died = tegus_died

    return (
        new_agents,
        active_edges_this_step,
        active_nodes_this_step,
        tegus_born,
        tegus_died,
    )
