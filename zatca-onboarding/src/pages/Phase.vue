<script setup lang="ts">
import { useRouter } from "vue-router";
import AppFrame from "@/components/AppFrame.vue";
import WizardSteps from "@/components/WizardSteps.vue";
import { __ } from "@/translate";
import type { Phase } from "@/types";
import { draft } from "@/wizard";

const router = useRouter();

const PHASES: { value: Phase; icon: string; title: string; help: string }[] = [
	{ value: "Phase One", icon: "lucide-qr-code", title: __("Phase 1"), help: __("QR code only") },
	{ value: "Phase Two", icon: "lucide-link", title: __("Phase 2"), help: __("Integration with ZATCA") },
];

function choose(phase: Phase) {
	draft.phase = phase;
	router.push({ name: "type" });
}
</script>

<template>
	<AppFrame>
		<WizardSteps />
		<div class="card p-8">
			<h1 class="text-3xl font-semibold text-navy">{{ __("Which phase is your company in?") }}</h1>
			<div class="mt-6 grid gap-4 sm:grid-cols-2">
				<button
					v-for="p in PHASES"
					:key="p.value"
					type="button"
					class="choice"
					:class="{ '!border-brand ring-1 ring-brand': draft.phase === p.value }"
					@click="choose(p.value)"
				>
					<span class="flex size-10 items-center justify-center rounded-full bg-brand-tint text-brand">
						<span :class="p.icon" class="size-5" aria-hidden="true" />
					</span>
					<span class="text-lg font-semibold text-ink-gray-9">{{ p.title }}</span>
					<span class="text-sm text-ink-gray-6">{{ p.help }}</span>
				</button>
			</div>
		</div>
	</AppFrame>
</template>
