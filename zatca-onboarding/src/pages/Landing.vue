<script setup lang="ts">
import { Button } from "frappe-ui";
import { useRouter } from "vue-router";
import AppFrame from "@/components/AppFrame.vue";
import FooterLinks from "@/components/FooterLinks.vue";
import ITMark from "@/components/ITMark.vue";
import Skyline from "@/components/Skyline.vue";
import { resetDraft } from "@/wizard";

const router = useRouter();

function start() {
	resetDraft();
	router.push({ name: "phase" });
}
</script>

<template>
	<AppFrame width="max-w-5xl" center>
		<div class="card overflow-hidden">
			<div class="space-y-6 px-8 pb-4 pt-14 sm:px-20">
				<h1 class="max-w-2xl text-8xl font-semibold tracking-tight text-navy sm:text-9xl">
					{{ __("Connect your company to ZATCA") }}
				</h1>
				<p class="max-w-xl text-xl leading-relaxed text-ink-gray-6">
					{{ __("Register your commercial registers and get certified for e-invoicing.") }}
				</p>
				<Button variant="solid" size="lg" class="btn-brand" icon-right="lucide-arrow-right" :label="__('Get started')" @click="start" />
			</div>
			<Skyline />
			<footer class="border-t border-outline-gray-1 bg-desk px-8 py-5 sm:px-20">
				<FooterLinks>
					<ITMark :size="28" />
				</FooterLinks>
			</footer>
		</div>
	</AppFrame>
</template>
