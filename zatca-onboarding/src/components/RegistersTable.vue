<script setup lang="ts">
import { Badge, Button } from "frappe-ui";
import { __ } from "@/translate";
import type { Phase } from "@/types";

interface Row {
	commercial_register_name: string;
	commercial_register_number: string;
	city: string;
	district: string;
	phase?: Phase;
}

defineProps<{ rows: Row[]; actions?: boolean; disabled?: boolean }>();
defineEmits<{ edit: [crn: string]; remove: [crn: string] }>();

const PHASE_LABEL: Record<Phase, string> = { "Phase One": "Phase 1", "Phase Two": "Phase 2" };
</script>

<template>
	<div class="overflow-x-auto rounded-4 border border-outline-gray-2">
		<table class="w-full text-start text-sm">
			<thead class="bg-desk text-xs text-ink-gray-6">
				<tr>
					<th class="px-4 py-2.5 text-start font-medium">{{ __("Name") }}</th>
					<th class="px-4 py-2.5 text-start font-medium">{{ __("CRN") }}</th>
					<th class="px-4 py-2.5 text-start font-medium">{{ __("City") }}</th>
					<th v-if="rows.some((r) => r.phase)" class="px-4 py-2.5 text-start font-medium">{{ __("Phase") }}</th>
					<th v-if="actions" class="w-24 px-4 py-2.5" />
				</tr>
			</thead>
			<tbody class="divide-y divide-outline-gray-1">
				<tr v-for="row in rows" :key="row.commercial_register_number" class="bg-white">
					<td class="px-4 py-3 font-medium text-ink-gray-9">{{ row.commercial_register_name }}</td>
					<td class="px-4 py-3 font-mono text-ink-gray-7">{{ row.commercial_register_number }}</td>
					<td class="px-4 py-3 text-ink-gray-7">
						{{ row.city }}<span v-if="row.district" class="text-ink-gray-5"> · {{ row.district }}</span>
					</td>
					<td v-if="row.phase" class="px-4 py-3">
						<Badge :label="__(PHASE_LABEL[row.phase] ?? row.phase)" :theme="row.phase === 'Phase Two' ? 'violet' : 'amber'" />
					</td>
					<td v-if="actions" class="px-4 py-2 text-end">
						<div class="flex justify-end gap-1">
							<Button
								variant="ghost"
								icon="lucide-pencil"
								:tooltip="__('Edit')"
								:aria-label="__('Edit')"
								:disabled="disabled"
								@click="$emit('edit', row.commercial_register_number)"
							/>
							<Button
								variant="ghost"
								theme="red"
								icon="lucide-trash-2"
								:tooltip="__('Remove')"
								:aria-label="__('Remove')"
								:disabled="disabled"
								@click="$emit('remove', row.commercial_register_number)"
							/>
						</div>
					</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>
