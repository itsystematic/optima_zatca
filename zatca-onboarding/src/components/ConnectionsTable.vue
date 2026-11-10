<script setup lang="ts">
import { Badge, Button, Dropdown } from "frappe-ui";
import { boot } from "@/boot";
import { connectable, ENVIRONMENT_TEXT, type ConnectionStatus, type RegisterConnections } from "@/environments";
import { __ } from "@/translate";
import type { Environment, Phase } from "@/types";

defineProps<{ groups: RegisterConnections[] }>();
const emit = defineEmits<{ connect: [group: RegisterConnections, environment: Environment] }>();

const PHASE_LABEL: Record<Phase, string> = { "Phase One": "Phase 1", "Phase Two": "Phase 2" };
const STATUS: Record<ConnectionStatus, { label: string; dot: string }> = {
	connected: { label: "Connected", dot: "bg-ok" },
	in_progress: { label: "In progress", dot: "bg-warn" },
	not_connected: { label: "Not connected", dot: "bg-line" },
};

function envLabel(environment: Environment) {
	return __(ENVIRONMENT_TEXT[environment].label, undefined, "onboarding");
}

function actionLabel(group: RegisterConnections, environment: Environment) {
	const started = group.connections.some((c) => c.environment === environment);
	return started ? __("Resume {0}", [envLabel(environment)]) : __("Connect to {0}", [envLabel(environment)]);
}

function options(group: RegisterConnections) {
	return connectable(group, boot.environments).map((environment) => ({
		label: actionLabel(group, environment),
		onClick: () => emit("connect", group, environment),
	}));
}
</script>

<template>
	<div class="overflow-x-auto rounded-4 border border-outline-gray-2">
		<table class="w-full text-start text-sm">
			<thead class="bg-desk text-xs text-ink-gray-6">
				<tr>
					<th class="px-4 py-2.5 text-start font-medium">{{ __("Name") }}</th>
					<th class="px-4 py-2.5 text-start font-medium">{{ __("CRN") }}</th>
					<th class="px-4 py-2.5 text-start font-medium">{{ __("City") }}</th>
					<th class="px-4 py-2.5 text-start font-medium">{{ __("Phase") }}</th>
					<th class="px-4 py-2.5 text-start font-medium">{{ __("Environment") }}</th>
					<th class="px-4 py-2.5" />
				</tr>
			</thead>
			<tbody class="divide-y divide-outline-gray-1">
				<tr v-for="group in groups" :key="group.register.commercial_register_number" class="bg-white align-top">
					<td class="min-w-32 px-4 py-3 font-medium text-ink-gray-9">{{ group.register.commercial_register_name }}</td>
					<td class="px-4 py-3 font-mono text-ink-gray-7">{{ group.register.commercial_register_number }}</td>
					<td class="px-4 py-3 text-ink-gray-7">
						{{ group.register.city }}<span v-if="group.register.district" class="text-ink-gray-5"> · {{ group.register.district }}</span>
					</td>
					<td class="px-4 py-3">
						<Badge
							:label="__(PHASE_LABEL[group.register.phase] ?? group.register.phase)"
							:theme="group.register.phase === 'Phase Two' ? 'violet' : 'amber'"
						/>
					</td>
					<td class="px-4 py-3">
						<ul class="space-y-1.5">
							<li v-for="c in group.connections" :key="c.environment" class="flex items-center gap-2 whitespace-nowrap">
								<span class="size-2 flex-none rounded-full" :class="STATUS[c.status].dot" aria-hidden="true" />
								<span class="font-medium text-ink-gray-8">{{ envLabel(c.environment) }}</span>
								<span class="text-ink-gray-6">{{ __(STATUS[c.status].label) }}</span>
								<Badge v-if="c.usedForInvoices" theme="blue" :label="__('Invoices')" :title="__('Used for invoices')" />
							</li>
						</ul>
					</td>
					<td class="whitespace-nowrap px-4 py-2 text-end">
						<template v-if="options(group).length === 1">
							<Button variant="outline" icon-left="lucide-plug" :label="options(group)[0].label" @click="options(group)[0].onClick()" />
						</template>
						<Dropdown
							v-else-if="options(group).length"
							:options="options(group)"
							:button="{ label: __('Connect'), variant: 'outline', iconLeft: 'lucide-plug' }"
						/>
					</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>
