/**
 * Links that leave this app.
 *
 * The router is mounted under a basename, so `navigate("/app/…")` resolves
 * inside it — `/zatca-onboarding/app/…`, which does not exist. Anything belonging to
 * the desk, or to the mail client, has to leave through the browser rather than
 * through the router.
 */

/** The Frappe desk route for a doctype's list, or a specific document. */
export function deskUrl(doctype: string, name?: string): string {
	const slug = doctype.toLowerCase().replace(/\s+/g, "-");
	return name ? `/app/${slug}/${encodeURIComponent(name)}` : `/app/${slug}`;
}

/** Leave the app for a desk route. */
export function openDesk(doctype: string, name?: string): void {
	window.location.href = deskUrl(doctype, name);
}

/**
 * Where a support request goes.
 *
 * Digits only, in international form and without the leading `+`: that is the
 * shape `wa.me` expects, and a number carrying spaces or a plus resolves to a
 * WhatsApp error page rather than a chat.
 */
export const SUPPORT_WHATSAPP = "201016649035";

/** The same number written for a human to read or dial. */
export const SUPPORT_WHATSAPP_DISPLAY = "+20 101 664 9035";

/**
 * A pre-filled WhatsApp message to support.
 *
 * The reference and company are filled in because they are the first two things
 * anyone answering would have to ask for, and the operator has them on screen
 * while writing but not once they have switched to WhatsApp.
 *
 * `wa.me` rather than the `whatsapp://` scheme: the former opens the desktop or
 * mobile app when one is installed and falls back to WhatsApp Web when it is
 * not, whereas the scheme fails silently on a machine with no app registered —
 * which for a browser-based accounting system is the common case.
 */
export function supportWhatsApp(opts: { reference?: string | null; company?: string } = {}): string {
	const message = [
		opts.reference
			? `E-invoicing support — ${opts.reference}`
			: "E-invoicing support",
		"",
		"Describe what you were doing and what happened:",
		"",
		"",
		"—",
		opts.company ? `Company: ${opts.company}` : null,
		opts.reference ? `Reference: ${opts.reference}` : null,
	]
		.filter((line) => line !== null)
		.join("\n");

	return `https://wa.me/${SUPPORT_WHATSAPP}?text=${encodeURIComponent(message)}`;
}
