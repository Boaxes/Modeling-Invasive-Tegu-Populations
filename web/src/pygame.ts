// Minimal Canvas 2D stand-in for the parts of pygame used by the V1 viewer
// (Archive/tegu_sim/viewer.py). Names and call shapes follow pygame so
// viewer.ts can mirror it.

export type Color = [number, number, number];
export type Point = [number, number];

export const QUIT = 256;
export const KEYDOWN = 768;
export const MOUSEBUTTONDOWN = 1025;
export const USEREVENT = 32866;
export const BLEND_RGB_ADD = 1;

export const K_SPACE = "Space";
export const K_h = "KeyH";
export const K_w = "KeyW";
export const K_a = "KeyA";
export const K_s = "KeyS";
export const K_d = "KeyD";

export interface Event {
    type: number;
    key?: string;
    button?: number;
    pos?: Point;
}

export class Rect {
    x: number;
    y: number;
    w: number;
    h: number;

    constructor(x: number, y: number, w: number, h: number) {
        this.x = Math.trunc(x);
        this.y = Math.trunc(y);
        this.w = Math.trunc(w);
        this.h = Math.trunc(h);
    }
}

type RectLike = Rect | [number, number, number, number];

function as_rect(r: RectLike): Rect {
    return r instanceof Rect ? r : new Rect(r[0], r[1], r[2], r[3]);
}

function rgb(color: Color): string {
    return `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
}

type Source = HTMLCanvasElement | HTMLImageElement;

// A Surface is a region of a source image/canvas, optionally drawn at a scaled size.
// subsurface() and transform.scale() are lazy views; only blit() touches pixels.
export class Surface {
    source: Source;
    rect: Rect;
    size: Point;

    constructor(size_or_source: Point | Source, rect?: Rect, size?: Point) {
        if (Array.isArray(size_or_source)) {
            const canvas = document.createElement("canvas");
            canvas.width = size_or_source[0];
            canvas.height = size_or_source[1];
            const ctx = canvas.getContext("2d")!;
            ctx.fillStyle = "black";
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            this.source = canvas;
        } else {
            this.source = size_or_source;
        }
        const w = this.source instanceof HTMLImageElement ? this.source.naturalWidth : this.source.width;
        const h = this.source instanceof HTMLImageElement ? this.source.naturalHeight : this.source.height;
        this.rect = rect ?? new Rect(0, 0, w, h);
        this.size = size ?? [this.rect.w, this.rect.h];
    }

    get ctx(): CanvasRenderingContext2D {
        if (!(this.source instanceof HTMLCanvasElement)) {
            throw new Error("Surface is not drawable");
        }
        const ctx = this.source.getContext("2d")!;
        ctx.imageSmoothingEnabled = false;
        return ctx;
    }

    get_width(): number {
        return this.size[0];
    }

    get_height(): number {
        return this.size[1];
    }

    subsurface(rect: Rect): Surface {
        return new Surface(
            this.source,
            new Rect(this.rect.x + rect.x, this.rect.y + rect.y, rect.w, rect.h)
        );
    }

    copy(): Surface {
        return this;
    }

    blit(src: Surface | TextSurface, dest: Point, area: Rect | null = null, special_flags = 0): void {
        const ctx = this.ctx;
        const dx = Math.trunc(dest[0]);
        const dy = Math.trunc(dest[1]);
        if (src instanceof TextSurface) {
            ctx.font = src.font;
            ctx.fillStyle = rgb(src.color);
            ctx.textBaseline = "top";
            ctx.fillText(src.text, dx, dy);
            return;
        }
        const r = area ?? src.rect;
        ctx.globalCompositeOperation = special_flags === BLEND_RGB_ADD ? "lighter" : "source-over";
        ctx.drawImage(src.source, r.x, r.y, r.w, r.h, dx, dy, src.size[0], src.size[1]);
        ctx.globalCompositeOperation = "source-over";
    }
}

export class TextSurface {
    constructor(
        public text: string,
        public font: string,
        public color: Color
    ) {}
}

export class Font {
    css: string;
    linesize: number;

    constructor(name: string, size: number) {
        this.css = `${size}px ${name}, sans-serif`;
        this.linesize = Math.round(size * 1.15);
    }

    size(text: string): Point {
        const ctx = measure_canvas.getContext("2d")!;
        ctx.font = this.css;
        return [Math.ceil(ctx.measureText(text).width), this.linesize];
    }

    render(text: string, antialias: boolean, color: Color): TextSurface {
        return new TextSurface(text, this.css, color);
    }
}

const measure_canvas = document.createElement("canvas");

// === pygame.draw ===
export const draw = {
    rect(surface: Surface, color: Color, rect: RectLike, width = 0): void {
        const r = as_rect(rect);
        const ctx = surface.ctx;
        if (width === 0) {
            ctx.fillStyle = rgb(color);
            ctx.fillRect(r.x, r.y, r.w, r.h);
        } else {
            // pygame draws the border inside the rect
            ctx.strokeStyle = rgb(color);
            ctx.lineWidth = width;
            ctx.strokeRect(r.x + width / 2, r.y + width / 2, r.w - width, r.h - width);
        }
    },

    line(surface: Surface, color: Color, start_pos: Point, end_pos: Point, width = 1): void {
        const ctx = surface.ctx;
        ctx.strokeStyle = rgb(color);
        ctx.lineWidth = width;
        ctx.beginPath();
        ctx.moveTo(start_pos[0], start_pos[1]);
        ctx.lineTo(end_pos[0], end_pos[1]);
        ctx.stroke();
    },

    circle(surface: Surface, color: Color, center: Point, radius: number): void {
        const ctx = surface.ctx;
        ctx.fillStyle = rgb(color);
        ctx.beginPath();
        ctx.arc(center[0], center[1], radius, 0, 2 * Math.PI);
        ctx.fill();
    },
};

// === pygame.transform ===
export const transform = {
    scale(surface: Surface, size: Point): Surface {
        return new Surface(surface.source, surface.rect, [Math.trunc(size[0]), Math.trunc(size[1])]);
    },
};

// === pygame.image ===
export const image = {
    frombuffer(buffer: Uint8Array, size: Point, format: "RGBA"): Surface {
        const canvas = document.createElement("canvas");
        canvas.width = size[0];
        canvas.height = size[1];
        const data = new ImageData(new Uint8ClampedArray(buffer.buffer as ArrayBuffer, buffer.byteOffset, buffer.byteLength), size[0], size[1]);
        canvas.getContext("2d")!.putImageData(data, 0, 0);
        return new Surface(canvas);
    },

    save(surface: Surface, filename: string): void {
        if (!(surface.source instanceof HTMLCanvasElement)) {
            throw new Error("Surface is not saveable");
        }
        surface.source.toBlob((blob) => {
            if (!blob) return;
            const a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = filename;
            a.click();
            setTimeout(() => URL.revokeObjectURL(a.href), 1000);
        }, "image/png");
    },
};

// === pygame.font ===
export const font = {
    SysFont(name: string, size: number): Font {
        return new Font(name, size);
    },
};

// === Events / input ===
let event_queue: Event[] = [];
const pressed = new Set<string>();
let screen_canvas: HTMLCanvasElement | null = null;
let last_wheel = 0;
const listeners: [EventTarget, string, EventListener][] = [];

function listen(target: EventTarget, type: string, fn: EventListener, options?: AddEventListenerOptions): void {
    target.addEventListener(type, fn, options);
    listeners.push([target, type, fn]);
}

function typing_in_form(e: KeyboardEvent): boolean {
    const target = e.target as HTMLElement | null;
    return !!target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA");
}

function canvas_pos(e: MouseEvent): Point {
    const canvas = screen_canvas!;
    const r = canvas.getBoundingClientRect();
    return [
        Math.trunc(((e.clientX - r.left) * canvas.width) / r.width),
        Math.trunc(((e.clientY - r.top) * canvas.height) / r.height),
    ];
}

export const event = {
    get(): Event[] {
        const events = event_queue;
        event_queue = [];
        return events;
    },

    post(e: Event): void {
        event_queue.push(e);
    },
};

export const key = {
    get_pressed(): Record<string, boolean> {
        const keys: Record<string, boolean> = {};
        for (const k of pressed) keys[k] = true;
        return keys;
    },
};

export function init(): void {
    event_queue = [];
    pressed.clear();
    listen(window, "keydown", (e) => {
        const ke = e as KeyboardEvent;
        if (typing_in_form(ke)) return;
        if ([K_SPACE, K_w, K_a, K_s, K_d, K_h].includes(ke.code)) ke.preventDefault();
        pressed.add(ke.code);
        // pygame has key repeat disabled by default
        if (!ke.repeat) event_queue.push({ type: KEYDOWN, key: ke.code });
    });
    listen(window, "keyup", (e) => {
        pressed.delete((e as KeyboardEvent).code);
    });
    listen(window, "blur", () => pressed.clear());
}

export function quit(): void {
    for (const [target, type, fn] of listeners) target.removeEventListener(type, fn);
    listeners.length = 0;
    event_queue = [];
    pressed.clear();
}

export const display = {
    set_mode(size: Point): Surface {
        screen_canvas = document.getElementById("screen") as HTMLCanvasElement;
        screen_canvas.width = size[0];
        screen_canvas.height = size[1];
        listen(screen_canvas, "mousedown", (e) => {
            const me = e as MouseEvent;
            if (me.button === 0) event_queue.push({ type: MOUSEBUTTONDOWN, button: 1, pos: canvas_pos(me) });
        });
        listen(
            screen_canvas,
            "wheel",
            (e) => {
                const we = e as WheelEvent;
                we.preventDefault();
                // One zoom step per wheel gesture tick (trackpads fire many small events)
                if (we.timeStamp - last_wheel < 120 || we.deltaY === 0) return;
                last_wheel = we.timeStamp;
                event_queue.push({ type: MOUSEBUTTONDOWN, button: we.deltaY < 0 ? 4 : 5, pos: canvas_pos(we) });
            },
            { passive: false }
        );
        return new Surface(screen_canvas);
    },

    set_caption(title: string): void {
        document.title = title;
    },

    flip(): void {
        // Canvas presents automatically
    },
};

// === pygame.time ===
export const time = {
    Clock: class Clock {
        last = 0;

        tick(framerate: number): Promise<number> {
            return new Promise((resolve) => {
                const frame = (now: number) => {
                    if (now - this.last < 1000 / framerate - 1) {
                        requestAnimationFrame(frame);
                        return;
                    }
                    const dt = now - this.last;
                    this.last = now;
                    resolve(dt);
                };
                requestAnimationFrame(frame);
            });
        }
    },
};
