<script setup lang="ts">
import { useRouter } from "vue-router";
import AppFrame from "@/components/AppFrame.vue";
import WizardSteps from "@/components/WizardSteps.vue";
import { __ } from "@/translate";
import type { RegisterType } from "@/types";
import { draft } from "@/wizard";

const router = useRouter();

const TYPES: { value: RegisterType; icon: string; title: string; help: string }[] = [
	{ value: "main", icon: "lucide-building", title: __("Main CRN"), help: __("One commercial register") },
	{ value: "multi", icon: "lucide-building-2", title: __("Multiple CRNs"), help: __("A main register and its branches") },
];

function choose(type: RegisterType) {
	if (type === "main" && draft.commercial_register.length > 1) {
		draft.commercial_register = draft.commercial_register.slice(0, 1);
	}
	draft.register_type = type;
	router.push({ name: "company" });
}
</script>

<template>
	<AppFrame>
		<WizardSteps />
		<div class="card p-8">
			<h1 class="text-3xl font-semibold text-navy">{{ __("How many commercial registers?") }}</h1>
			<div class="mt-6 grid gap-4 sm:grid-cols-2">
				<button
					v-for="t in TYPES"
					:key="t.value"
					type="button"
					class="choice"
					:class="{ '!border-brand ring-1 ring-brand': draft.register_type === t.value }"
					@click="choose(t.value)"
				>
					<span class="flex size-10 items-center justify-center rounded-full bg-brand-tint text-brand">
						<span :class="t.icon" class="size-5" aria-hidden="true" />
					</span>
					<span class="text-lg font-semibold text-ink-gray-9">{{ t.title }}</span>
					<span class="text-sm text-ink-gray-6">{{ t.help }}</span>
				</button>
			</div>
		</div>
	</AppFrame>
</template>
