<script setup lang="ts">
import logoUrl from "@/assets/it-logo.webp";

withDefaults(defineProps<{ size?: number }>(), { size: 36 });
</script>

<template>
	<img
		:src="logoUrl"
		:width="size"
		:height="size"
		:style="{ width: `${size}px`, height: `${size}px` }"
		class="flex-none object-contain"
		alt="IT Systematic"
		draggable="false"
	/>
</template>
