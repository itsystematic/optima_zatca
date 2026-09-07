import { Link } from "react-router-dom";
import { useT } from "@/i18n/core";
import type { MessageKey } from "@/i18n/core";
import { paths } from "./paths";

/**
 * Areas the onboarding flow links to that are outside this build. Better an
 * honest placeholder than an invented screen with no design behind it.
 */
export function Stub({ titleKey, bodyKey }: { titleKey: MessageKey; bodyKey: MessageKey }) {
	const t = useT();
	return (
		<div className="stub">
			<div className="stub__card">
				<h1 className="stub__title">{t(titleKey)}</h1>
				<p className="stub__body">{t(bodyKey)}</p>
				<Link to={paths.root} style={{ fontSize: 13, fontWeight: 600 }}>
					{t("stub.back")}
				</Link>
			</div>
		</div>
	);
}
