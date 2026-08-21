import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { QueryClient, UseMutationOptions } from "@tanstack/react-query";
import * as api from "@/api";
import type { Setup } from "@/api";
import { SCOPED_KEYS, SETUP_DERIVED_KEYS, qk } from "./keys";

/**
 * The setup record is the single source of truth for the whole wizard, so every
 * mutation returns it and writes it straight into the cache. No refetch, no
 * flash of stale state between steps.
 */

export function useSetup() {
	return useQuery({
		queryKey: qk.setup,
		queryFn: api.getSetup,
		// the progress screen turns this up; everywhere else the record only
		// changes in response to something the operator just did
		staleTime: 5_000,
	});
}

export function useGuidance() {
	return useQuery({ queryKey: qk.guidance, queryFn: api.getGuidance, staleTime: Infinity });
}

export function useCompanies() {
	return useQuery({ queryKey: qk.companies, queryFn: api.getCompanies, staleTime: Infinity });
}

/** Which obligations this company may choose, and why not, when it may not. */
export function usePhaseOptions() {
	return useQuery({ queryKey: qk.phaseOptions, queryFn: api.getPhaseOptions, staleTime: 60_000 });
}

export function useCities() {
	return useQuery({ queryKey: qk.cities, queryFn: api.getCities, staleTime: Infinity });
}

/**
 * Wrap a mutation that returns the setup record so its result seeds the cache.
 * Every write in this app has that shape, which is why it is worth a helper.
 */
function useSetupMutation<TInput>(
	mutationFn: (input: TInput) => Promise<Setup>,
	options?: Omit<UseMutationOptions<Setup, Error, TInput>, "mutationFn">,
) {
	const qc = useQueryClient();
	return useMutation<Setup, Error, TInput>({
		mutationFn,
		...options,
		onSuccess: (...args) => {
			qc.setQueryData(qk.setup, args[0]);
			// this write moved the setup on, and the company list reports where each
			// company's setup has got to
			for (const queryKey of SETUP_DERIVED_KEYS) qc.invalidateQueries({ queryKey });
			options?.onSuccess?.(...args);
		},
	});
}

export const useSaveMode = () => useSetupMutation(api.saveMode);
export const useSaveScope = () => useSetupMutation(api.saveScope);
export const useSaveEntity = () => useSetupMutation(api.saveEntity);
export const useMarkEntityVerified = () => useSetupMutation(() => api.markEntityVerified());

export const useAddRegister = () => useSetupMutation(api.addRegister);
export const useUpdateRegister = () =>
	useSetupMutation(({ id, input }: { id: string; input: api.RegisterInput }) =>
		api.updateRegister(id, input),
	);
export const useRemoveRegister = () => useSetupMutation(api.removeRegister);
export const useSetAcknowledged = () => useSetupMutation(api.setAcknowledged);

export const useSubmitOtp = () => useSetupMutation(api.submitOtp);
/**
 * Retrying takes optional codes: a register that already holds a compliance
 * certificate resumes without one, while a register that failed earlier needs a
 * fresh password and the server refuses without it.
 */
export const useRetryRegisters = () =>
	useSetupMutation(({ ids, entries }: { ids: string[]; entries?: api.OtpEntry[] }) =>
		api.retryRegisters(ids, entries ?? []),
	);
export const useFinishWithLive = () => useSetupMutation(() => api.finishWithLive());

/**
 * Point the app at another company's setup.
 *
 * The scope decides which record every read returns, so everything cached
 * belongs to the company being left. These are removed rather than invalidated
 * on purpose: an invalidated query keeps serving what it holds while it refetches,
 * and what it holds is the previous company's answers — which is how an operator
 * ends up looking at one company's registers under another company's name.
 */
export function useSwitchCompany() {
	const qc = useQueryClient();
	return (company: string | null) => {
		api.setCompanyScope(company);
		resetForCompanySwitch(qc);
	};
}

/**
 * Bring the cache in line with a company that just changed.
 *
 * Separate from the hook so it can be tested against a real QueryClient rather
 * than inferred from a component's behaviour: which queries survive a switch, and
 * which merely go stale, is the kind of distinction that silently rots.
 */
export function resetForCompanySwitch(qc: QueryClient): void {
	// removed, not invalidated: an invalidated query keeps serving what it holds
	// while it refetches, and what it holds is the previous company's answers
	for (const queryKey of SCOPED_KEYS) qc.removeQueries({ queryKey });
	// invalidated, not removed: the list is right for every company, but the
	// company being left has just changed state — most often it was finished,
	// which is the whole reason the operator is switching
	for (const queryKey of SETUP_DERIVED_KEYS) qc.invalidateQueries({ queryKey });
}
