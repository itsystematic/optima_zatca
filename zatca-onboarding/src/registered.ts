import { ref } from "vue";
import { getRegistered } from "@/api";
import type { RegisteredRow } from "@/types";

export const registered = ref<RegisteredRow[]>([]);
let loading: Promise<RegisteredRow[]> | null = null;

export function loadRegistered(force = false): Promise<RegisteredRow[]> {
	if (force || !loading) {
		loading = getRegistered().then((rows) => (registered.value = rows ?? []));
		loading.catch(() => (loading = null));
	}
	return loading;
}
