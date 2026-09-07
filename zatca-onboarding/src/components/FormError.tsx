import { useFormError } from "@/lib/errors";
import { Mark } from "./primitives";

/**
 * A failed write, said out loud.
 *
 * Every screen that mutates renders one of these. A refusal the operator cannot
 * see is worse than the refusal itself: the button appears to do nothing, and
 * the natural response is to press it again.
 */
export function FormError({ error }: { error: unknown }) {
	const message = useFormError()(error);
	if (!message) return null;
	return (
		<div className="formerror" role="alert">
			<Mark kind="fail" size={15} font={10} style={{ marginTop: 1 }} />
			<span>{message}</span>
		</div>
	);
}
