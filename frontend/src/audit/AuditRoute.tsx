import { useCallback, useEffect, useRef, useState } from "react";
import { AuditApiError, fetchAuditEvents, fetchAuditSummary } from "./api";
import {
  auditPageFromApi,
  auditSummaryFromApi,
  defaultAuditFilters,
  type AuditEventPage,
  type AuditQueryFilters,
  type AuditState,
} from "./model";
import { AuditPage } from "./AuditPage";

const auditStates: AuditState[] = ["normal", "loading", "empty", "error", "unauthorized", "long-content"];

export function AuditRoute() {
  const requestedState = new URLSearchParams(window.location.search).get("state") as AuditState | null;
  const fixtureState = import.meta.env.DEV && requestedState && auditStates.includes(requestedState) ? requestedState : null;
  const [state, setState] = useState<AuditState>(fixtureState ?? "loading");
  const [page, setPage] = useState<AuditEventPage>({
    periodStart: new Date().toISOString(),
    periodEnd: new Date().toISOString(),
    integrityValid: true,
    integrityCheckedCount: 0,
    firstInvalidEventId: null,
    nextAfterSequenceNo: null,
    throughSequenceNo: 0,
    pageSize: 0,
    policyVersion: "",
    items: [],
  });
  const [summary, setSummary] = useState({
    totalCount: 0,
    resultDistribution: {} as Record<string, number>,
    actionDistribution: {} as Record<string, number>,
    topActors: [] as Array<{ actorId: string; count: number }>,
    periodStart: new Date().toISOString(),
    periodEnd: new Date().toISOString(),
  });
  const [filters, setFilters] = useState<AuditQueryFilters>(defaultAuditFilters);
  const [correlationId, setCorrelationId] = useState<string>();
  const [autoRefreshMs, setAutoRefreshMs] = useState(0);
  const [newEventCount, setNewEventCount] = useState(0);
  const pageRef = useRef(page);
  useEffect(() => { pageRef.current = page; }, [page]);
  const load = useCallback(async (
    nextFilters: AuditQueryFilters,
    append = false,
    signal?: AbortSignal,
    background = false,
  ) => {
    if (fixtureState) return;
    if (!append && !background) setState("loading");
    try {
      const currentPage = pageRef.current;
      const eventRequest = fetchAuditEvents(nextFilters, {
        afterSequenceNo: append ? currentPage.nextAfterSequenceNo ?? undefined : undefined,
        periodEnd: append ? currentPage.periodEnd : undefined,
        throughSequenceNo: append ? currentPage.throughSequenceNo : undefined,
        signal,
      });
      const [response, summaryResponse] = append
        ? [await eventRequest, null]
        : await Promise.all([
            eventRequest,
            fetchAuditSummary(nextFilters, { signal }),
          ]);
      const nextPage = auditPageFromApi(response);
      if (summaryResponse) setSummary(auditSummaryFromApi(summaryResponse));
      if (background) {
        const currentEventIds = new Set(currentPage.items.map((item) => item.eventId));
        const discoveredCount = nextPage.items.filter((item) => !currentEventIds.has(item.eventId)).length;
        setNewEventCount((current) => current + discoveredCount);
      } else if (!append) {
        setNewEventCount(0);
      }
      setPage((current) => append
        ? { ...nextPage, items: [...current.items, ...nextPage.items] }
        : nextPage);
      setCorrelationId(response.correlation_id);
      setState((append ? currentPage.items.length + nextPage.items.length : nextPage.items.length) ? "normal" : "empty");
    } catch (error) {
      if (signal?.aborted) return;
      if (error instanceof AuditApiError) {
        setCorrelationId(error.correlationId);
        setState(error.kind === "unauthorized" ? "unauthorized" : "error");
      } else setState("error");
    }
  }, [fixtureState]);
  useEffect(() => {
    const controller = new AbortController();
    void load(defaultAuditFilters, false, controller.signal);
    return () => controller.abort();
  }, [fixtureState, load]);
  useEffect(() => {
    if (!autoRefreshMs || fixtureState) return undefined;
    const intervalId = window.setInterval(() => {
      void load(filters, false, undefined, true);
    }, autoRefreshMs);
    return () => window.clearInterval(intervalId);
  }, [autoRefreshMs, filters, fixtureState, load]);
  const query = (nextFilters: AuditQueryFilters) => {
    setFilters(nextFilters);
    void load(nextFilters);
  };
  const showNewEvents = () => {
    setNewEventCount(0);
    void load(filters);
  };
  return (
    <AuditPage
      autoRefreshMs={autoRefreshMs}
      correlationId={correlationId}
      newEventCount={newEventCount}
      onAutoRefreshChange={setAutoRefreshMs}
      onLoadMore={() => void load(filters, true)}
      onNewEventsRefresh={showNewEvents}
      onQuery={query}
      onRefresh={() => void load(filters)}
      page={page}
      state={fixtureState ?? state}
      summary={summary}
    />
  );
}
