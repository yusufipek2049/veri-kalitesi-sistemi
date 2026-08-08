import { useCallback, useEffect, useState } from "react";
import { AuditApiError, fetchAuditEvents } from "./api";
import {
  auditPageFromApi,
  defaultAuditFilters,
  syntheticAuditPage,
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
  const [page, setPage] = useState<AuditEventPage>(syntheticAuditPage);
  const [filters, setFilters] = useState<AuditQueryFilters>(defaultAuditFilters);
  const [correlationId, setCorrelationId] = useState<string>();
  const load = useCallback(async (
    nextFilters: AuditQueryFilters,
    append = false,
    signal?: AbortSignal,
  ) => {
    if (fixtureState) return;
    if (!append) setState("loading");
    try {
      const response = await fetchAuditEvents(nextFilters, {
        afterSequenceNo: append ? page.nextAfterSequenceNo ?? undefined : undefined,
        periodEnd: append ? page.periodEnd : undefined,
        throughSequenceNo: append ? page.throughSequenceNo : undefined,
        signal,
      });
      const nextPage = auditPageFromApi(response);
      setPage((current) => append
        ? { ...nextPage, items: [...current.items, ...nextPage.items] }
        : nextPage);
      setCorrelationId(response.correlation_id);
      setState((append ? page.items.length + nextPage.items.length : nextPage.items.length) ? "normal" : "empty");
    } catch (error) {
      if (signal?.aborted) return;
      if (error instanceof AuditApiError) {
        setCorrelationId(error.correlationId);
        setState(error.kind === "unauthorized" ? "unauthorized" : "error");
      } else setState("error");
    }
  }, [fixtureState, page.items.length, page.nextAfterSequenceNo, page.throughSequenceNo]);
  useEffect(() => {
    const controller = new AbortController();
    void load(defaultAuditFilters, false, controller.signal);
    return () => controller.abort();
  }, [fixtureState]);
  const query = (nextFilters: AuditQueryFilters) => {
    setFilters(nextFilters);
    void load(nextFilters);
  };
  return <AuditPage correlationId={correlationId} onLoadMore={() => void load(filters, true)} onQuery={query} onRefresh={() => void load(filters)} page={page} state={fixtureState ?? state} />;
}
