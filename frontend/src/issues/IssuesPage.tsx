import { useMemo, useState } from "react";
import { Alert, Box, Button, Skeleton, Typography } from "@mui/material";
import { Plus, RefreshCw } from "lucide-react";
import { AppShell } from "../components/AppShell";
import { AssignmentDialog } from "./dialogs/AssignmentDialog";
import { CloseIssueDialog } from "./dialogs/CloseIssueDialog";
import { CreateIssueDialog } from "./dialogs/CreateIssueDialog";
import { ResolutionDialog } from "./dialogs/ResolutionDialog";
import { VerificationDialog } from "./dialogs/VerificationDialog";
import { filterIssues, initialIssueFilters, newestUpdatedTime } from "./filtering";
import type { IssueRowAction } from "./IssueActionMenu";
import { IssuesFilters } from "./IssuesFilters";
import { IssuesInventory } from "./IssuesInventory";
import type { IssueActionFeedback } from "./labels";
import {
  syntheticIssues,
  type IssueAssigneeOption,
  type IssueCreateInput,
  type IssueEvidenceCandidate,
  type IssueEvidenceRecord,
  type IssueListItem,
  type IssuePriority,
  type IssueState,
} from "./model";

interface IssuesPageProps {
  state?: IssueState;
  items?: IssueListItem[];
  correlationId?: string;
  pageActions?: string[];
  onRefresh?: () => void;
  onCreateIssue?: (input: IssueCreateInput) => Promise<void>;
  onStartInvestigation?: (item: IssueListItem) => Promise<void>;
  onLoadAssignmentOptions?: (item: IssueListItem) => Promise<IssueAssigneeOption[]>;
  onReassign?: (
    item: IssueListItem,
    assigneeUserId: string,
    priority: IssuePriority,
  ) => Promise<void>;
  onLoadEvidence?: (item: IssueListItem) => Promise<{
    records: IssueEvidenceRecord[];
    candidates: IssueEvidenceCandidate[];
  }>;
  onCaptureEvidence?: (
    item: IssueListItem,
    candidateKey: string,
  ) => Promise<IssueEvidenceRecord>;
  onUploadEvidence?: (
    item: IssueListItem, file: File, label: string, classification: string,
    onProgress: (percentage: number) => void,
  ) => Promise<IssueEvidenceRecord>;
  onDownloadEvidence?: (item: IssueListItem, evidenceId: string) => Promise<void>;
  onResolve?: (
    item: IssueListItem,
    rootCause: string,
    correctiveAction: string,
    evidenceReferenceId: string,
    completedAt: string,
  ) => Promise<void>;
  onVerify?: (
    item: IssueListItem,
    verificationReferenceId: string,
  ) => Promise<void>;
  onClose?: (item: IssueListItem) => Promise<void>;
}

function StateMessage({
  state,
  correlationId,
  onRefresh,
}: Pick<IssuesPageProps, "correlationId" | "onRefresh"> & {
  state: "empty" | "error" | "unauthorized";
}) {
  const content = {
    empty: ["Sorun bulunamadı", "Yetkili kapsam ve seçili filtrelerle eşleşen sorun yok."],
    error: ["Sorunlar yüklenemedi", `Teknik bir sorun oluştu. Yeniden deneyin. İzleme kodu: ${correlationId ?? "bulunamadı"}.`],
    unauthorized: ["Bu görünüm için yetkiniz yok", "Sorun envanteri gösterilmedi. Erişim talebi için yetkili biriminizle iletişime geçin."],
  }[state];
  return (
    <Alert
      action={state === "error" ? <Button color="inherit" onClick={onRefresh}>Yeniden dene</Button> : undefined}
      severity={state === "error" ? "error" : state === "unauthorized" ? "warning" : "info"}
    >
      <Typography sx={{ fontWeight: 700 }}>{content[0]}</Typography>
      <Typography variant="body2">{content[1]}</Typography>
    </Alert>
  );
}

function longContentItems(items: IssueListItem[]): IssueListItem[] {
  return Array.from({ length: 4 }, (_, group) => items.map((item) => ({
    ...item,
    id: `${item.id}-${group + 1}`,
    issueNo: `${item.issueNo}-${group + 1}`,
  }))).flat();
}

function IssuesPageHeader({
  showActions,
  canCreateIssue,
  onCreate,
  onRefresh,
}: {
  showActions: boolean;
  canCreateIssue: boolean;
  onCreate?: () => void;
  onRefresh?: () => void;
}) {
  return (
    <Box sx={{ alignItems: { md: "center" }, display: "flex", flexDirection: { xs: "column", md: "row" }, gap: 3, justifyContent: "space-between" }}>
      <Box>
        <Typography component="h1" variant="h1">Sorunlar</Typography>
        <Typography color="text.secondary">Yetkili kapsamınızdaki kalite ve teknik sorunları inceleyin ve yönetin</Typography>
      </Box>
      {showActions ? (
        <Box sx={{ display: "flex", gap: 2 }}>
          {canCreateIssue && onCreate ? (
            <Button onClick={onCreate} startIcon={<Plus aria-hidden="true" size={16} />} variant="outlined">Yeni Sorun</Button>
          ) : null}
          <Button onClick={onRefresh} startIcon={<RefreshCw aria-hidden="true" size={16} />} variant="contained">Yenile</Button>
        </Box>
      ) : null}
    </Box>
  );
}

function IssuesContent({
  state,
  items,
  correlationId,
  onRefresh,
  pendingIssueId,
  onRowAction,
}: {
  state: IssueState;
  items: IssueListItem[];
  correlationId?: string;
  onRefresh?: () => void;
  pendingIssueId?: string;
  onRowAction: (action: IssueRowAction, item: IssueListItem) => void;
}) {
  if (state === "loading") {
    return (
      <Box aria-busy="true" aria-label="Sorunlar yükleniyor">
        {Array.from({ length: 6 }, (_, index) => <Skeleton height={88} key={index} />)}
      </Box>
    );
  }
  if (state === "empty" || state === "error" || state === "unauthorized") {
    return <StateMessage correlationId={correlationId} onRefresh={onRefresh} state={state} />;
  }
  if (!items.length) return <StateMessage state="empty" />;
  return (
    <IssuesInventory
      items={items}
      onAction={onRowAction}
      pendingIssueId={pendingIssueId}
    />
  );
}

function useIssueRowActions({
  onStartInvestigation,
  pendingIssueId,
  setPendingIssueId,
  notify,
  setAssignmentItem,
  setResolutionItem,
  setVerificationItem,
  setCloseItem,
}: {
  onStartInvestigation?: (item: IssueListItem) => Promise<void>;
  pendingIssueId?: string;
  setPendingIssueId: (id: string | undefined) => void;
  notify: (feedback: IssueActionFeedback | undefined) => void;
  setAssignmentItem: (item: IssueListItem) => void;
  setResolutionItem: (item: IssueListItem) => void;
  setVerificationItem: (item: IssueListItem) => void;
  setCloseItem: (item: IssueListItem) => void;
}) {
  const startInvestigation = async (item: IssueListItem) => {
    if (!onStartInvestigation || pendingIssueId) return;
    setPendingIssueId(item.id);
    notify(undefined);
    try {
      await onStartInvestigation(item);
      notify({
        severity: "success",
        message: `${item.issueNo} incelemeye alındı.`,
      });
    } catch (error) {
      notify({
        severity: "error",
        message: error instanceof Error
          ? error.message
          : "İşlem tamamlanamadı. Sorunu yenileyip yeniden deneyin.",
      });
    } finally {
      setPendingIssueId(undefined);
    }
  };
  const openDialog = (setItem: (item: IssueListItem) => void) => (item: IssueListItem) => {
    notify(undefined);
    setItem(item);
  };
  const handlers: Record<IssueRowAction, (item: IssueListItem) => void> = {
    START_INVESTIGATION: (item) => void startInvestigation(item),
    REASSIGN: openDialog(setAssignmentItem),
    RESOLVE: openDialog(setResolutionItem),
    VERIFY: openDialog(setVerificationItem),
    CLOSE: openDialog(setCloseItem),
  };
  return (action: IssueRowAction, item: IssueListItem) => handlers[action](item);
}

export function IssuesPage({
  state = "normal",
  items = syntheticIssues,
  correlationId,
  pageActions,
  onLoadAssignmentOptions,
  onCaptureEvidence,
  onCreateIssue,
  onLoadEvidence,
  onUploadEvidence,
  onDownloadEvidence,
  onRefresh,
  onReassign,
  onResolve,
  onStartInvestigation,
  onVerify,
  onClose,
}: IssuesPageProps) {
  const [filters, setFilters] = useState(initialIssueFilters);
  const [pendingIssueId, setPendingIssueId] = useState<string>();
  const [assignmentItem, setAssignmentItem] = useState<IssueListItem>();
  const [resolutionItem, setResolutionItem] = useState<IssueListItem>();
  const [verificationItem, setVerificationItem] = useState<IssueListItem>();
  const [closeItem, setCloseItem] = useState<IssueListItem>();
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [actionFeedback, setActionFeedback] = useState<IssueActionFeedback>();
  const newestTime = newestUpdatedTime(items);
  const visibleItems = useMemo(
    () => filterIssues(items, filters, newestTime),
    [items, filters, newestTime],
  );
  const effectiveItems = state === "long-content" ? longContentItems(items) : visibleItems;
  const handleRowAction = useIssueRowActions({
    notify: setActionFeedback,
    onStartInvestigation,
    pendingIssueId,
    setAssignmentItem,
    setCloseItem,
    setPendingIssueId,
    setResolutionItem,
    setVerificationItem,
  });
  const canCreateIssue = pageActions?.includes("CREATE_ISSUE") ?? false;

  return (
    <AppShell currentPage="Sorunlar">
      <Box sx={(theme) => ({ display: "grid", gap: 5, margin: "0 auto", maxWidth: theme.appLayout.contentMaxWidth, p: { xs: 3, md: 4, lg: 6 }, width: "100%" })}>
        <IssuesPageHeader
          canCreateIssue={canCreateIssue && Boolean(onCreateIssue)}
          onCreate={() => { setActionFeedback(undefined); setCreateDialogOpen(true); }}
          onRefresh={onRefresh}
          showActions={state !== "unauthorized"}
        />

        {state !== "unauthorized" ? (
          <IssuesFilters
            filters={filters}
            onChange={(patch) => setFilters((current) => ({ ...current, ...patch }))}
            onReset={() => setFilters(initialIssueFilters)}
          />
        ) : null}

        {actionFeedback ? (
          <Alert aria-live="polite" severity={actionFeedback.severity}>
            {actionFeedback.message}
          </Alert>
        ) : null}
        <AssignmentDialog
          item={assignmentItem}
          onClose={() => setAssignmentItem(undefined)}
          onLoadAssignmentOptions={onLoadAssignmentOptions}
          onNotify={setActionFeedback}
          onReassign={onReassign}
          pendingIssueId={pendingIssueId}
          setPendingIssueId={setPendingIssueId}
        />
        <ResolutionDialog
          item={resolutionItem}
          onCaptureEvidence={onCaptureEvidence}
          onClose={() => setResolutionItem(undefined)}
          onDownloadEvidence={onDownloadEvidence}
          onLoadEvidence={onLoadEvidence}
          onNotify={setActionFeedback}
          onResolve={onResolve}
          onUploadEvidence={onUploadEvidence}
          pendingIssueId={pendingIssueId}
          setPendingIssueId={setPendingIssueId}
        />
        <VerificationDialog
          item={verificationItem}
          onClose={() => setVerificationItem(undefined)}
          onNotify={setActionFeedback}
          onVerify={onVerify}
          pendingIssueId={pendingIssueId}
          setPendingIssueId={setPendingIssueId}
        />
        <CloseIssueDialog
          item={closeItem}
          onClose={() => setCloseItem(undefined)}
          onCloseIssue={onClose}
          onNotify={setActionFeedback}
          pendingIssueId={pendingIssueId}
          setPendingIssueId={setPendingIssueId}
        />
        <CreateIssueDialog
          onCreateIssue={onCreateIssue}
          onClose={() => setCreateDialogOpen(false)}
          onNotify={setActionFeedback}
          open={createDialogOpen}
        />
        <IssuesContent
          correlationId={correlationId}
          items={effectiveItems}
          onRefresh={onRefresh}
          onRowAction={handleRowAction}
          pendingIssueId={pendingIssueId}
          state={state}
        />
      </Box>
    </AppShell>
  );
}
