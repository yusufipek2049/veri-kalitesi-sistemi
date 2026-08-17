import { useState } from "react";
import type { RuleAction, RuleListItem, RuleTestResult } from "./model";
import { initialSqlEditorValues, type SqlEditorValues } from "./sqlValidation";

export type RuleDialogKind =
  | "version"
  | "activate"
  | "approval-request"
  | "decision"
  | "withdraw"
  | "passivate";

interface UseRuleActionsOptions {
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
  onLoadRuleDetail?: (ruleId: string) => Promise<Record<string, unknown>>;
}

export interface VersionDialogSeed {
  sql: SqlEditorValues;
  loading: boolean;
}

const idleSeed: VersionDialogSeed = { sql: initialSqlEditorValues, loading: false };

function seedFromDefinition(definition: Record<string, unknown>): VersionDialogSeed {
  return {
    sql: {
      text: definition.sql ? String(definition.sql) : "",
      timeout: typeof definition.timeout_seconds === "number" ? definition.timeout_seconds : 30,
      rowLimit: typeof definition.row_limit === "number" ? definition.row_limit : 1000,
    },
    loading: false,
  };
}

// Pre-populate SQL for CUSTOM_SQL rules before opening the version dialog
function useVersionDialogOpener(
  onLoadRuleDetail: ((ruleId: string) => Promise<Record<string, unknown>>) | undefined,
  openDialog: (kind: RuleDialogKind) => void,
) {
  const [versionSeed, setVersionSeed] = useState<VersionDialogSeed>(idleSeed);

  const openVersionDialog = (item: RuleListItem) => {
    setVersionSeed(item.ruleType === "CUSTOM_SQL" && onLoadRuleDetail
      ? { sql: initialSqlEditorValues, loading: true }
      : idleSeed);
    openDialog("version");
    if (item.ruleType !== "CUSTOM_SQL" || !onLoadRuleDetail) return;
    onLoadRuleDetail(item.id)
      .then(seedFromDefinition)
      // SQL pre-population failure is non-fatal
      .catch(() => idleSeed)
      .then(setVersionSeed);
  };

  return { versionSeed, openVersionDialog };
}

// Activate / request-approval / passivate share the same guarded submit shape
function useGuardedRuleActions(
  activeItem: RuleListItem | null,
  setActionError: (message: string | null) => void,
  closeDialog: () => void,
  {
    onActivateRule,
    onRequestApproval,
    onPassivateRule,
  }: Pick<UseRuleActionsOptions, "onActivateRule" | "onRequestApproval" | "onPassivateRule">,
) {
  const [dialogLoading, setDialogLoading] = useState(false);

  const runGuardedAction = async (
    operation: (item: RuleListItem) => Promise<void>,
    errorMessage: string,
  ) => {
    if (!activeItem || dialogLoading) return;
    setDialogLoading(true);
    setActionError(null);
    try {
      await operation(activeItem);
      closeDialog();
    } catch {
      setActionError(errorMessage);
    } finally {
      setDialogLoading(false);
    }
  };

  const activate = () => {
    if (!onActivateRule) return;
    void runGuardedAction(onActivateRule, "Kural aktifleştirilemedi.");
  };

  const requestApproval = () => {
    if (!onRequestApproval) return;
    void runGuardedAction(onRequestApproval, "Onay isteği gönderilemedi.");
  };

  const passivate = () => {
    if (!onPassivateRule) return;
    void runGuardedAction(onPassivateRule, "Kural pasifleştirilemedi.");
  };

  return { dialogLoading, runGuardedAction, activate, requestApproval, passivate };
}

export function useRuleActions({
  onTestRule,
  onActivateRule,
  onRequestApproval,
  onDecideApproval,
  onWithdrawApproval,
  onPassivateRule,
  onLoadRuleDetail,
}: UseRuleActionsOptions) {
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [activeItem, setActiveItem] = useState<RuleListItem | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [dialog, setDialog] = useState<RuleDialogKind | null>(null);
  const [testResult, setTestResult] = useState<RuleTestResult | null>(null);
  const [testResultOpen, setTestResultOpen] = useState(false);
  const { versionSeed, openVersionDialog } = useVersionDialogOpener(onLoadRuleDetail, setDialog);
  const guarded = useGuardedRuleActions(
    activeItem,
    setActionError,
    () => setDialog(null),
    { onActivateRule, onRequestApproval, onPassivateRule },
  );

  const runTest = async (item: RuleListItem) => {
    if (!onTestRule) return;
    setActionLoading(item.id);
    setTestResult(null);
    setActionError(null);
    try {
      const result = await onTestRule(item, item.versionId);
      setTestResult(result);
      setTestResultOpen(true);
    } catch {
      setActionError("Test çalıştırılamadı.");
    } finally {
      setActionLoading(null);
    }
  };

  const handleAction = (item: RuleListItem, action: RuleAction) => {
    setActiveItem(item);
    setActionError(null);
    if (action === "TEST_RULE") {
      void runTest(item);
      return;
    }
    const dialogByAction: Record<Exclude<RuleAction, "TEST_RULE" | "CREATE_VERSION">, RuleDialogKind> = {
      ACTIVATE: "activate",
      REQUEST_APPROVAL: "approval-request",
      DECIDE_APPROVAL: "decision",
      WITHDRAW_APPROVAL: "withdraw",
      PASSIVATE: "passivate",
    };
    if (action === "CREATE_VERSION") {
      openVersionDialog(item);
      return;
    }
    setDialog(dialogByAction[action]);
  };

  const resolveApprovalRequestId = (): string | null => {
    if (!activeItem?.pendingApprovalRequestId) {
      setActionError("Bu kural için bekleyen onay isteği bulunamadı.");
      return null;
    }
    return activeItem.pendingApprovalRequestId;
  };

  const decide = (decision: "APPROVE" | "REJECT", reason: string) => {
    if (!activeItem || !onDecideApproval || guarded.dialogLoading) return;
    if (!reason.trim()) {
      setActionError("Gerekçe kodu zorunludur.");
      return;
    }
    const approvalRequestId = resolveApprovalRequestId();
    if (!approvalRequestId) return;
    void guarded.runGuardedAction(
      (item) => onDecideApproval(item, approvalRequestId, decision, reason),
      "Onay kararı kaydedilemedi.",
    );
  };

  const withdraw = (reason: string) => {
    if (!activeItem || !onWithdrawApproval || guarded.dialogLoading) return;
    if (!reason.trim()) {
      setActionError("Gerekçe kodu zorunludur.");
      return;
    }
    const approvalRequestId = resolveApprovalRequestId();
    if (!approvalRequestId) return;
    void guarded.runGuardedAction(
      (item) => onWithdrawApproval(item, approvalRequestId, reason),
      "Onay geri çekilemedi.",
    );
  };

  return {
    actionLoading,
    activeItem,
    actionError,
    setActionError,
    dialog,
    dialogLoading: guarded.dialogLoading,
    testResult,
    testResultOpen,
    versionSeed,
    handleAction,
    closeDialog: () => setDialog(null),
    closeTestResult: () => setTestResultOpen(false),
    activate: guarded.activate,
    requestApproval: guarded.requestApproval,
    decide,
    withdraw,
    passivate: guarded.passivate,
  };
}
