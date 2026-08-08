import { useCallback, useEffect, useState } from "react";
import { ProfilingApiError, fetchDriftJudgment, fetchProfileSnapshotDetail, fetchProfileSnapshots } from "./api";
import {
  driftJudgmentFromApi,
  snapshotDetailFromApi,
  snapshotListItemFromApi,
  syntheticDriftJudgment,
  syntheticSnapshotDetail,
  syntheticSnapshots,
  type DriftJudgment,
  type ProfileSnapshotDetail,
  type ProfileSnapshotListItem,
  type ProfilingState,
} from "./model";
import { ProfilingPage } from "./ProfilingPage";

const profilingStates: ProfilingState[] = ["normal", "loading", "empty", "error", "unauthorized", "long-content"];

export function ProfilingRoute() {
  const requestedState = new URLSearchParams(window.location.search).get("state") as ProfilingState | null;
  const fixtureState = import.meta.env.DEV && requestedState && profilingStates.includes(requestedState) ? requestedState : null;
  const [state, setState] = useState<ProfilingState>(fixtureState ?? "loading");
  const [snapshots, setSnapshots] = useState<ProfileSnapshotListItem[]>(syntheticSnapshots);
  const [selectedSnapshot, setSelectedSnapshot] = useState<ProfileSnapshotDetail | null>(null);
  const [driftJudgment, setDriftJudgment] = useState<DriftJudgment | null>(null);
  const [correlationId, setCorrelationId] = useState<string>();
  const [limit, setLimit] = useState<number>(50);

  const searchParams = new URLSearchParams(window.location.search);
  const datasetId = searchParams.get("dataset_id") ?? "ds-core-banking";
  const profileId = searchParams.get("profile_id") ?? undefined;
  const invalidProfileId = searchParams.has("profile_id") && !searchParams.get("profile_id");

  const load = useCallback(async (signal?: AbortSignal) => {
    if (fixtureState) return;
    setState("loading");
    try {
      const response = await fetchProfileSnapshots(datasetId, signal);
      const nextSnapshots = response.items.map(snapshotListItemFromApi);
      setSnapshots(nextSnapshots);
      setLimit(response.limit);
      setCorrelationId(response.correlation_id);
      setState(nextSnapshots.length ? "normal" : "empty");
    } catch (error) {
      if (signal?.aborted) return;
      if (error instanceof ProfilingApiError) {
        setCorrelationId(error.correlationId);
        setState(error.kind === "unauthorized" ? "unauthorized" : "error");
      } else setState("error");
    }
  }, [fixtureState, datasetId]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  useEffect(() => {
    if (!profileId || invalidProfileId) {
      setSelectedSnapshot(null);
      setDriftJudgment(null);
      return;
    }
    const controller = new AbortController();
    const loadDetail = async () => {
      try {
        const detailResponse = await fetchProfileSnapshotDetail(profileId, controller.signal);
        setSelectedSnapshot(snapshotDetailFromApi(detailResponse));
        const driftResponse = await fetchDriftJudgment(profileId, undefined, controller.signal);
        setDriftJudgment(driftJudgmentFromApi(driftResponse));
      } catch (error) {
        if (controller.signal.aborted) return;
        if (error instanceof ProfilingApiError) {
          setCorrelationId(error.correlationId);
        }
        setSelectedSnapshot(null);
        setDriftJudgment(null);
      }
    };
    void loadDetail();
    return () => controller.abort();
  }, [profileId, invalidProfileId]);

  return (
    <ProfilingPage
      correlationId={correlationId}
      driftJudgment={driftJudgment}
      limit={limit}
      onRefresh={() => void load()}
      selectedSnapshot={selectedSnapshot}
      snapshots={snapshots}
      state={fixtureState ?? state}
    />
  );
}
