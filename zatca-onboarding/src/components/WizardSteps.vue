<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { __ } from "@/translate";
import { draft } from "@/wizard";

const route = useRoute();
const router = useRouter();

const steps = computed(() => {
	const all = [
		{ label: __("Phase"), routes: ["phase", "type"] },
		{ label: __("Company"), routes: ["company"] },
		{ label: __("Registers"), routes: ["registers"] },
		{ label: __("Review", undefined, "onboarding"), routes: ["review"] },
	];
	return draft.mode === "adding" ? all.slice(2) : all;
});

const current = computed(() => steps.value.findIndex((s) => s.routes.includes(route.name as string)));
</script>

<template>
	<ol class="mb-6 flex items-center gap-2 text-sm">
		<li v-for="(step, i) in steps" :key="step.label" class="flex flex-1 items-center gap-2 last:flex-none">
			<button
				type="button"
				class="flex items-center gap-2 whitespace-nowrap"
				:class="i < current ? 'cursor-pointer text-ink-gray-8 hover:text-brand' : 'cursor-default'"
				:disabled="i >= current"
				@click="router.push({ name: step.routes[0] })"
			>
				<span
					class="flex size-6 items-center justify-center rounded-full text-xs font-medium"
					:class="
						i < current
							? 'bg-brand text-white'
							: i === current
								? 'bg-brand-tint text-brand ring-1 ring-brand'
								: 'bg-white text-ink-gray-5 ring-1 ring-line'
					"
				>
					<span v-if="i < current" class="lucide-check size-3.5" aria-hidden="true" />
					<template v-else>{{ i + 1 }}</template>
				</span>
				<span :class="i === current ? 'font-medium text-ink-gray-9' : 'text-ink-gray-6'">{{ step.label }}</span>
			</button>
			<span v-if="i < steps.length - 1" class="h-px flex-1" :class="i < current ? 'bg-brand' : 'bg-line'" />
		</li>
	</ol>
</template>
