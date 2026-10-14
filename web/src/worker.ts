// Runs the Python core (tegu_sim) in Pyodide off the main thread.

const PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/";
const PY_FILES = ["__init__.py", "state.py", "environment.py", "graph.py", "simulation.py", "web_bridge.py"];
const PY_DIR = new URL("../../tegu_sim/", import.meta.url);

interface WorkerScope {
    postMessage(message: unknown, transfer?: Transferable[]): void;
    onmessage: ((e: MessageEvent) => void) | null;
}
const scope = self as unknown as WorkerScope;

function log(line: string): void {
    scope.postMessage({ type: "log", line });
}

async function load(): Promise<any> {
    log("Loading Python runtime...");
    const { loadPyodide } = await import(PYODIDE_URL + "pyodide.mjs");
    const pyodide = await loadPyodide({ indexURL: PYODIDE_URL });
    pyodide.setStdout({ batched: log });
    pyodide.setStderr({ batched: log });

    log("Loading numpy and scipy...");
    await pyodide.loadPackage(["numpy", "scipy"], { messageCallback: () => {} });

    pyodide.FS.mkdirTree("/home/pyodide/tegu_sim");
    for (const name of PY_FILES) {
        const response = await fetch(new URL(name, PY_DIR));
        if (!response.ok) throw new Error(`Failed to fetch tegu_sim/${name}: ${response.status}`);
        pyodide.FS.writeFile(`/home/pyodide/tegu_sim/${name}`, await response.text());
    }
    return pyodide.pyimport("tegu_sim.web_bridge");
}

const bridge = load();

function to_js(result: any): any {
    const data = result.toJs({ dict_converter: Object.fromEntries, create_pyproxies: false });
    result.destroy();
    return data;
}

function buffers(data: Record<string, unknown>): Transferable[] {
    return Object.values(data)
        .filter((v): v is Uint8Array => v instanceof Uint8Array)
        .map((v) => v.buffer);
}

const FUNCTIONS = ["build_environment", "build_graph", "initialize_agents", "update_tegu_field"];

scope.onmessage = async (e: MessageEvent) => {
    const { id, fn, args } = e.data;
    try {
        if (!FUNCTIONS.includes(fn)) throw new Error(`Unknown function ${fn}`);
        const web_bridge = await bridge;
        // Pyodide maps JS undefined to None, but null to a separate JsNull object
        const py_args = args.map((a: unknown) => (a === null ? undefined : a));
        const data = to_js(web_bridge[fn](...py_args));
        scope.postMessage({ id, type: "result", data }, buffers(data));
    } catch (err) {
        scope.postMessage({ id, type: "error", message: String(err) });
    }
};
