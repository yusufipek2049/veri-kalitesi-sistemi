import { DashboardPage } from "./dashboard/DashboardPage";
import type { DashboardState } from "./dashboard/model";

const dashboardStates: DashboardState[] = ["normal", "loading", "empty", "error", "unauthorized", "long-content"];

export default function App() {
  const requestedState = new URLSearchParams(window.location.search).get("state") as DashboardState | null;
  const state = requestedState && dashboardStates.includes(requestedState) ? requestedState : "normal";

  return <DashboardPage state={state} />;
}
