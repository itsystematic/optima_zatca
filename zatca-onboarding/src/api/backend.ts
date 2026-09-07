/**
 * The backend implementation this build talks to.
 *
 * Always the real one. `VITE_OZ_API=mock` makes Vite resolve this specifier
 * to `./mock/handlers` instead (see `vite.config.ts`), so a production build
 * never contains the stand-in — not its scenario engine, and not its fixtures.
 *
 * That indirection has to be a module boundary rather than a branch: a
 * `mock ? … : live` ternary keeps both in the module graph, and the fake
 * companies end up in the shipped bundle.
 *
 * TypeScript resolves this file, never the mock, so the live module is what the
 * app is checked against. `./mock/conformance.ts` checks the other direction.
 */

export * from "./live";
