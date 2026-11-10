<script setup lang="ts">
import { Button, ErrorMessage, FormControl } from "frappe-ui";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { getCompanies } from "@/api";
import AppFrame from "@/components/AppFrame.vue";
import WizardSteps from "@/components/WizardSteps.vue";
import { errorText } from "@/run";
import { __ } from "@/translate";
import type { Company } from "@/types";
import { isClean, validateCompany, type CompanyField, type Errors } from "@/validation";
import { draft } from "@/wizard";

const router = useRouter();

const form = reactive({
	company: draft.company,
	company_name_in_arabic: draft.company_name_in_arabic,
	tax_id: draft.tax_id,
});
const errors = ref<Errors<CompanyField>>({});
const companies = ref<Company[]>([]);
const loadError = ref("");
// The select positions its menu for the options it has when opened, so it waits for them.
const loading = ref(true);

const options = computed(() => companies.value.map((c) => ({ label: c.name, value: c.name })));

onMounted(async () => {
	try {
		companies.value = await getCompanies();
		if (!form.company && companies.value.length === 1) form.company = companies.value[0].name;
	} catch (error) {
		loadError.value = errorText(error);
	} finally {
		loading.value = false;
	}
});

// Fill what the Company record already knows, without overwriting what was typed.
watch([() => form.company, companies], () => {
	const company = companies.value.find((c) => c.name === form.company);
	if (!company) return;
	form.company_name_in_arabic ||= company.company_name_in_arabic ?? "";
	form.tax_id ||= company.tax_id ?? "";
});

function next() {
	errors.value = validateCompany(form);
	if (!isClean(errors.value)) return;
	if (draft.company !== form.company) draft.commercial_register = [];
	Object.assign(draft, {
		company: form.company,
		company_name_in_arabic: form.company_name_in_arabic.trim(),
		tax_id: form.tax_id.trim(),
	});
	router.push({ name: "registers" });
}

const error = (field: CompanyField) => (errors.value[field] ? __(errors.value[field]!) : undefined);
</script>

<template>
	<AppFrame>
		<WizardSteps />
		<form class="card space-y-5 p-8" novalidate @submit.prevent="next">
			<h1 class="text-3xl font-semibold text-navy">{{ __("Company") }}</h1>
			<ErrorMessage v-if="loadError" :message="loadError" />
			<FormControl
				v-model="form.company"
				type="select"
				size="md"
				variant="outline"
				:label="__('Company')"
				:placeholder="__('Select a company')"
				:options="options"
				:disabled="loading"
				:error="error('company')"
				required
			/>
			<FormControl
				v-model="form.company_name_in_arabic"
				size="md"
				variant="outline"
				dir="rtl"
				:label="__('Company name (Arabic)')"
				:error="error('company_name_in_arabic')"
				required
			/>
			<FormControl
				v-model="form.tax_id"
				size="md"
				variant="outline"
				class="mono-input"
				inputmode="numeric"
				:maxlength="15"
				:label="__('VAT number')"
				:description="__('15 digits, starting and ending with 3')"
				:error="error('tax_id')"
				required
			/>
			<div class="flex justify-end pt-2">
				<Button type="submit" variant="solid" size="md" class="btn-brand" icon-right="lucide-arrow-right" :label="__('Next')" />
			</div>
		</form>
	</AppFrame>
</template>
