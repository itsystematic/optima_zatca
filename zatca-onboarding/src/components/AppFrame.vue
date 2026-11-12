<script setup lang="ts">
import ITMark from "@/components/ITMark.vue";
import Skyline from "@/components/Skyline.vue";

/** `backdrop` lays the Landing card's skyline across the foot of the page, behind the content. */
withDefaults(defineProps<{ width?: string; center?: boolean; backdrop?: boolean }>(), {
	width: "max-w-4xl",
	center: false,
	backdrop: true,
});
</script>

<template>
	<div class="relative isolate flex min-h-screen flex-col">
		<div v-if="backdrop" class="pointer-events-none fixed inset-x-0 bottom-0 -z-10 opacity-40">
			<Skyline height="auto" />
		</div>
		<header class="flex h-16 flex-none items-center gap-3 px-6 sm:px-10">
			<ITMark :size="40" />
			<div class="grow" />
			<slot name="status" />
		</header>
		<main class="flex flex-1 justify-center px-4 pb-12 sm:px-10" :class="{ 'items-center': center }">
			<div class="w-full" :class="width">
				<slot />
			</div>
		</main>
	</div>
</template>
