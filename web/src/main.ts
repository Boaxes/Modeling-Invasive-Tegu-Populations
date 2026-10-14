import * as pygame from "./pygame.js";

import { set_busy, set_log } from "./core.js";
import { run, SAVE_FRAME } from "./viewer.js";

const overlay = document.getElementById("overlay")!;
const log_el = document.getElementById("log")!;
const status_el = document.getElementById("status")!;
const seed_input = document.getElementById("seed") as HTMLInputElement;
const buttons = document.querySelectorAll<HTMLButtonElement>("#controls button");

let current: Promise<void> | null = null;

set_log((line) => {
    log_el.textContent += line + "\n";
});
set_busy((busy) => {
    status_el.textContent = busy ? "Running Python..." : "";
});

function parse_seed(): number | null {
    const text = seed_input.value.trim();
    return /^-?\d+$/.test(text) ? Number(text) : null;
}

function set_controls(enabled: boolean): void {
    buttons.forEach((b) => (b.disabled = !enabled));
}

async function start(): Promise<void> {
    set_controls(false);
    if (current) {
        pygame.event.post({ type: pygame.QUIT });
        await current;
    }

    const seed = parse_seed();
    const url = new URL(location.href);
    if (seed === null) url.searchParams.delete("seed");
    else url.searchParams.set("seed", String(seed));
    history.replaceState(null, "", url);

    log_el.textContent = seed === null ? "Seed: random\n" : `Seed: ${seed}\n`;
    overlay.hidden = false;
    overlay.classList.remove("error");
    current = run(seed, () => {
        overlay.hidden = true;
        set_controls(true);
    }).catch((err) => {
        log_el.textContent += `\nError: ${err instanceof Error ? err.message : err}\n`;
        overlay.hidden = false;
        overlay.classList.add("error");
        current = null;
        (document.getElementById("restart") as HTMLButtonElement).disabled = false;
    });
}

document.getElementById("step")!.addEventListener("click", () => {
    pygame.event.post({ type: pygame.KEYDOWN, key: pygame.K_SPACE });
});
document.getElementById("heatmap")!.addEventListener("click", () => {
    pygame.event.post({ type: pygame.KEYDOWN, key: pygame.K_h });
});
document.getElementById("save")!.addEventListener("click", () => {
    pygame.event.post({ type: SAVE_FRAME });
});
document.getElementById("restart")!.addEventListener("click", () => {
    void start();
});
seed_input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") void start();
});

seed_input.value = new URLSearchParams(location.search).get("seed") ?? "";
void start();
