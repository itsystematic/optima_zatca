<script setup lang="ts">
import { FormControl } from "frappe-ui";
import { computed } from "vue";
import { __ } from "@/translate";
import type { CommercialRegister, RegisterField } from "@/types";
import { ADDRESS_COLUMNS, REGISTER_FIELDS, type Errors, type FieldSpec } from "@/validation";

const register = defineModel<CommercialRegister>({ required: true });
const props = defineProps<{ errors: Errors<RegisterField>; crnLocked?: boolean }>();

// v15 asked for the address only once the register itself was identified.
const showAddress = computed(
	() =>
		props.crnLocked ||
		(register.value.commercial_register_name.trim() !== "" &&
			/^\d{10}$/.test(register.value.commercial_register_number.trim())),
);

function attrs(spec: FieldSpec) {
	return {
		label: __(spec.label),
		required: spec.required,
		error: props.errors[spec.key] ? __(props.errors[spec.key]!) : undefined,
		maxlength: spec.maxlength,
		inputmode: spec.numeric ? "numeric" : undefined,
		size: "md" as const,
		variant: "outline" as const,
	};
}
</script>

<template>
	<div class="space-y-5">
		<div class="grid gap-4 sm:grid-cols-2">
			<FormControl
				v-for="spec in REGISTER_FIELDS"
				:key="spec.key"
				v-model="register[spec.key]"
				v-bind="attrs(spec)"
				:disabled="crnLocked && spec.key === 'commercial_register_number'"
				:class="{ 'mono-input': spec.numeric }"
			/>
		</div>

		<template v-if="showAddress">
			<div class="text-sm font-medium text-ink-gray-7">{{ __("National address") }}</div>
			<div class="grid gap-4 sm:grid-cols-2">
				<div v-for="(column, c) in ADDRESS_COLUMNS" :key="c" class="space-y-4">
					<FormControl
						v-for="spec in column"
						:key="spec.key"
						v-model="register[spec.key]"
						v-bind="attrs(spec)"
						:class="{ 'mono-input': spec.numeric }"
					/>
				</div>
			</div>
		</template>
	</div>
</template>
