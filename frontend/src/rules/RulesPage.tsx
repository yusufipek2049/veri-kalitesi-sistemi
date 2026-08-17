import { useMemo, useState } from "react";
import { Alert, Box, Button, Skeleton, Typography } from "@mui/material";
import { Plus, RefreshCw } from "lucide-react";
import { AppShell } from "../components/AppShell";
import { ActivateRuleDialog } from "./dialogs/ActivateRuleDialog";
import { ApprovalDecisionDialog } from "./dialogs/ApprovalDecisionDialog";
import { CreateRuleDialog } from "./dialogs/CreateRuleDialog";
import { CreateVersionDialog } from "./dialogs/CreateVersionDialog";
import { PassivateRuleDialog } from "./dialogs/PassivateRuleDialog";
import { RequestApprovalDialog } from "./dialogs/RequestApprovalDialog";
import { TestResultDialog } from "./dialogs/TestResultDialog";
import { WithdrawApprovalDialog } from "./dialogs/WithdrawApprovalDialog";
import { filterRules, initialRuleFilters, longContentItems, type RuleFilterValues } from "./filtering";
import { RulesFilters } from "./RulesFilters";
import { RulesInventory } from "./RulesInventory";
import {
  syntheticRules,
  type RuleAction,
  type RuleCreateRequest,
  type RuleListItem,
  type RuleState,
  type RuleTestResult,
  type RuleVersionCreateRequest,
} from "./model";
import { useRuleActions } from "./useRuleActions";

interface RulesPageProps {
  state?: RuleState;
  items?: RuleListItem[];
  correlationId?: string;
  onRefresh?: () => void;
  onCreateRule?: (payload: RuleCreateRequest) => Promise<void>;
  onCreateVersion?: (rule: RuleListItem, data: RuleVersionCreateRequest) => Promise<void>;
  onTestRule?: (rule: RuleListItem, ruleVersionId: string) => Promise<RuleTestResult>;
  onActivateRule?: (rule: RuleListItem) => Promise<void>;
  onRequestApproval?: (rule: RuleListItem) => Promise<void>;
  onDecideApproval?: (
    rule: RuleListItem,
    approvalRequestId: string,
    decision: "APPROVE" | "REJECT",
    reasonCode: string,
  ) => Promise<void>;
  onWithdrawApproval?: (rule: RuleListItem, approvalRequestId: string, reasonCode: string) => Promise<void>;
  onPassivateRule?: (rule: RuleListItem) => Promise<void>;
  catalogDatasets?: { id: string; name: string; namespace: string }[];
  catalogFields?: { id: string; name: string; datasetId: string }[];
  onLoadFields?: (datasetId: string) => Promise<void>;
  onLoadRuleDetail?: (ruleId: string) => Promise<Record<string, unknown>>;
}

function StateMessage({
  state,
  correlationId,
  onRefresh,
}: Pick<RulesPageProps, "correlationId" | "onRefresh"> & {
  state: "empty" | "error" | "unauthorized";
}) {
  const content = {
    empty: ["Kural bulunamadı", "Yetkili kapsam ve seçili filtrelerle eşleşen kural yok."],
    error: [
      "Kurallar yüklenemedi",
      `Teknik bir sorun oluştu. Yeniden deneyin. İzleme kodu: ${correlationId ?? "bulunamadı"}.`,
    ],
    unauthorized: [
      "Bu görünüm için yetkiniz yok",
      "Kural içeriği gösterilmedi. Erişim talebi için yetkili biriminizle iletişime geçin.",
    ],
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

function RulesPageHeader({
  showActions,
  onCreate,
  onRefresh,
}: {
  showActions: boolean;
  onCreate: () => void;
  onRefresh?: () => void;
}) {
  return (
    <Box sx={{ alignItems: { md: "center" }, display: "flex", flexDirection: { xs: "column", md: "row" }, gap: 3, justifyContent: "space-between" }}>
      <Box>
        <Typography component="h1" variant="h1">Kurallar</Typography>
        <Typography color="text.secondary">Yetkili dataset kapsamınızdaki kural envanteri</Typography>
      </Box>
      {showActions ? (
        <Box sx={{ display: "flex", gap: 2 }}>
          <Button
            onClick={onCreate}
            startIcon={<Plus aria-hidden="true" size={16} />}
            variant="outlined"
          >
            Kural Oluştur
          </Button>
          <Button
            onClick={onRefresh}
            startIcon={<RefreshCw aria-hidden="true" size={16} />}
            variant="contained"
          >
            Yenile
          </Button>
        </Box>
      ) : null}
    </Box>
  );
}

function RulesContent({
  state,
  items,
  correlationId,
  onRefresh,
  actionLoading,
  catalogDatasets,
  onRowAction,
}: {
  state: RuleState;
  items: RuleListItem[];
  correlationId?: string;
  onRefresh?: () => void;
  actionLoading: string | null;
  catalogDatasets?: { id: string; name: string; namespace: string }[];
  onRowAction: (item: RuleListItem, action: RuleAction) => void;
}) {
  if (state === "loading") {
    return (
      <Box aria-busy="true" aria-label="Kurallar yükleniyor">
        {Array.from({ length: 5 }, (_, index) => <Skeleton height={84} key={index} />)}
      </Box>
    );
  }
  if (state === "empty" || state === "error" || state === "unauthorized") {
    return <StateMessage correlationId={correlationId} onRefresh={onRefresh} state={state} />;
  }
  if (!items.length) return <StateMessage state="empty" />;
  return (
    <RulesInventory
      items={items}
      onAction={onRowAction}
      actionLoading={actionLoading}
      catalogDatasets={catalogDatasets}
    />
  );
}

function RuleActionDialogs({
  actions,
  onCreateVersion,
}: {
  actions: ReturnType<typeof useRuleActions>;
  onCreateVersion?: (rule: RuleListItem, data: RuleVersionCreateRequest) => Promise<void>;
}) {
  return (
    <>
      <CreateVersionDialog
        open={actions.dialog === "version"}
        item={actions.activeItem}
        seed={actions.versionSeed}
        error={actions.actionError}
        onClose={actions.closeDialog}
        onError={actions.setActionError}
        onCreateVersion={onCreateVersion}
      />
      <TestResultDialog
        open={actions.testResultOpen}
        result={actions.testResult}
        onClose={actions.closeTestResult}
      />
      <ActivateRuleDialog
        open={actions.dialog === "activate"}
        item={actions.activeItem}
        error={actions.actionError}
        loading={actions.dialogLoading}
        onClose={actions.closeDialog}
        onConfirm={actions.activate}
      />
      <RequestApprovalDialog
        open={actions.dialog === "approval-request"}
        item={actions.activeItem}
        error={actions.actionError}
        loading={actions.dialogLoading}
        onClose={actions.closeDialog}
        onConfirm={actions.requestApproval}
      />
      <ApprovalDecisionDialog
        open={actions.dialog === "decision"}
        item={actions.activeItem}
        error={actions.actionError}
        loading={actions.dialogLoading}
        onClose={actions.closeDialog}
        onSubmit={actions.decide}
      />
      <WithdrawApprovalDialog
        open={actions.dialog === "withdraw"}
        item={actions.activeItem}
        error={actions.actionError}
        loading={actions.dialogLoading}
        onClose={actions.closeDialog}
        onSubmit={actions.withdraw}
      />
      <PassivateRuleDialog
        open={actions.dialog === "passivate"}
        item={actions.activeItem}
        error={actions.actionError}
        loading={actions.dialogLoading}
        onClose={actions.closeDialog}
        onConfirm={actions.passivate}
      />
    </>
  );
}

export function RulesPage({
  state = "normal",
  items = syntheticRules,
  correlationId,
  onRefresh,
  onCreateRule,
  onCreateVersion,
  onTestRule,
  onActivateRule,
  onRequestApproval,
  onDecideApproval,
  onWithdrawApproval,
  onPassivateRule,
  catalogDatasets,
  catalogFields,
  onLoadFields,
  onLoadRuleDetail,
}: RulesPageProps) {
  const [filters, setFilters] = useState<RuleFilterValues>(initialRuleFilters);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const actions = useRuleActions({
    onTestRule,
    onActivateRule,
    onRequestApproval,
    onDecideApproval,
    onWithdrawApproval,
    onPassivateRule,
    onLoadRuleDetail,
  });

  const visibleItems = useMemo(() => filterRules(items, filters), [items, filters]);
  const effectiveItems = state === "long-content" ? longContentItems(items) : visibleItems;

  return (
    <AppShell currentPage="Kurallar">
      <Box sx={(theme) => ({ display: "grid", gap: 5, margin: "0 auto", maxWidth: theme.appLayout.contentMaxWidth, p: { xs: 3, md: 4, lg: 6 }, width: "100%" })}>
        <RulesPageHeader
          showActions={state !== "unauthorized"}
          onCreate={() => setCreateDialogOpen(true)}
          onRefresh={onRefresh}
        />

        <CreateRuleDialog
          open={createDialogOpen}
          onClose={() => setCreateDialogOpen(false)}
          onCreateRule={onCreateRule}
          catalogDatasets={catalogDatasets}
          catalogFields={catalogFields}
          onLoadFields={onLoadFields}
        />
        <RuleActionDialogs actions={actions} onCreateVersion={onCreateVersion} />

        {state !== "unauthorized" ? (
          <RulesFilters
            filters={filters}
            onChange={(patch) => setFilters((current) => ({ ...current, ...patch }))}
          />
        ) : null}

        {actions.actionError && state === "normal" ? (
          <Alert severity="error" sx={{ mb: 1 }}>{actions.actionError}</Alert>
        ) : null}

        <RulesContent
          state={state}
          items={effectiveItems}
          correlationId={correlationId}
          onRefresh={onRefresh}
          actionLoading={actions.actionLoading}
          catalogDatasets={catalogDatasets}
          onRowAction={actions.handleAction}
        />
      </Box>
    </AppShell>
  );
}
