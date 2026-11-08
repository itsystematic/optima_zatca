<script setup lang="ts">
import ITMark from "@/components/ITMark.vue";

withDefaults(defineProps<{ width?: string; center?: boolean }>(), {
	width: "max-w-4xl",
	center: false,
});
</script>

<template>
	<div class="flex min-h-screen flex-col">
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
