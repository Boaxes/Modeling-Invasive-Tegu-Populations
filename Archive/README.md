# Archive: V1 Desktop Viewer

This folder holds the original V1 version of the project: a `pygame` desktop viewer with the simulation core it shipped with. It has been replaced by the browser version in the repository root and is no longer maintained. The code here is kept exactly as it was in the [`V1`](https://github.com/Boaxes/Modeling-Invasive-Tegu-Populations/tree/V1) tag.

## Running V1

Install the required Python packages:

```bash
py -3 -m pip install numpy pygame pillow scipy matplotlib
```

Run it from the **repository root** so it can find the satellite image:

```bash
py -3 Archive/InvasiveTegus.py
```

## Controls

- `W`, `A`, `S`, `D`: pan around the map
- Mouse wheel: zoom in and out
- Left click on a node to display information
- `Space`: advance the simulation by one timestep and save a frame into `frames/`
- `H`: cycle between no heatmap, desirability heatmap, and tegu-count heatmap
- Close the window: exit the program

Startup takes about a minute and each timestep several seconds. V2 removed those bottlenecks without changing the model's results.
