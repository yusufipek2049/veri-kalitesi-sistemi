import { useCallback, useEffect, useState } from "react";
import { createReport, fetchReportSummary, listReports, ReportApiError, triggerDownload } from "./api";
import { reportSummaryFromApi, syntheticReportSummary, type ReportItem, type ReportRequest, type ReportState, type ReportSummary } from "./model";
import { ReportsPage } from "./ReportsPage";

const reportStates: ReportState[] = ["normal", "loading", "empty", "error", "unauthorized", "long-content"];

export function ReportsRoute() {
  const requestedState = new URLSearchParams(window.location.search).get("state") as ReportState | null;
  const fixtureState = import.meta.env.DEV && requestedState && reportStates.includes(requestedState) ? requestedState : null;
  const [state, setState] = useState<ReportState>(fixtureState ?? "loading");
  const [summary, setSummary] = useState<ReportSummary>(syntheticReportSummary);
  const [reportItems, setReportItems] = useState<ReportItem[]>([]);
  const [correlationId, setCorrelationId] = useState<string>();
  const load = useCallback(async (signal?: AbortSignal) => {
    if (fixtureState) return;
    setState("loading");
    try {
      const [summaryResponse, listResponse] = await Promise.all([
        fetchReportSummary(signal),
        listReports(50, 0, signal),
      ]);
      const nextSummary = reportSummaryFromApi(summaryResponse);
      setSummary(nextSummary);
      setReportItems(listResponse.items);
      setCorrelationId(summaryResponse.correlation_id);
      setState(nextSummary.rows.length ? "normal" : "empty");
    } catch (error) {
      if (signal?.aborted) return;
      if (error instanceof ReportApiError) {
        setCorrelationId(error.correlationId);
        setState(error.kind === "unauthorized" ? "unauthorized" : "error");
      } else setState("error");
    }
  }, [fixtureState]);
  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const handleCreateReport = useCallback(async (request: ReportRequest) => {
    const response = await createReport(request);
    setReportItems((current) => [response.report, ...current]);
    setCorrelationId(response.correlation_id);
  }, []);

  const handleDownloadReport = useCallback(async (reportId: string, filename: string) => {
    await triggerDownload(reportId, filename);
  }, []);

  return (
    <ReportsPage
      correlationId={correlationId}
      onRefresh={() => void load()}
      onCreateReport={handleCreateReport}
      onDownloadReport={handleDownloadReport}
      reportItems={reportItems}
      state={fixtureState ?? state}
      summary={summary}
    />
  );
}
