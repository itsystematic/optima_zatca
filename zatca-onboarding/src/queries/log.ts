import { useQuery } from "@tanstack/react-query";
import * as api from "@/api";
import { qk } from "./keys";

/**
 * The exchanges recorded for one register.
 *
 * Only fetched when a register is actually named — the log is opened on demand,
 * from the progress board or the log page, not loaded alongside the wizard.
 */
export function useRegisterLog(register: string | null, limit?: number) {
	return useQuery({
		queryKey: qk.registerLog(register ?? "", limit),
		queryFn: () => api.getRegisterLog(register!, limit),
		enabled: Boolean(register),
		staleTime: 5_000,
	});
}
