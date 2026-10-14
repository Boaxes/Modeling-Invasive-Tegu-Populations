import os
import time
import random

import numpy as np
import pygame
from PIL import Image
from scipy.ndimage import gaussian_filter
from matplotlib import colormaps

from .state import AppState


def build_environment():
    state = AppState()

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

    state.IMAGE_PATH = IMAGE_PATH
    state.VIEW_WIDTH = VIEW_WIDTH
    state.VIEW_HEIGHT = VIEW_HEIGHT
    state.PAN_SPEED = PAN_SPEED
    state.ZOOM_LEVELS = ZOOM_LEVELS
    state.zoom_index = zoom_index
    state.FONT_SIZE = FONT_SIZE
    state.x_min = x_min
    state.x_max = x_max
    state.y_min = y_min
    state.y_max = y_max
    state.img = img
    state.img_width = img_width
    state.img_height = img_height
    state.image_surface = image_surface
    state.PREVIEW_WIDTH = PREVIEW_WIDTH
    state.PREVIEW_HEIGHT = PREVIEW_HEIGHT
    state.preview_surface = preview_surface
    state.field_width = field_width
    state.field_height = field_height
    state.raw_field = raw_field
    state.scalar_field = scalar_field
    state.cmap = cmap
    state.colored = colored
    state.scalar_surface = scalar_surface
    state.heatmap_mode = heatmap_mode

    return state
