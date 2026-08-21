/**
 * Give the test environment a working `localStorage`.
 *
 * Node 26 defines a global `localStorage` of its own, which is inert unless the
 * process was started with `--localstorage-file`. Being a global on
 * `globalThis`, it shadows the one jsdom installs, so `localStorage` is present
 * but reads as `undefined` — and the mock backend, which persists there so a
 * reload resumes the wizard, has nothing to write to.
 *
 * Rather than pass a Node flag through every runner, the shim below installs a
 * plain in-memory Storage when what is there does not work. A real browser is
 * untouched: this file is only ever loaded by Vitest.
 */

class MemoryStorage implements Storage {
	#entries = new Map<string, string>();

	get length(): number {
		return this.#entries.size;
	}

	clear(): void {
		this.#entries.clear();
	}

	getItem(key: string): string | null {
		return this.#entries.get(String(key)) ?? null;
	}

	key(index: number): string | null {
		return [...this.#entries.keys()][index] ?? null;
	}

	removeItem(key: string): void {
		this.#entries.delete(String(key));
	}

	setItem(key: string, value: string): void {
		this.#entries.set(String(key), String(value));
	}

	[name: string]: unknown;
}

/** Whether what is installed can actually hold a value. */
function works(candidate: unknown): boolean {
	try {
		const storage = candidate as Storage | undefined;
		if (!storage) return false;
		const probe = "__probe__";
		storage.setItem(probe, "1");
		storage.removeItem(probe);
		return true;
	} catch {
		return false;
	}
}

if (!works(globalThis.localStorage)) {
	const storage = new MemoryStorage();
	Object.defineProperty(globalThis, "localStorage", {
		value: storage,
		configurable: true,
		writable: true,
	});
	if (typeof window !== "undefined") {
		Object.defineProperty(window, "localStorage", {
			value: storage,
			configurable: true,
			writable: true,
		});
	}
}
