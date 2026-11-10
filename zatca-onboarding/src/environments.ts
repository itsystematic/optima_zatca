import type { Environment, RegisteredRow } from "@/types";

/** Production first: it is the one that matters once a register has it. */
export const ENVIRONMENT_ORDER: Environment[] = ["production", "simulation", "sandbox"];

export type ConnectionStatus = "connected" | "in_progress" | "not_connected";

export interface Connection {
	environment: Environment;
	status: ConnectionStatus;
	usedForInvoices: boolean;
}

/** A register with its settings, one per environment it was onboarded in. */
export interface RegisterConnections {
	register: RegisteredRow;
	connections: Connection[];
}

export function connectionStatus(row: Pick<RegisteredRow, "check_csid" | "check_pcsid">): ConnectionStatus {
	if (row.check_pcsid) return "connected";
	return row.check_csid ? "in_progress" : "not_connected";
}

export function groupByRegister(rows: RegisteredRow[]): RegisterConnections[] {
	const groups = new Map<string, RegisterConnections>();
	for (const row of rows) {
		const crn = row.commercial_register_number;
		const group = groups.get(crn) ?? { register: row, connections: [] };
		group.connections.push({
			environment: row.environment,
			status: connectionStatus(row),
			usedForInvoices: !!row.use_for_invoices,
		});
		groups.set(crn, group);
	}
	for (const group of groups.values()) {
		group.connections.sort(
			(a, b) => ENVIRONMENT_ORDER.indexOf(a.environment) - ENVIRONMENT_ORDER.indexOf(b.environment),
		);
	}
	return [...groups.values()];
}

/** The offered environments a register is not connected in yet: new ones, and ones to resume. */
export function connectable(group: RegisterConnections, offered: Environment[]): Environment[] {
	const connected = group.connections.filter((c) => c.status === "connected").map((c) => c.environment);
	return ENVIRONMENT_ORDER.filter((e) => offered.includes(e) && !connected.includes(e));
}

/**
 * Once any environment holds a compliance CSID, the register's details are in its CSR, so the
 * backend saves only the new environment's setting and leaves them as they are.
 */
export function detailsLocked(group: RegisterConnections): boolean {
	return group.connections.some((c) => c.status !== "not_connected");
}

/** Source strings, translated where shown; the labels under the "onboarding" context. */
export const ENVIRONMENT_TEXT: Record<Environment, { label: string; help: string; icon: string }> = {
	production: { label: "Production", help: "Live invoices, with legal effect", icon: "lucide-badge-check" },
	simulation: {
		label: "Simulation",
		help: "A rehearsal on Fatoora's simulation portal, without legal effect",
		icon: "lucide-flask-conical",
	},
	sandbox: { label: "Sandbox", help: "ZATCA's developer portal, for testing this app", icon: "lucide-code" },
};
