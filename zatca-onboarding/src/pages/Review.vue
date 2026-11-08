<script setup lang="ts">
import { Button, Checkbox, Dialog } from "frappe-ui";
import { ref } from "vue";
import { useRouter } from "vue-router";
import AppFrame from "@/components/AppFrame.vue";
import OtpDialog from "@/components/OtpDialog.vue";
import RegisterForm from "@/components/RegisterForm.vue";
import RegistersTable from "@/components/RegistersTable.vue";
import WizardSteps from "@/components/WizardSteps.vue";
import { startRun } from "@/run";
import type { CommercialRegister, RegisterField } from "@/types";
import { isClean, normalizeRegister, validateRegister, type Errors } from "@/validation";
import { draft, removeRegister, saveRegister, toPayload } from "@/wizard";

const router = useRouter();

const confirmed = ref(false);
const otpOpen = ref(false);

const editing = ref<CommercialRegister | null>(null);
const editErrors = ref<Errors<RegisterField>>({});

function edit(crn: string) {
	const register = draft.commercial_register.find((r) => r.commercial_register_number === crn);
	editErrors.value = {};
	editing.value = register ? { ...register } : null;
}

function saveEdit() {
	const register = normalizeRegister(editing.value!);
	// The CRN is locked while editing, so there is no other register it could collide with.
	editErrors.value = validateRegister(register);
	if (!isClean(editErrors.value)) return;
	saveRegister(register);
	editing.value = null;
}

function remove(crn: string) {
	removeRegister(crn);
	if (!draft.commercial_register.length) router.push({ name: "registers" });
}

function connect(otps: Record<string, string>) {
	for (const r of draft.commercial_register) r.otp = otps[r.commercial_register_number];
	startRun(toPayload(draft));
	router.replace({ name: "progress" });
}
</script>

<template>
	<AppFrame>
		<WizardSteps />
		<div class="card space-y-6 p-8">
			<div>
				<h1 class="text-3xl font-semibold text-navy">{{ __("Review", undefined, "onboarding") }}</h1>
				<p class="mt-1 text-sm text-ink-gray-6">
					{{ draft.company }} · <span class="font-mono">{{ draft.tax_id }}</span>
				</p>
			</div>
			<RegistersTable :rows="draft.commercial_register" actions :disabled="confirmed" @edit="edit" @remove="remove" />
			<Checkbox v-model="confirmed" :label="__('I confirm this data is correct')" />
			<div class="flex items-center gap-2">
				<Button variant="ghost" size="md" icon-left="lucide-arrow-left" :label="__('Back', undefined, 'onboarding')" @click="router.push({ name: 'registers' })" />
				<div class="grow" />
				<Button
					variant="solid"
					size="md"
					class="btn-brand"
					:disabled="!confirmed"
					:label="__('Enter OTPs')"
					@click="otpOpen = true"
				/>
			</div>
		</div>

		<OtpDialog v-model:open="otpOpen" :registers="draft.commercial_register" @connect="connect" />

		<Dialog :open="!!editing" :title="__('Edit commercial register')" size="2xl" @update:open="(v: boolean) => !v && (editing = null)">
			<RegisterForm v-if="editing" v-model="editing" :errors="editErrors" crn-locked />
			<template #actions>
				<div class="flex justify-end gap-2">
					<Button variant="ghost" size="md" :label="__('Cancel')" @click="editing = null" />
					<Button variant="solid" size="md" class="btn-brand" :label="__('Save')" @click="saveEdit" />
				</div>
			</template>
		</Dialog>
	</AppFrame>
</template>
