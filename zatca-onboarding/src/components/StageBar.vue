<script setup lang="ts">
import { computed } from "vue";
import { currentStep, currentTestNumber, type Mark, type RowProgress } from "@/progress";
import { __ } from "@/translate";

const props = defineProps<{ progress: RowProgress }>();

type Cell = Mark | "running";

const cells = computed(() => {
	const p = props.progress;
	const running = p.state === "running" ? currentStep(p) : null;
	const testRunning = running === "tests" ? currentTestNumber(p) - 1 : -1;
	return {
		csid: (running === "csid" ? "running" : p.csid) as Cell,
		tests: p.tests.map((t, i) => (i === testRunning ? "running" : t)) as Cell[],
		pcsid: (running === "pcsid" ? "running" : p.pcsid) as Cell,
	};
});

const tone: Record<Cell, string> = {
	pending: "bg-hair",
	ok: "bg-ok",
	failed: "bg-danger",
	running: "bg-warn-band animate-pulse",
};
</script>

<template>
	<div class="flex items-start gap-3">
		<div class="w-14">
			<div class="h-2 rounded-full" :class="tone[cells.csid]" />
			<div class="mt-1 text-2xs text-ink-gray-5">{{ __("CSID") }}</div>
		</div>
		<div class="flex-1">
			<div class="flex gap-1">
				<div v-for="(cell, i) in cells.tests" :key="i" class="h-2 flex-1 rounded-full" :class="tone[cell]" />
			</div>
			<div class="mt-1 text-2xs text-ink-gray-5">{{ __("Test invoices") }}</div>
		</div>
		<div class="w-14">
			<div class="h-2 rounded-full" :class="tone[cells.pcsid]" />
			<div class="mt-1 text-2xs text-ink-gray-5">{{ __("PCSID") }}</div>
		</div>
	</div>
</template>
