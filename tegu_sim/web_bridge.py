import random

import numpy as np

from . import environment, graph, simulation

# Called from web/src/core.ts in the same order as run() in web/src/viewer.ts;
# each function returns plain data for JS.

state = None


def rgba_bytes(colored):
    alpha = np.full(colored.shape[:2] + (1,), 255, dtype=np.uint8)
    return np.concatenate((colored, alpha), axis=2).tobytes()


def build_environment(seed=None):
    global state

    # seed=None reseeds from system randomness, same as the unseeded V1 app
    random.seed(seed)

    state = environment.build_environment()

    return {
        "IMAGE_PATH": state.IMAGE_PATH,
        "VIEW_WIDTH": state.VIEW_WIDTH,
        "VIEW_HEIGHT": state.VIEW_HEIGHT,
        "PAN_SPEED": state.PAN_SPEED,
        "ZOOM_LEVELS": state.ZOOM_LEVELS,
        "zoom_index": state.zoom_index,
        "FONT_SIZE": state.FONT_SIZE,
        "x_min": state.x_min,
        "x_max": state.x_max,
        "y_min": state.y_min,
        "y_max": state.y_max,
        "field_width": state.field_width,
        "field_height": state.field_height,
        "colored": rgba_bytes(state.colored),
        "heatmap_mode": state.heatmap_mode,
    }


def build_graph():
    global state

    state = graph.build_graph(state)

    return {
        "edge_desirability": [
            [edge, state.edge_desirability[edge]] for edge in state.grid_edges
        ],
        "grid_nodes": state.grid_nodes,
        "grid_edges": state.grid_edges,
        "grid_size": state.grid_size,
        "node_data": [[k, v] for k, v in state.node_data.items()],
        "tegu_sources": state.tegu_sources,
        "tegu_colored": rgba_bytes(state.tegu_colored),
    }


def initialize_agents():
    simulation.initialize_agents(state)

    return {
        "agents": state.agents,
        "tegus_born": state.tegus_born,
        "tegus_died": state.tegus_died,
    }


def update_tegu_field():
    previous_agents = state.agents.copy()
    (
        state.agents,
        used_edges,
        used_nodes,
        tegus_born,
        tegus_died,
    ) = simulation.update_tegu_field(state, previous_agents)

    return {
        "node_data": [[k, v] for k, v in state.node_data.items()],
        "agents": state.agents,
        "used_edges": list(used_edges),
        "used_nodes": list(used_nodes),
        "tegus_born": tegus_born,
        "tegus_died": tegus_died,
        "tegu_colored": rgba_bytes(state.tegu_colored),
    }
