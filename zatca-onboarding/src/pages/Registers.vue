<script setup lang="ts">
import { Button } from "frappe-ui";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import AppFrame from "@/components/AppFrame.vue";
import RegisterForm from "@/components/RegisterForm.vue";
import WizardSteps from "@/components/WizardSteps.vue";
import { loadRegistered, registered } from "@/registered";
import type { CommercialRegister, RegisterField } from "@/types";
import { isClean, normalizeRegister, validateRegister, type Errors } from "@/validation";
import { draft, emptyRegister, removeRegister, resetDraft, saveRegister } from "@/wizard";

const router = useRouter();

const multi = computed(() => draft.register_type === "multi" || draft.adding);
const form = ref<CommercialRegister>(multi.value ? emptyRegister() : { ...(draft.commercial_register[0] ?? emptyRegister()) });
const errors = ref<Errors<RegisterField>>({});

onMounted(() => loadRegistered().catch(() => {}));

function add(): boolean {
	const register = normalizeRegister(form.value);
	errors.value = validateRegister(register, {
		registered: registered.value.map((r) => r.commercial_register_number),
		// A single register replaces the draft's one, so it cannot collide with it.
		added: multi.value ? draft.commercial_register.map((r) => r.commercial_register_number) : [],
	});
	if (!isClean(errors.value)) return false;
	if (multi.value) {
		saveRegister(register);
		form.value = emptyRegister();
	} else {
		draft.commercial_register = [register];
	}
	return true;
}

const isBlank = (r: CommercialRegister) => Object.values(r).every((v) => !String(v).trim());

function next() {
	// A half-typed register would otherwise be dropped without a word.
	if (!multi.value || !isBlank(form.value) || !draft.commercial_register.length) {
		if (!add()) return;
	}
	router.push({ name: "review" });
}

function back() {
	if (draft.adding) {
		resetDraft();
		router.push({ name: "registered" });
	} else {
		router.push({ name: "company" });
	}
}
</script>

<template>
	<AppFrame>
		<WizardSteps />
		<div class="flex flex-col gap-4 lg:flex-row lg:items-start">
			<aside v-if="multi" class="card w-full flex-none p-5 lg:w-72">
				<div class="text-sm font-medium text-ink-gray-7">
					{{ __("Added") }} <span class="text-ink-gray-5">({{ draft.commercial_register.length }})</span>
				</div>
				<p v-if="!draft.commercial_register.length" class="mt-3 text-sm text-ink-gray-5">
					{{ __("Registers you add appear here.") }}
				</p>
				<ul class="mt-3 space-y-2">
					<li
						v-for="r in draft.commercial_register"
						:key="r.commercial_register_number"
						class="flex items-center gap-2 rounded-4 border border-outline-gray-1 bg-desk px-3 py-2"
					>
						<div class="min-w-0 flex-1">
							<div class="truncate text-sm font-medium">{{ r.commercial_register_name }}</div>
							<div class="font-mono text-xs text-ink-gray-5">{{ r.commercial_register_number }}</div>
						</div>
						<Button
							variant="ghost"
							theme="red"
							icon="lucide-trash-2"
							:tooltip="__('Remove')"
							:aria-label="__('Remove')"
							@click="removeRegister(r.commercial_register_number)"
						/>
					</li>
				</ul>
			</aside>

			<form class="card min-w-0 flex-1 space-y-6 p-8" novalidate @submit.prevent="multi ? add() : next()">
				<h1 class="text-3xl font-semibold text-navy">
					{{ multi ? __("Add commercial registers") : __("Commercial register") }}
				</h1>
				<RegisterForm v-model="form" :errors="errors" />
				<div class="flex items-center gap-2 pt-2">
					<Button variant="ghost" size="md" icon-left="lucide-arrow-left" :label="__('Back', undefined, 'onboarding')" @click="back" />
					<div class="grow" />
					<Button v-if="multi" type="submit" variant="outline" size="md" icon-left="lucide-plus" :label="__('Add')" />
					<Button
						variant="solid"
						size="md"
						class="btn-brand"
						icon-right="lucide-arrow-right"
						:label="__('Next')"
						@click="next"
					/>
				</div>
			</form>
		</div>
	</AppFrame>
</template>
