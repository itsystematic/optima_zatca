import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";

import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/ui.css";
import "./styles/app.css";

const queryClient = new QueryClient({
	defaultOptions: {
		queries: {
			// the setup record is only changed by this operator, in this tab
			refetchOnWindowFocus: false,
			retry: 1,
		},
		mutations: { retry: 0 },
	},
});

/**
 * Frappe serves the built app at `/zatca-onboarding`; the dev server serves it at the
 * root. The router has to know which, or every in-app link loses the prefix.
 */
const ROUTER_BASE = import.meta.env.DEV ? "/" : "/zatca-onboarding";

createRoot(document.getElementById("root")!).render(
	<StrictMode>
		<QueryClientProvider client={queryClient}>
			<BrowserRouter basename={ROUTER_BASE}>
				<App />
			</BrowserRouter>
		</QueryClientProvider>
	</StrictMode>,
);
