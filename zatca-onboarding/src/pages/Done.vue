<script setup lang="ts">
import { Button } from "frappe-ui";
import { computed } from "vue";
import { useRouter } from "vue-router";
import AppFrame from "@/components/AppFrame.vue";
import { NEW_SALES_INVOICE_URL, SUPPORT_LINKS } from "@/links";
import { finishRun, run, totals } from "@/run";
import { __ } from "@/translate";

const router = useRouter();

const company = run.payload?.company ?? "";
const summary = computed(() =>
	totals.value.live === 1
		? __("1 commercial register is live.")
		: __("{0} commercial registers are live.", [totals.value.live]),
);

function backToRegisters() {
	finishRun().finally(() => router.push({ name: "landing" }));
}

function openNewInvoice() {
	window.location.href = NEW_SALES_INVOICE_URL;
}
</script>

<template>
	<AppFrame width="max-w-2xl" center>
		<div class="card flex flex-col items-center gap-5 px-8 py-12 text-center">
			<span class="flex size-14 items-center justify-center rounded-full bg-ok-tint text-ok">
				<span class="lucide-check size-7" aria-hidden="true" />
			</span>
			<div class="space-y-2">
				<h1 class="text-4xl font-semibold text-navy">{{ __("{0} is connected to ZATCA", [company]) }}</h1>
				<p class="text-ink-gray-6">{{ summary }}</p>
			</div>
			<div class="flex flex-wrap justify-center gap-2">
				<Button variant="solid" size="md" class="btn-brand" :label="__('New sales invoice')" @click="openNewInvoice" />
				<Button variant="outline" size="md" :label="__('Back to registers')" @click="backToRegisters" />
			</div>
			<a
				:href="SUPPORT_LINKS.whatsapp"
				target="_blank"
				rel="noopener"
				class="inline-flex items-center gap-1.5 text-sm text-ink-gray-6 hover:text-brand"
			>
				<span class="lucide-message-circle size-4" aria-hidden="true" />{{ __("WhatsApp support") }}
			</a>
		</div>
	</AppFrame>
</template>
