/**
 * What `@/dev-toolbar` resolves to in a production build.
 *
 * The real toolbar drives the in-memory backend, so importing it would drag the
 * mock into the bundle. Vite points the specifier here instead; both exports are
 * shaped so `App.tsx` needs no branch of its own.
 */

export function isDevToolbarEnabled(): boolean {
	return false;
}

export function DevToolbar() {
	return null;
}
