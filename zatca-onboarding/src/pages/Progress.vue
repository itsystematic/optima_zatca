<script setup lang="ts">
import { Badge, Button } from "frappe-ui";
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import AppFrame from "@/components/AppFrame.vue";
import OtpDialog from "@/components/OtpDialog.vue";
import StageBar from "@/components/StageBar.vue";
import { ENVIRONMENT_TEXT } from "@/environments";
import { currentStep, currentTestNumber, TEST_INVOICES, type RowProgress } from "@/progress";
import { board, finishRun, retry, run, totals } from "@/run";
import { __ } from "@/translate";
import type { CommercialRegister } from "@/types";

const router = useRouter();

watch(
	totals,
	(t) => {
		if (t.total && t.live === t.total) router.replace({ name: "done" });
	},
	{ immediate: true },
);

const title = computed(() => {
	const { total, live, settled } = totals.value;
	if (settled) return __("{0} of {1} connected", [live, total]);
	return total === 1
		? __("Connecting 1 commercial register")
		: __("Connecting {0} commercial registers", [total]);
});

const FAILED_AT = {
	request: __("Could not start"),
	csid: __("Compliance certificate refused"),
	tests: __("Test invoice rejected"),
	pcsid: __("Production certificate refused"),
};

function status(p: RowProgress): string {
	if (p.state === "waiting") return __("Waiting");
	if (p.state === "live") return __("Connected");
	if (p.state === "failed") return p.failedAt ? FAILED_AT[p.failedAt] : __("Failed");
	const step = currentStep(p);
	if (step === "csid") return __("Requesting compliance certificate");
	if (step === "tests") return __("Test invoice {0} of {1}", [currentTestNumber(p), TEST_INVOICES]);
	return __("Requesting production certificate");
}

const otpFor = ref<CommercialRegister | null>(null);
const otpOpen = computed({
	get: () => !!otpFor.value,
	set: (open: boolean) => {
		if (!open) otpFor.value = null;
	},
});

function onRetry(register: CommercialRegister, p: RowProgress) {
	// A refused CSID is retried with a new OTP; past the CSID the backend no longer reads it.
	if (p.csid !== "ok") otpFor.value = register;
	else retry(register.commercial_register_number);
}

function retryWithOtp(otps: Record<string, string>) {
	const [[crn, otp]] = Object.entries(otps);
	retry(crn, otp);
}

function backToRegisters() {
	finishRun().finally(() => router.push({ name: "landing" }));
}
</script>

<template>
	<AppFrame width="max-w-5xl">
		<div class="card overflow-hidden">
			<div class="flex items-center gap-6 border-b border-outline-gray-1 px-8 py-6">
				<div class="flex flex-1 items-center gap-3">
					<h1 class="text-3xl font-semibold text-navy">{{ title }}</h1>
					<Badge
						v-if="run.payload"
						size="lg"
						theme="blue"
						:label="__(ENVIRONMENT_TEXT[run.payload.environment].label, undefined, 'onboarding')"
					/>
				</div>
				<div class="w-48 space-y-1.5">
					<div class="text-end text-sm text-ink-gray-6">
						{{ __("{0} of {1} done", [totals.live, totals.total]) }}
					</div>
					<div class="flex h-1.5 overflow-hidden rounded-full bg-hair">
						<div class="bg-ok transition-all" :style="{ width: `${(totals.live / totals.total) * 100}%` }" />
						<div class="bg-danger transition-all" :style="{ width: `${(totals.failed / totals.total) * 100}%` }" />
					</div>
				</div>
			</div>

			<ul class="divide-y divide-outline-gray-1">
				<li
					v-for="{ register, progress } in board"
					:key="register.commercial_register_number"
					class="grid items-center gap-x-6 gap-y-3 px-8 py-5 md:grid-cols-[12rem_1fr_18rem]"
				>
					<div class="min-w-0">
						<div class="truncate font-medium text-ink-gray-9">{{ register.commercial_register_name }}</div>
						<div class="font-mono text-xs text-ink-gray-5">{{ register.commercial_register_number }}</div>
					</div>
					<StageBar :progress="progress" />
					<div class="flex min-w-0 items-center gap-3">
						<span
							v-if="progress.state === 'running'"
							class="lucide-loader-circle size-4 flex-none animate-spin text-warn"
							aria-hidden="true"
						/>
						<span v-else-if="progress.state === 'live'" class="lucide-circle-check size-4 flex-none text-ok" aria-hidden="true" />
						<span v-else-if="progress.state === 'failed'" class="lucide-circle-alert size-4 flex-none text-danger" aria-hidden="true" />
						<span
							class="min-w-0 flex-1 truncate text-sm"
							:class="progress.state === 'failed' ? 'text-danger' : 'text-ink-gray-7'"
							:title="status(progress)"
						>
							{{ status(progress) }}
						</span>
						<Button
							v-if="progress.state === 'failed'"
							size="sm"
							variant="outline"
							icon-left="lucide-rotate-ccw"
							:label="__('Retry')"
							:disabled="!totals.settled"
							@click="onRetry(register, progress)"
						/>
					</div>
					<p
						v-if="progress.state === 'failed' && progress.message"
						dir="auto"
						class="truncate rounded-4 bg-danger-tint px-3 py-1.5 font-mono text-xs text-danger md:col-span-2 md:col-start-2"
						:title="progress.message"
					>
						{{ progress.message }}
					</p>
				</li>
			</ul>

			<footer v-if="totals.settled" class="flex items-center gap-4 border-t border-outline-gray-1 bg-desk px-8 py-4">
				<p class="flex-1 text-sm text-ink-gray-6">{{ __("Connected registers stay connected while you retry the others.") }}</p>
				<Button variant="ghost" size="md" :label="__('Back to registers')" @click="backToRegisters" />
			</footer>
		</div>

		<OtpDialog
			v-model:open="otpOpen"
			:registers="otpFor ? [otpFor] : []"
			:environment="run.payload?.environment ?? 'production'"
			@connect="retryWithOtp"
		/>
	</AppFrame>
</template>
