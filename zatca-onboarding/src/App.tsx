import { Navigate, Route, Routes } from "react-router-dom";
import { DevToolbar, isDevToolbarEnabled } from "@/dev-toolbar";
import { I18nProvider } from "@/i18n/core";
import { RequireStep, ResumeRedirect } from "@/routes/Guards";
import { Company } from "@/routes/Company";
import { Stub } from "@/routes/Stub";
import { Done } from "@/routes/Done";
import { Log } from "@/routes/Log";
import { Entity } from "@/routes/Entity";
import { HowItWorks } from "@/routes/HowItWorks";
import { Mode } from "@/routes/Mode";
import { Otp } from "@/routes/Otp";
import { Progress } from "@/routes/Progress";
import { Registers } from "@/routes/Registers";
import { Review } from "@/routes/Review";
import { Scope } from "@/routes/Scope";
import { Welcome } from "@/routes/Welcome";
import { paths } from "@/routes/paths";

export default function App() {
	return (
		<I18nProvider>
			<div className="app">
				{isDevToolbarEnabled() && <DevToolbar />}
				<main className="app__main">
					<Routes>
						<Route path={paths.root} element={<ResumeRedirect />} />

						<Route path={paths.welcome} element={<Welcome />} />
						<Route path={paths.howItWorks} element={<HowItWorks />} />

						<Route path={paths.company} element={<Company />} />

						<Route
							path={paths.mode}
							element={
								<RequireStep step="mode">
									<Mode />
								</RequireStep>
							}
						/>
						<Route
							path={paths.scope}
							element={
								<RequireStep step="scope">
									<Scope />
								</RequireStep>
							}
						/>
						<Route
							path={paths.entity}
							element={
								<RequireStep step="entity">
									<Entity />
								</RequireStep>
							}
						/>
						<Route
							path={paths.registers}
							element={
								<RequireStep step="registers">
									<Registers />
								</RequireStep>
							}
						/>
						<Route
							path={paths.review}
							element={
								<RequireStep step="review">
									<Review />
								</RequireStep>
							}
						/>
						<Route
							path={paths.otp}
							element={
								<RequireStep step="otp">
									<Otp />
								</RequireStep>
							}
						/>
						<Route
							path={paths.progress}
							element={
								<RequireStep step="progress">
									<Progress />
								</RequireStep>
							}
						/>
						<Route
							path={paths.done}
							element={
								<RequireStep step="done">
									<Done />
								</RequireStep>
							}
						/>

						<Route path={paths.log} element={<Log />} />
						<Route
							path={paths.registerAdmin}
							element={
								<Stub titleKey="stub.registers.title" bodyKey="stub.registers.body" />
							}
						/>

						<Route path="*" element={<Navigate to={paths.root} replace />} />
					</Routes>
				</main>
			</div>
		</I18nProvider>
	);
}
