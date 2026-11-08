<script setup lang="ts">
import { Button, Dialog, FormControl } from "frappe-ui";
import { reactive, watch } from "vue";
import { FATOORA_URL } from "@/links";
import { __ } from "@/translate";
import type { CommercialRegister } from "@/types";
import { OTP_LENGTH, otpError } from "@/validation";

const open = defineModel<boolean>("open", { required: true });
const props = defineProps<{ registers: CommercialRegister[] }>();
const emit = defineEmits<{ connect: [otps: Record<string, string>] }>();

const otps = reactive<Record<string, string>>({});
const errors = reactive<Record<string, string | undefined>>({});

watch(open, (isOpen) => {
	if (!isOpen) return;
	for (const r of props.registers) {
		otps[r.commercial_register_number] = "";
		errors[r.commercial_register_number] = undefined;
	}
});

function connect() {
	let clean = true;
	for (const r of props.registers) {
		const crn = r.commercial_register_number;
		errors[crn] = otpError(otps[crn] ?? "");
		if (errors[crn]) clean = false;
	}
	if (!clean) return;
	emit("connect", Object.fromEntries(props.registers.map((r) => [r.commercial_register_number, otps[r.commercial_register_number].trim()])));
	open.value = false;
}
</script>

<template>
	<Dialog v-model:open="open" :title="__('Enter OTPs')" size="md">
		<form class="space-y-4" novalidate @submit.prevent="connect">
			<p class="text-sm text-ink-gray-6">
				{{ __("One code per commercial register, from the Fatoora portal.") }}
				<a :href="FATOORA_URL" target="_blank" rel="noopener" class="inline-flex items-center gap-1 font-medium text-brand hover:underline">
					{{ __("Get OTP from Fatoora") }}<span class="lucide-external-link size-3.5" aria-hidden="true" />
				</a>
			</p>
			<div v-for="r in registers" :key="r.commercial_register_number" class="flex items-start gap-4">
				<div class="min-w-0 flex-1 pt-1.5">
					<div class="truncate text-sm font-medium text-ink-gray-9">{{ r.commercial_register_name }}</div>
					<div class="font-mono text-xs text-ink-gray-5">{{ r.commercial_register_number }}</div>
				</div>
				<FormControl
					v-model="otps[r.commercial_register_number]"
					class="otp-input w-36"
					size="md"
					variant="outline"
					inputmode="numeric"
					autocomplete="one-time-code"
					:maxlength="OTP_LENGTH"
					:aria-label="__('OTP for {0}', [r.commercial_register_name])"
					:error="errors[r.commercial_register_number] ? __(errors[r.commercial_register_number]!) : undefined"
				/>
			</div>
			<button type="submit" class="hidden" />
		</form>
		<template #actions>
			<div class="flex justify-end">
				<Button variant="solid" size="md" class="btn-brand" :label="__('Connect')" @click="connect" />
			</div>
		</template>
	</Dialog>
</template>
