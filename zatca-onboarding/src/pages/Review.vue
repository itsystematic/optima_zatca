<script setup lang="ts">
import { Badge, Button, Checkbox, Dialog } from "frappe-ui";
import { ref } from "vue";
import { useRouter } from "vue-router";
import AppFrame from "@/components/AppFrame.vue";
import OtpDialog from "@/components/OtpDialog.vue";
import RegisterForm from "@/components/RegisterForm.vue";
import RegistersTable from "@/components/RegistersTable.vue";
import WizardSteps from "@/components/WizardSteps.vue";
import { boot } from "@/boot";
import { ENVIRONMENT_TEXT } from "@/environments";
import { startRun } from "@/run";
import type { CommercialRegister, RegisterField } from "@/types";
import { isClean, normalizeRegister, validateRegister, type Errors } from "@/validation";
import { draft, removeRegister, resetDraft, saveRegister, toPayload } from "@/wizard";

const router = useRouter();

const connecting = draft.mode === "connecting";

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

function back() {
	if (connecting) {
		resetDraft();
		router.push({ name: "registered" });
	} else {
		router.push({ name: "registers" });
	}
}

function connect(otps: Record<string, string>) {
	for (const r of draft.commercial_register) r.otp = otps[r.commercial_register_number] ?? "";
	startRun(toPayload(draft));
	router.replace({ name: "progress" });
}
</script>

<template>
	<AppFrame>
		<WizardSteps v-if="!connecting" />
		<div class="card space-y-6 p-8">
			<div>
				<div class="flex items-center gap-3">
					<h1 class="text-3xl font-semibold text-navy">{{ __("Review", undefined, "onboarding") }}</h1>
					<Badge
						v-if="connecting"
						size="lg"
						theme="blue"
						:label="__(ENVIRONMENT_TEXT[draft.environment].label, undefined, 'onboarding')"
					/>
				</div>
				<p class="mt-1 text-sm text-ink-gray-6">
					{{ draft.company }} · <span class="font-mono">{{ draft.tax_id }}</span>
				</p>
			</div>
			<fieldset v-if="!connecting" :disabled="confirmed">
				<legend class="text-sm font-medium text-ink-gray-7">{{ __("Environment") }}</legend>
				<div class="mt-2 grid gap-3" :class="boot.environments.length > 2 ? 'sm:grid-cols-3' : 'sm:grid-cols-2'">
					<label
						v-for="e in boot.environments"
						:key="e"
						class="choice cursor-pointer !gap-1.5 !p-4 has-[:disabled]:cursor-default has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-brand"
						:class="{ '!border-brand ring-1 ring-brand': draft.environment === e }"
					>
						<input v-model="draft.environment" type="radio" name="environment" :value="e" class="sr-only" />
						<span class="flex items-center gap-2">
							<span :class="ENVIRONMENT_TEXT[e].icon" class="size-4 text-brand" aria-hidden="true" />
							<span class="font-semibold text-ink-gray-9">{{ __(ENVIRONMENT_TEXT[e].label, undefined, "onboarding") }}</span>
						</span>
						<span class="text-sm text-ink-gray-6">{{ __(ENVIRONMENT_TEXT[e].help) }}</span>
					</label>
				</div>
			</fieldset>
			<p v-if="connecting && draft.locked" class="text-sm text-ink-gray-6">
				{{ __("These details are already in a ZATCA certificate, so they are sent as they are.") }}
			</p>
			<RegistersTable
				:rows="draft.commercial_register"
				:actions="!(connecting && draft.locked)"
				:removable="!connecting"
				:disabled="confirmed"
				@edit="edit"
				@remove="remove"
			/>
			<Checkbox v-model="confirmed" :label="__('I confirm this data is correct')" />
			<div class="flex items-center gap-2">
				<Button variant="ghost" size="md" icon-left="lucide-arrow-left" :label="__('Back', undefined, 'onboarding')" @click="back" />
				<div class="grow" />
				<Button
					v-if="draft.resuming"
					variant="solid"
					size="md"
					class="btn-brand"
					:disabled="!confirmed"
					:label="__('Resume')"
					@click="connect({})"
				/>
				<Button
					v-else
					variant="solid"
					size="md"
					class="btn-brand"
					:disabled="!confirmed"
					:label="__('Enter OTPs')"
					@click="otpOpen = true"
				/>
			</div>
		</div>

		<OtpDialog v-model:open="otpOpen" :registers="draft.commercial_register" :environment="draft.environment" @connect="connect" />

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
