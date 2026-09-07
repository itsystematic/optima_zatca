import { useCallback } from "react";
import { ApiError } from "@/api";
import type { Problem } from "@/api";
import { useT } from "@/i18n/core";
import type { MessageKey } from "@/i18n/core";
import { byField } from "./validation";

/** Field errors the server rejected a write with, keyed by field name. */
export function serverFieldErrors(error: unknown): Record<string, Problem> {
	return error instanceof ApiError ? byField(error.fieldErrors) : {};
}

/**
 * Turn a rule failure into a sentence in the reader's language.
 *
 * Rules carry keys, not prose, so the same failure renders correctly whether it
 * came from the form on this screen or from the server rejecting the write.
 */
export function useProblemText() {
	const t = useT();
	return useCallback(
		(problem: Problem | undefined): string | null =>
			problem ? t(problem.key as MessageKey, problem.params) : null,
		[t],
	);
}

/** A single sentence to show above a form when a write failed. */
export function useFormError() {
	const t = useT();
	return useCallback(
		(error: unknown): string | null => {
			if (!error) return null;
			if (error instanceof ApiError) return t(error.key as MessageKey);
			return t("common.somethingWrong");
		},
		[t],
	);
}
