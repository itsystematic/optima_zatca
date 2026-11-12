<script setup lang="ts">
import { SUPPORT_LINKS } from "@/links";
import { __ } from "@/translate";

const links = [
	{ href: SUPPORT_LINKS.docs, icon: "lucide-book-open", label: __("Docs") },
	{ href: SUPPORT_LINKS.youtube, icon: "lucide-square-play", label: __("YouTube") },
	{ href: SUPPORT_LINKS.website, icon: "lucide-globe", label: __("Website") },
	{ href: SUPPORT_LINKS.whatsapp, icon: "lucide-message-circle", label: __("Help") },
];
</script>

<template>
	<nav class="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-ink-gray-6">
		<a
			v-for="link in links"
			:key="link.href"
			:href="link.href"
			target="_blank"
			rel="noopener"
			class="inline-flex items-center gap-1.5 hover:text-brand"
		>
			<span :class="link.icon" class="size-4" aria-hidden="true" />
			{{ link.label }}
		</a>
		<div class="grow" />
		<slot />
	</nav>
</template>
