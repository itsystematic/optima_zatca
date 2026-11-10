import { createRouter, createWebHistory } from "vue-router";
import { loadRegistered } from "@/registered";
import { run, totals } from "@/run";
import { draft, guardRedirect, type WizardRoute } from "@/wizard";

const WIZARD: WizardRoute[] = ["phase", "type", "company", "registers", "review"];

const router = createRouter({
	history: createWebHistory("/zatca-onboarding"),
	routes: [
		{ path: "/", name: "landing", component: () => import("@/pages/Landing.vue") },
		{ path: "/registered", name: "registered", component: () => import("@/pages/Registered.vue") },
		{ path: "/phase", name: "phase", component: () => import("@/pages/Phase.vue") },
		{ path: "/type", name: "type", component: () => import("@/pages/RegisterType.vue") },
		{ path: "/company", name: "company", component: () => import("@/pages/Company.vue") },
		{ path: "/registers", name: "registers", component: () => import("@/pages/Registers.vue") },
		{ path: "/review", name: "review", component: () => import("@/pages/Review.vue") },
		{ path: "/progress", name: "progress", component: () => import("@/pages/Progress.vue") },
		{ path: "/done", name: "done", component: () => import("@/pages/Done.vue") },
		{ path: "/:rest(.*)*", redirect: "/" },
	],
});

router.beforeEach(async (to) => {
	const name = to.name as string;

	if (name === "landing" || name === "registered") {
		const rows = await loadRegistered().catch(() => []);
		if (name === "landing" && rows.length) return { name: "registered" };
		if (name === "registered" && !rows.length) return { name: "landing" };
		return true;
	}
	if (name === "progress") return run.active || { name: "landing" };
	if (name === "done") return (run.active && totals.value.live === totals.value.total) || { name: "landing" };

	if (run.active) return { name: "progress" };
	const redirect = WIZARD.includes(name as WizardRoute) && guardRedirect(name as WizardRoute, draft);
	return redirect ? { name: redirect } : true;
});

export default router;
