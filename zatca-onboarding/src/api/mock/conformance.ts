import type * as live from "../live";
import * as mock from "./handlers";

/**
 * The mock replaces `../live` wholesale at build time, and TypeScript only ever
 * sees the live module through `../backend`. Without this, a method added to
 * `live.ts` and forgotten in the mock would type-check everywhere and fail only
 * at runtime, in the test suite that is supposed to be checking it.
 *
 * Assigning the mock namespace to the live module's type makes that a compile
 * error. Extra members on the mock — the scenario controls — are allowed.
 */
export const conforms: typeof live = mock;
