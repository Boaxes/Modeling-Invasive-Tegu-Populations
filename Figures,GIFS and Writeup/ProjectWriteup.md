\clearpage
# Personal Project

The following details a personal project implemented that utilizes Graph Theory in the context of Mathematical Biology. The reader should carefully note the model is not designed to be biologically accurate (although details of how such a task could be accomplished are provided), but rather as an exercise and example of yet another way we can use Graph Theory in Mathematical Biology. The project has been attached with the submission.

## Overview

Argentine black and white tegus (*Salvator merianae*) are a rapidly spreading invasive species in the Florida Everglades. These lizards pose ecological threats by preying on native species and competing for resources\cite{https://doi.org/10.1002/ecs2.3579}. Understanding their potential spread is valuable for informing control strategies and anticipating ecological impact. While detailed ecological models exist, we explore a simplified agent-based simulation to illustrate how Graph Theory and spatial modeling techniques can be used in this context.

## Methodology

This model was implemented in Python, using the Pygame library for visualization and interaction, alongside NumPy and SciPy for numerical operations. A satellite image of the Florida Everglades was overlaid with a spatially aligned grid system. We began by generating a 100$\times$100 uniform grid of candidate nodes. However, this initial grid was not used directly—instead,we built a connected subgraph by activating nodes and edges using a selective, desirability-driven expansion process.

To simulate habitat variability, we created a scalar field that assigns a ``desirability score'' to each location. This field is constructed by filtering random noise with a Gaussian kernel and then applying histogram equalization to produce a smooth but structured distribution. Let $D(x, y)$ represent the desirability value at coordinates $(x, y)$. For each node, we sample $D$ to assign its desirability score.

We then select a small set of highly desirable ``seed'' nodes, denoted by:

\[
S = \{s_1, s_2, \dots, s_k\}
\]

These are chosen to be spatially separated and high in desirability. From each seed node, we grow a region by performing a random walk that preferentially activates nodes in more desirable areas. edges between nodes are similarly formed, and each edge receives a desirability weight sampled from $D$ at its midpoint.

### Graph Generation

graph generation proceeds in four steps:

1. Create the scalar desirability field $D(x, y)$.
2. Choose $k$ seed nodes $S$ from high-desirability areas.
3. Perform desirability-weighted random walks from each $s_i$ to activate connected nodes.
4. Connect seed regions with stochastic paths to ensure overall connectivity.

The resulting graph is a biologically-inspired subset of the full grid, focusing computational effort on plausible habitat.

### Tegu Agent Behaviour

Each tegu agent is characterized by:

- Current position: $(i, j)$  
- Age: $a$  
- Lifespan: $L$, randomly selected from 15 to 20 timesteps  

At each timestep, the agent decides whether to move, based on edge desirability and crowding at neighboring nodes. The probability of moving to a neighboring node $v$ is given by:

\[
P(v) \propto \text{desirability}_{(i,j)\rightarrow v} \times \left(1 + \frac{100 - \text{population}_v}{20} \right)
\]

- $\text{Desirability}_{(i,j)\rightarrow v}$: edge desirability between the current node and $v$  
- $\text{Population}_v$: Number of tegus currently at node $v$  

This equation gives higher preference to edges that are both desirable and lead to less crowded destinations.

If an agent's age reaches its lifespan ($a \geq L$), it is removed from the simulation. Reproduction occurs if a node has at least 2 tegus. A new tegu is added with probability:

\[
P_\text{birth} = \max\left(0.05, 1 - \frac{n}{20} \right)
\]

- $n$: The current number of tegus at the node  

This discourages reproduction in highly crowded areas, promoting expansion into underused habitat.

(see Figure 7: Image of the simulation. The scalar field described is represented by the red and blue regions)

## Results

For full results, please see the attached files: ``\textit{Supplementary GIF 1}",``\textit{Supplementary GIF 2}",``\textit{Supplementary GIF 3}",``\textit{Supplementary GIF 4}"

For sake of visualization of results, we program our simulation to take a snapshot of the scalar field, and desirability field at each time step simulated. We then use external software to merge the images into a GIF. Below are four simulations that were ran. The first two showcase the end result of the program after 50 time-steps, and 100 time-steps respectively. The following showcase the simulation after 100 and 500 time-steps. We use a different seed for our scalar field (Gaussian blur) on the ladder two. Readers should carefully note that although the seed is kept consistent between two simulations, the stochastic nature of the graph generation means the graphs are \textit{not} the same among any simulation.
\clearpage

### Seed 1 50,100 Timesteps

(see Figure 8: Last time-step of 50 time-step simulation, Seed 1)  
(see Figure 9: Last time-step of 100 time-step simulation, Seed 1)  
(see Figure 10: Comparison of last time-step frames for simulations of different lengths using Seed 1)

### Seed 2 100,500 Timesteps

(see Figure 11: Last time-step of 100 time-step simulation, Seed 2)  
(see Figure 12: Last time-step of 500 time-step simulation, Seed 2)  
(see Figure 13: Comparison of last time-step frames for simulations of different lengths using Seed 2)

### Interpretation of results

Despite the stochastic nature of the graph generation process—where each simulation produces a unique structure—simulations using the same desirability seed consistently converged toward similar steady-state distributions. Seed 2 illustrates this most clearly: both the 100- and 500-timestep runs display remarkably similar final configurations, suggesting that the dynamics of the system are robust to structural variation. Notably, the 500-timestep simulation appeared to stabilize around steps 200–300, with little visible change in population spread thereafter.

This behavior is reminiscent of steady-state solutions in differential equation models (as taught in Math 331), yet here it emerges from discrete, agent-based interactions governed by simple rules. The simulations also consistently show that tegu agents tend to spread relatively evenly across the habitat over time. No single area maintains an unusually high population, due to the way crowding penalties and desirability values influence both movement and reproduction. Together, these results suggest that the current model naturally promotes equilibrium-like behavior, even under randomness in both environment and agent decision-making.

## Suggestions for improvement

A major simplification in this project is the use of artificial Gaussian noise to model habitat desirability. A more biologically grounded approach would incorporate real ecological data- such as land cover type, proximity to water, or human infrastructure---which are known to influence tegu movement and habitat selection\cite{KlugEtAl_TeguEcology}\cite{FWC_TeguWeb}. For example, studies suggest that tegus often follow road networks, making road proximity a useful predictor\cite{PernasEtAl_TeguNesting}.

Furthermore, parameter tuning for reproduction, mortality, and movement could be informed by field studies or telemetry data. Introducing stochastic variability in environment quality or seasonal factors would also enhance realism\cite{McEachernEtAl_Brumation}.

## Project Conclusion

This project demonstrates how Graph Theory provides a powerful framework for modeling ecological dynamics, even in simplified or abstracted scenarios. By representing spatial structure with a graph and agent behavior as probabilistic transitions over that graph, we gain a flexible platform for simulating biological processes. While not biologically precise, this model offers a concrete example of how mathematical tools can be brought to bear on real-world ecological questions in Mathematical Biology.