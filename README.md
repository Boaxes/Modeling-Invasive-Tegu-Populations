# Modeling Invasive Tegu Populations

![Tegu Invasion Simulator](Figure7.png)

## Description

An agent-based simulation of invasive Argentine black and white tegu (*Salvator merianae*) population spread across the Florida Everglades, visualized in real time over satellite imagery. Built with `pygame`, `numpy`, `scipy`, `matplotlib`, and `Pillow`. For a full mathematical presentation of the model, [see the original paper here](https://drive.google.com/file/d/1JGha21ooZma4E8qc3kM4hL-1Og2eA54A/view?usp=sharing) (model discussion starts on page 8).

## Motivation

Argentine black and white tegus are one of Florida's most damaging invasive species, threatening native wildlife including American alligators, gopher tortoises, and ground-nesting birds. Traditional population models treat spread as a continuous diffusion process, losing the individual-level behavior that drives real invasion dynamics. This project was built to explore whether an agent-based approach, where each tegu makes its own movement and reproduction decisions based on local habitat could better capture the spatial patterns of an active invasion.

## Quick Start

Install the required Python packages:

```bash
py -3 -m pip install numpy pygame pillow scipy matplotlib
```

Run the viewer with:

```bash
py -3 InvasiveTegus.py
```

## Usage

- `W`, `A`, `S`, `D`: pan around the map
- Mouse wheel: zoom in and out
- Left click on a node to display information
- `Space`: advance the simulation by one timestep
- `H`: cycle between no heatmap, desirability heatmap, and tegu-count heatmap
- Close the window: exit the program

Each time you press `Space`, the program advances the simulation by one timestep and saves a frame image into a `frames/` folder. Those saved frames can be combined into GIFs like the ones below.

| Seed 1 | Seed 2 |
|:---:|:---:|
| ![Seed 1 – 100 timesteps](GIFS/Supplementary%20GIF%202.gif) | ![Seed 2 – 100 timesteps](GIFS/Supplementary%20GIF%203.gif) |

*GIFs showing two different random initial seeds, each simulated over 100 timesteps, where red represents high habitat desirability, blue represents low habitat desirability, and green represents tegu population density.*
