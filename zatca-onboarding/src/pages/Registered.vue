<script setup lang="ts">
import { Button } from "frappe-ui";
import { computed } from "vue";
import { useRouter } from "vue-router";
import AppFrame from "@/components/AppFrame.vue";
import ConnectionsTable from "@/components/ConnectionsTable.vue";
import FooterLinks from "@/components/FooterLinks.vue";
import { groupByRegister, type RegisterConnections } from "@/environments";
import { registered } from "@/registered";
import type { Environment } from "@/types";
import { startAdding, startConnecting } from "@/wizard";

const router = useRouter();

const groups = computed(() => groupByRegister(registered.value));

function addRegister() {
	startAdding(registered.value[0]);
	router.push({ name: "registers" });
}

function connect(group: RegisterConnections, environment: Environment) {
	startConnecting(group, environment);
	router.push({ name: "review" });
}
</script>

<template>
	<AppFrame width="max-w-5xl">
		<div class="card overflow-hidden">
			<div class="flex items-center gap-4 px-8 pb-5 pt-8">
				<div class="min-w-0 flex-1">
					<h1 class="text-3xl font-semibold text-navy">{{ __("Commercial registers") }}</h1>
					<p class="mt-1 text-sm text-ink-gray-6">{{ registered[0]?.company }}</p>
				</div>
				<Button variant="solid" size="md" class="btn-brand" icon-left="lucide-plus" :label="__('Add CR')" @click="addRegister" />
			</div>
			<div class="px-8 pb-8">
				<ConnectionsTable :groups="groups" @connect="connect" />
			</div>
			<footer class="border-t border-outline-gray-1 bg-desk px-8 py-4">
				<FooterLinks />
			</footer>
		</div>
	</AppFrame>
</template>
