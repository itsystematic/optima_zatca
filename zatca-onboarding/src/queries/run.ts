import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "@/api";
import { isConnected, subscribe, watchConnection } from "@/lib/realtime";
import { qk } from "./keys";

/** How often to ask when nothing is telling us. */
const POLL_MS = 900;

/**
 * The progress screen's read.
 *
 * Same cache entry as `useSetup`. Driven by the server pushing each stage as it
 * happens, and falling back to polling when there is no socket to push down —
 * `bench start` serves socket.io on another port, a proxy may not forward it, and
 * the mock has no server at all.
 *
 * Polling stops the moment the run settles either way, so a finished page is not
 * asking the server once a second forever.
 */
export function useRunningSetup() {
	const qc = useQueryClient();
	const live = useRealtimeRun();

	const query = useQuery({
		queryKey: qk.setup,
		queryFn: api.getSetup,
		// only when nothing is pushing: with a socket up, an interval would refetch
		// the row the event already told us about
		refetchInterval: (q) =>
			q.state.data?.status === "running" && !live ? POLL_MS : false,
		refetchIntervalInBackground: true,
		staleTime: 0,
	});

	// A socket that drops mid-run leaves the board frozen, because the interval was
	// off while it was up. Asking once on the transition covers the gap before
	// polling resumes.
	useEffect(() => {
		if (!live && query.data?.status === "running") {
			qc.invalidateQueries({ queryKey: qk.setup });
		}
	}, [live, query.data?.status, qc]);

	return query;
}

/**
 * Subscribe to run progress, returning whether the socket is actually carrying it.
 *
 * The event says a row changed rather than carrying the whole board, so the setup
 * record is refetched. It is published after commit, so the refetch reads the new
 * row rather than racing the transaction that wrote it.
 */
function useRealtimeRun(): boolean {
	const qc = useQueryClient();
	const [connected, setConnected] = useState(() => isConnected());

	useEffect(() => {
		const stopWatching = watchConnection(setConnected);
		const stopListening = subscribe("optima_zatca_run_progress", () => {
			qc.invalidateQueries({ queryKey: qk.setup });
		});
		return () => {
			stopWatching();
			stopListening();
		};
	}, [qc]);

	return connected;
}
