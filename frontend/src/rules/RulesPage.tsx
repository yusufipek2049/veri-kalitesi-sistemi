import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  IconButton,
  InputLabel,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Paper,
  Select,
  Skeleton,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  Activity,
  Ban,
  Braces,
  CheckCircle,
  ChevronRight,
  CircleCheck,
  Clock3,
  FilePen,
  KeyRound,
  ListChecks,
  LoaderCircle,
  MoreVertical,
  Plus,
  PowerOff,
  RefreshCw,
  ScanText,
  Search,
  SendHorizontal,
  ThumbsUp,
  Undo2,
  type LucideIcon,
} from "lucide-react";
import { Link } from "react-router-dom";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import { designTokens } from "../theme/tokens";
import {
  syntheticRules,
  type RuleAction,
  type RuleCreateRequest,
  type RuleListItem,
  type RuleState,
  type RuleTestResult,
  type RuleVersionCreateRequest,
} from "./model";

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

const statusLabels: Record<string, string> = {
  DRAFT: "Taslak",
  ACTIVE: "Aktif",
  PASSIVE: "Pasif",
  REVIEW_REQUIRED: "İnceleme gerekli",
  ARCHIVED: "Arşivlendi",
};

const dimensionLabels: Record<string, string> = {
  COMPLETENESS: "Tamlık",
  ACCURACY: "Doğruluk",
  VALIDITY: "Geçerlilik",
  CONSISTENCY: "Tutarlılık",
  UNIQUENESS: "Tekillik",
  TIMELINESS: "Güncellik",
  INTEGRITY: "Bütünlük",
};

const criticalityLabels: Record<string, string> = {
  LOW: "Düşük",
  MEDIUM: "Orta",
  HIGH: "Yüksek",
  CRITICAL: "Kritik",
};

const ruleTypeLabels: Record<string, string> = {
  REQUIRED: "Zorunluluk",
  UNIQUE: "Tekillik",
  RANGE: "Aralık",
  REGEX: "Desen",
  FRESHNESS: "Güncellik",
  REFERENTIAL_INTEGRITY: "Referans bütünlüğü",
  CROSS_TABLE_CONSISTENCY: "Tablolar arası tutarlılık",
  CUSTOM_SQL: "Özel SQL",
};

const actionLabels: Record<RuleAction, string> = {
  CREATE_VERSION: "Sürüm Oluştur",
  TEST_RULE: "Test Et",
  ACTIVATE: "Aktifleştir",
  REQUEST_APPROVAL: "Onaya Gönder",
  DECIDE_APPROVAL: "Onayla/Reddet",
  WITHDRAW_APPROVAL: "Onayı Geri Çek",
  PASSIVATE: "Pasifleştir",
};

const actionIcons: Record<RuleAction, LucideIcon> = {
  CREATE_VERSION: FilePen,
  TEST_RULE: Activity,
  ACTIVATE: CheckCircle,
  REQUEST_APPROVAL: SendHorizontal,
  DECIDE_APPROVAL: ThumbsUp,
  WITHDRAW_APPROVAL: Undo2,
  PASSIVATE: PowerOff,
};

function ruleIcon(ruleType: string): LucideIcon {
  if (ruleType === "FRESHNESS") return Clock3;
  if (ruleType === "REFERENTIAL_INTEGRITY") return KeyRound;
  if (ruleType === "REGEX") return ScanText;
  if (ruleType === "CUSTOM_SQL") return Braces;
  return ListChecks;
}

function statusTone(status: string): "success" | "warning" | "unknown" {
  if (status === "ACTIVE") return "success";
  if (status === "REVIEW_REQUIRED") return "warning";
  return "unknown";
}

function criticalityTone(
  criticality: string,
): "critical" | "warning" | "info" | "unknown" {
  if (criticality === "CRITICAL") return "critical";
  if (criticality === "HIGH") return "warning";
  if (criticality === "MEDIUM") return "info";
  return "unknown";
}

interface RuleRowProps {
  item: RuleListItem;
  onAction: (item: RuleListItem, action: RuleAction) => void;
  actionLoading: string | null;
  catalogDatasets?: { id: string; name: string; namespace: string }[];
}

function RuleRow({ item, onAction, actionLoading, catalogDatasets }: RuleRowProps) {
  const datasetName = catalogDatasets?.find((ds) => ds.id === item.datasetId);
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const Icon = ruleIcon(item.ruleType);
  const open = Boolean(anchorEl);

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => setAnchorEl(null);

  const handleAction = (action: RuleAction) => {
    handleClose();
    onAction(item, action);
  };

  return (
    <Box
      component="li"
      sx={{
        alignItems: "center",
        borderBottom: 1,
        borderColor: "divider",
        display: "grid",
        gap: 3,
        gridTemplateColumns: {
          xs: "40px minmax(0, 1fr)",
          md: "40px minmax(260px, 1fr) minmax(145px, .65fr) minmax(110px, .5fr)",
          lg: "40px minmax(230px, 1.4fr) minmax(125px, .65fr) minmax(145px, .7fr) minmax(125px, .6fr) minmax(175px, .75fr) 40px",
        },
        minHeight: 84,
        px: 4,
        py: 3,
        "&:last-child": { borderBottom: 0 },
      }}
    >
      <Box
        aria-hidden="true"
        data-testid="rule-icon-slot"
        sx={(theme) => ({
          alignItems: "center",
          bgcolor: theme.status.infoSurface,
          borderRadius: 1,
          color: theme.status.info,
          display: "flex",
          height: 40,
          justifyContent: "center",
          width: 40,
        })}
      >
        <Icon size={designTokens.layout.navIconSize} strokeWidth={1.8} />
      </Box>
      <Box sx={{ minWidth: 0 }}>
        <Typography noWrap sx={{ fontWeight: 700 }}>{item.name}</Typography>
        <Typography color="text.secondary" noWrap variant="caption">
          {item.code} ·{" "}
          <Link
            to={`/catalog/datasets/${item.datasetId}`}
            style={{ color: "inherit", textDecoration: "underline" }}
          >
            {datasetName ? `${datasetName.namespace}.${datasetName.name}` : item.datasetId}
          </Link>
        </Typography>
      </Box>
      <Typography
        color="text.secondary"
        sx={{ display: { xs: "none", lg: "block" } }}
        variant="body2"
      >
        {dimensionLabels[item.dimension] ?? item.dimension}
      </Typography>
      <Box sx={{ gridColumn: { xs: "2", md: "auto" } }}>
        <StatusBadge
          label={statusLabels[item.status] ?? item.status}
          tone={statusTone(item.status)}
        />
      </Box>
      <Box sx={{ gridColumn: { xs: "2", md: "auto" } }}>
        <StatusBadge
          label={criticalityLabels[item.criticality] ?? item.criticality}
          tone={criticalityTone(item.criticality)}
        />
      </Box>
      <Box sx={{ display: { xs: "none", lg: "block" } }}>
        <Typography variant="body2">
          Sürüm {item.versionNo} · {ruleTypeLabels[item.ruleType] ?? item.ruleType}
        </Typography>
        <Typography color="text.secondary" sx={{ display: "block" }} variant="caption">
          {item.definitionSource === "CUSTOM_SQL" ? "Güvenli özel SQL" : "No-code şablon"} · {item.scopeType ?? "DATASET"} · {item.irVersion ?? "DQ_RULE_IR_V1"}
        </Typography>
        <Typography color="text.secondary" variant="caption">
          {new Intl.DateTimeFormat("tr-TR", {
            dateStyle: "medium",
            timeStyle: "short",
          }).format(new Date(item.createdAt))}
        </Typography>
      </Box>
      <Box>
        <Tooltip title="Eylemler">
          <IconButton
            aria-label={`${item.name} için eylemler`}
            data-testid="rule-actions-trigger"
            disabled={actionLoading === item.id}
            onClick={handleClick}
            size="small"
          >
            {actionLoading === item.id ? (
              <LoaderCircle aria-hidden="true" size={18} />
            ) : (
              <MoreVertical aria-hidden="true" size={18} />
            )}
          </IconButton>
        </Tooltip>
        <Menu
          anchorEl={anchorEl}
          anchorOrigin={{ horizontal: "right", vertical: "bottom" }}
          onClose={handleClose}
          open={open}
          slotProps={{ paper: { sx: { minWidth: 200 } } }}
          transformOrigin={{ horizontal: "right", vertical: "top" }}
        >
          {item.availableActions.map((action) => {
            const ActionIcon = actionIcons[action];
            return (
              <MenuItem
                key={action}
                data-testid={`rule-action-${action}`}
                onClick={() => handleAction(action)}
              >
                <ListItemIcon>
                  <ActionIcon aria-hidden="true" size={18} />
                </ListItemIcon>
                <ListItemText>{actionLabels[action]}</ListItemText>
              </MenuItem>
            );
          })}
          {item.availableActions.length === 0 && (
            <MenuItem disabled>
              <ListItemText>
                <Typography color="text.secondary" variant="body2">
                  Kullanılabilir eylem yok
                </Typography>
              </ListItemText>
            </MenuItem>
          )}
        </Menu>
      </Box>
    </Box>
  );
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
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("ALL");
  const [dimension, setDimension] = useState("ALL");
  const [criticality, setCriticality] = useState("ALL");
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formData, setFormData] = useState<RuleCreateRequest>({
    code: "",
    name: "",
    dataset_id: "",
    rule_type: "REQUIRED",
    primary_dimension: "COMPLETENESS",
    threshold: 100,
    weight: 1,
    criticality: "MEDIUM",
    owner_user_id: "",
    parameters: {},
  });

  // Action state
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [activeItem, setActiveItem] = useState<RuleListItem | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // Version dialog
  const [versionDialogOpen, setVersionDialogOpen] = useState(false);
  const [versionForm, setVersionForm] = useState<RuleVersionCreateRequest>({
    threshold: 100,
    weight: 1,
    criticality: "MEDIUM",
    parameters: {},
  });
  const [versionLoading, setVersionLoading] = useState(false);

  // Test result dialog
  const [testResultOpen, setTestResultOpen] = useState(false);
  const [testResult, setTestResult] = useState<RuleTestResult | null>(null);
  const [testLoading, setTestLoading] = useState(false);

  // Activation dialog
  const [activateDialogOpen, setActivateDialogOpen] = useState(false);
  const [activateLoading, setActivateLoading] = useState(false);

  // Approval request dialog
  const [approvalRequestDialogOpen, setApprovalRequestDialogOpen] = useState(false);
  const [approvalRequestLoading, setApprovalRequestLoading] = useState(false);

  // Approval decision dialog
  const [decisionDialogOpen, setDecisionDialogOpen] = useState(false);
  const [decision, setDecision] = useState<"APPROVE" | "REJECT">("APPROVE");
  const [decisionReason, setDecisionReason] = useState("");
  const [decisionLoading, setDecisionLoading] = useState(false);

  // Withdraw dialog
  const [withdrawDialogOpen, setWithdrawDialogOpen] = useState(false);
  const [withdrawReason, setWithdrawReason] = useState("");
  const [withdrawLoading, setWithdrawLoading] = useState(false);

  // Passivation dialog
  const [passivateDialogOpen, setPassivateDialogOpen] = useState(false);
  const [passivateLoading, setPassivateLoading] = useState(false);

  // Field selection for rule creation
  const [selectedFieldIds, setSelectedFieldIds] = useState<string[]>([]);

  // SQL editor for CUSTOM_SQL rules
  const [sqlText, setSqlText] = useState("");
  const [sqlTimeout, setSqlTimeout] = useState(30);
  const [sqlRowLimit, setSqlRowLimit] = useState(1000);
  const [sqlError, setSqlError] = useState<string | null>(null);
  const [sqlLoading, setSqlLoading] = useState(false);

  // Load fields when dataset changes in create dialog
  const handleDatasetChange = useCallback((datasetId: string) => {
    setFormData((prev) => ({ ...prev, dataset_id: datasetId }));
    setSelectedFieldIds([]);
    if (datasetId && onLoadFields) {
      void onLoadFields(datasetId);
    }
  }, [onLoadFields]);

  // Filter fields for the selected dataset
  const fieldsForDataset = useMemo(() => {
    if (!formData.dataset_id || !catalogFields) return [];
    return catalogFields.filter((f) => f.datasetId === formData.dataset_id);
  }, [formData.dataset_id, catalogFields]);

  // Validate SQL for CUSTOM_SQL rules
  const validateSql = useCallback((sql: string): string | null => {
    const trimmed = sql.trim();
    if (!trimmed) return "SQL sorgusu zorunludur.";
    const upper = trimmed.toUpperCase();
    if (!upper.startsWith("SELECT")) return "SQL sorgusu SELECT ile başlamalıdır.";
    const forbidden = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE", "CREATE"];
    for (const keyword of forbidden) {
      if (upper.includes(`${keyword} `)) return `SQL sorgusu ${keyword} içermemelidir.`;
    }
    return null;
  }, []);

  const handleCreateRule = () => {
    setDialogOpen(true);
    setCreateError(null);
  };

  const handleCloseDialog = () => {
    if (!createLoading) {
      setDialogOpen(false);
      setCreateError(null);
    }
  };

  const handleSubmit = async () => {
    if (createLoading) return;
    // Validate SQL if CUSTOM_SQL
    if (formData.rule_type === "CUSTOM_SQL") {
      const err = validateSql(sqlText);
      if (err) {
        setSqlError(err);
        return;
      }
      setSqlError(null);
    }
    setCreateLoading(true);
    setCreateError(null);
    try {
      if (onCreateRule) {
        // Build parameters with field references and SQL
        const parameters: Record<string, unknown> = { ...formData.parameters };
        if (selectedFieldIds.length > 0) {
          // Single-field rule types use field_id, multi-field use field_ids
          const singleFieldTypes = ["REQUIRED", "RANGE", "REGEX", "FRESHNESS"];
          if (singleFieldTypes.includes(formData.rule_type) && selectedFieldIds.length === 1) {
            parameters.field_id = selectedFieldIds[0];
          } else {
            parameters.field_ids = selectedFieldIds;
          }
        }
        if (formData.rule_type === "CUSTOM_SQL") {
          parameters.sql = sqlText.trim();
          parameters.timeout_seconds = sqlTimeout;
          parameters.row_limit = sqlRowLimit;
        }
        await onCreateRule({ ...formData, parameters });
      }
      setDialogOpen(false);
      setFormData({
        code: "",
        name: "",
        dataset_id: "",
        rule_type: "REQUIRED",
        primary_dimension: "COMPLETENESS",
        threshold: 100,
        weight: 1,
        criticality: "MEDIUM",
        owner_user_id: "",
        parameters: {},
      });
      setSelectedFieldIds([]);
      setSqlText("");
      setSqlTimeout(30);
      setSqlRowLimit(1000);
      setSqlError(null);
    } catch {
      setCreateError("Kural oluşturulamadı. Lütfen bilgileri kontrol edin.");
    } finally {
      setCreateLoading(false);
    }
  };

  const handleAction = (item: RuleListItem, action: RuleAction) => {
    setActiveItem(item);
    setActionError(null);

    switch (action) {
      case "CREATE_VERSION":
        setVersionForm({
          threshold: 100,
          weight: 1,
          criticality: item.criticality,
          parameters: {},
        });
        // Pre-populate SQL for CUSTOM_SQL rules
        setSqlText("");
        setSqlError(null);
        setSqlTimeout(30);
        setSqlRowLimit(1000);
        setSqlLoading(false);
        if (item.ruleType === "CUSTOM_SQL" && onLoadRuleDetail) {
          setSqlLoading(true);
          onLoadRuleDetail(item.id).then((definition) => {
            if (definition.sql) setSqlText(String(definition.sql));
            if (typeof definition.timeout_seconds === "number") setSqlTimeout(definition.timeout_seconds);
            if (typeof definition.row_limit === "number") setSqlRowLimit(definition.row_limit);
          }).catch(() => {
            // SQL pre-population failure is non-fatal
          }).finally(() => {
            setSqlLoading(false);
          });
        }
        setVersionDialogOpen(true);
        break;
      case "TEST_RULE":
        handleTestRule(item);
        break;
      case "ACTIVATE":
        setActivateDialogOpen(true);
        break;
      case "REQUEST_APPROVAL":
        setApprovalRequestDialogOpen(true);
        break;
      case "DECIDE_APPROVAL":
        setDecision("APPROVE");
        setDecisionReason("");
        setDecisionDialogOpen(true);
        break;
      case "WITHDRAW_APPROVAL":
        setWithdrawReason("");
        setWithdrawDialogOpen(true);
        break;
      case "PASSIVATE":
        setPassivateDialogOpen(true);
        break;
    }
  };

  const handleTestRule = async (item: RuleListItem) => {
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

  const handleCreateVersion = async () => {
    if (!activeItem || !onCreateVersion || versionLoading) return;
    // Validate SQL if CUSTOM_SQL
    if (activeItem.ruleType === "CUSTOM_SQL") {
      const err = validateSql(sqlText);
      if (err) {
        setSqlError(err);
        return;
      }
      setSqlError(null);
    }
    setVersionLoading(true);
    setActionError(null);
    try {
      const versionData = { ...versionForm };
      if (activeItem.ruleType === "CUSTOM_SQL") {
        versionData.parameters = {
          ...versionData.parameters,
          sql: sqlText.trim(),
          timeout_seconds: sqlTimeout,
          row_limit: sqlRowLimit,
        };
      }
      await onCreateVersion(activeItem, versionData);
      setVersionDialogOpen(false);
    } catch {
      setActionError("Sürüm oluşturulamadı.");
    } finally {
      setVersionLoading(false);
    }
  };

  const handleActivate = async () => {
    if (!activeItem || !onActivateRule || activateLoading) return;
    setActivateLoading(true);
    setActionError(null);
    try {
      await onActivateRule(activeItem);
      setActivateDialogOpen(false);
    } catch {
      setActionError("Kural aktifleştirilemedi.");
    } finally {
      setActivateLoading(false);
    }
  };

  const handleRequestApproval = async () => {
    if (!activeItem || !onRequestApproval || approvalRequestLoading) return;
    setApprovalRequestLoading(true);
    setActionError(null);
    try {
      await onRequestApproval(activeItem);
      setApprovalRequestDialogOpen(false);
    } catch {
      setActionError("Onay isteği gönderilemedi.");
    } finally {
      setApprovalRequestLoading(false);
    }
  };

  const handleDecideApproval = async () => {
    if (!activeItem || !onDecideApproval || decisionLoading) return;
    if (!decisionReason.trim()) {
      setActionError("Gerekçe kodu zorunludur.");
      return;
    }
    const approvalRequestId = activeItem.pendingApprovalRequestId;
    if (!approvalRequestId) {
      setActionError("Bu kural için bekleyen onay isteği bulunamadı.");
      return;
    }
    setDecisionLoading(true);
    setActionError(null);
    try {
      await onDecideApproval(activeItem, approvalRequestId, decision, decisionReason);
      setDecisionDialogOpen(false);
    } catch {
      setActionError("Onay kararı kaydedilemedi.");
    } finally {
      setDecisionLoading(false);
    }
  };

  const handleWithdrawApproval = async () => {
    if (!activeItem || !onWithdrawApproval || withdrawLoading) return;
    if (!withdrawReason.trim()) {
      setActionError("Gerekçe kodu zorunludur.");
      return;
    }
    const approvalRequestId = activeItem.pendingApprovalRequestId;
    if (!approvalRequestId) {
      setActionError("Bu kural için bekleyen onay isteği bulunamadı.");
      return;
    }
    setWithdrawLoading(true);
    setActionError(null);
    try {
      await onWithdrawApproval(activeItem, approvalRequestId, withdrawReason);
      setWithdrawDialogOpen(false);
    } catch {
      setActionError("Onay geri çekilemedi.");
    } finally {
      setWithdrawLoading(false);
    }
  };

  const handlePassivate = async () => {
    if (!activeItem || !onPassivateRule || passivateLoading) return;
    setPassivateLoading(true);
    setActionError(null);
    try {
      await onPassivateRule(activeItem);
      setPassivateDialogOpen(false);
    } catch {
      setActionError("Kural pasifleştirilemedi.");
    } finally {
      setPassivateLoading(false);
    }
  };

  const visibleItems = useMemo(
    () => items.filter((item) => {
      const searchable = `${item.name} ${item.code} ${item.datasetId} ${item.ruleType}`;
      return searchable.toLocaleLowerCase("tr-TR").includes(query.toLocaleLowerCase("tr-TR"))
        && (status === "ALL" || item.status === status)
        && (dimension === "ALL" || item.dimension === dimension)
        && (criticality === "ALL" || item.criticality === criticality);
    }),
    [criticality, dimension, items, query, status],
  );
  const effectiveItems = state === "long-content"
    ? Array.from({ length: 4 }, (_, group) => items.map((item) => ({
      ...item,
      id: `${item.id}-${group + 1}`,
      name: `${item.name} ${group + 1}`,
    }))).flat()
    : visibleItems;

  return (
    <AppShell currentPage="Kurallar">
      <Box sx={(theme) => ({ display: "grid", gap: 5, margin: "0 auto", maxWidth: theme.appLayout.contentMaxWidth, p: { xs: 3, md: 4, lg: 6 }, width: "100%" })}>
        <Box sx={{ alignItems: { md: "center" }, display: "flex", flexDirection: { xs: "column", md: "row" }, gap: 3, justifyContent: "space-between" }}>
          <Box>
            <Typography component="h1" variant="h1">Kurallar</Typography>
            <Typography color="text.secondary">Yetkili dataset kapsamınızdaki kural envanteri</Typography>
          </Box>
          {state !== "unauthorized" ? (
            <Box sx={{ display: "flex", gap: 2 }}>
              <Button
                onClick={handleCreateRule}
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

        {/* Kural Oluşturma Dialogu */}
        <Dialog
          aria-labelledby="create-rule-dialog-title"
          maxWidth="sm"
          onClose={handleCloseDialog}
          open={dialogOpen}
          fullWidth
        >
          <DialogTitle id="create-rule-dialog-title">Kural Oluştur</DialogTitle>
          <DialogContent>
            <Box sx={{ display: "grid", gap: 3, pt: 2 }}>
              <TextField
                autoFocus
                fullWidth
                label="Kod"
                onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                required
                value={formData.code}
              />
              <TextField
                fullWidth
                label="Ad"
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
                value={formData.name}
              />
              <FormControl fullWidth>
                <InputLabel id="dataset-id-label">Dataset</InputLabel>
                <Select
                  fullWidth
                  label="Dataset"
                  labelId="dataset-id-label"
                  onChange={(e) => handleDatasetChange(e.target.value)}
                  required
                  value={formData.dataset_id}
                >
                  {(catalogDatasets ?? []).map((ds) => (
                    <MenuItem key={ds.id} value={ds.id}>
                      {ds.name} ({ds.namespace})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              {/* Field multi-select (shown after dataset is chosen) */}
              {formData.dataset_id && fieldsForDataset.length > 0 && formData.rule_type !== "CUSTOM_SQL" ? (
                <FormControl fullWidth>
                  <InputLabel id="field-select-label">Alanlar</InputLabel>
                  <Select
                    fullWidth
                    label="Alanlar"
                    labelId="field-select-label"
                    multiple
                    onChange={(e) => {
                      const val = e.target.value;
                      setSelectedFieldIds(typeof val === "string" ? val.split(",") : val);
                    }}
                    renderValue={(selected) => (
                      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                        {(selected as string[]).map((id) => {
                          const f = fieldsForDataset.find((fd) => fd.id === id);
                          return <Chip key={id} label={f?.name ?? id} size="small" />;
                        })}
                      </Box>
                    )}
                    value={selectedFieldIds}
                  >
                    {fieldsForDataset.map((f) => (
                      <MenuItem key={f.id} value={f.id}>
                        {f.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              ) : null}
              <FormControl fullWidth>
                <InputLabel id="rule-type-label">Kural Tipi</InputLabel>
                <Select
                  label="Kural Tipi"
                  labelId="rule-type-label"
                  onChange={(e) => setFormData({ ...formData, rule_type: e.target.value })}
                  value={formData.rule_type}
                >
                  {Object.entries(ruleTypeLabels).map(([value, label]) => (
                    <MenuItem key={value} value={value}>{label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
              {/* SQL editor for CUSTOM_SQL */}
              {formData.rule_type === "CUSTOM_SQL" ? (
                <Box sx={{ display: "grid", gap: 2 }}>
                  <TextField
                    fullWidth
                    label="SQL Sorgusu"
                    multiline
                    minRows={6}
                    maxRows={16}
                    onChange={(e) => { setSqlText(e.target.value); setSqlError(null); }}
                    placeholder="SELECT ... -- Salt okunur SQL sorgusunu giriniz"
                    required
                    error={!!sqlError}
                    helperText={sqlError ?? "SELECT ile başlamalı; DROP, DELETE, INSERT, UPDATE içermemelidir."}
                    sx={{ "& .MuiInputBase-input": { fontFamily: "monospace", fontSize: 13 } }}
                    value={sqlText}
                  />
                  <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: "1fr 1fr" }}>
                    <TextField
                      fullWidth
                      label="Zaman Aşımı (sn)"
                      onChange={(e) => setSqlTimeout(Number(e.target.value))}
                      type="number"
                      value={sqlTimeout}
                    />
                    <TextField
                      fullWidth
                      label="Satır Limiti"
                      onChange={(e) => setSqlRowLimit(Number(e.target.value))}
                      type="number"
                      value={sqlRowLimit}
                    />
                  </Box>
                </Box>
              ) : null}
              <FormControl fullWidth>
                <InputLabel id="dimension-label">Birincil Boyut</InputLabel>
                <Select
                  label="Birincil Boyut"
                  labelId="dimension-label"
                  onChange={(e) => setFormData({ ...formData, primary_dimension: e.target.value })}
                  value={formData.primary_dimension}
                >
                  {Object.entries(dimensionLabels).map(([value, label]) => (
                    <MenuItem key={value} value={value}>{label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
              <TextField
                fullWidth
                label="Eşik Değeri (0-100)"
                onChange={(e) => setFormData({ ...formData, threshold: Number(e.target.value) })}
                required
                type="number"
                value={formData.threshold}
              />
              <TextField
                fullWidth
                label="Ağırlık"
                onChange={(e) => setFormData({ ...formData, weight: Number(e.target.value) })}
                required
                type="number"
                value={formData.weight}
              />
              <FormControl fullWidth>
                <InputLabel id="criticality-label">Kritiklik</InputLabel>
                <Select
                  label="Kritiklik"
                  labelId="criticality-label"
                  onChange={(e) => setFormData({ ...formData, criticality: e.target.value })}
                  value={formData.criticality}
                >
                  {Object.entries(criticalityLabels).map(([value, label]) => (
                    <MenuItem key={value} value={value}>{label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
              <TextField
                fullWidth
                label="Sahip Kullanıcı ID"
                onChange={(e) => setFormData({ ...formData, owner_user_id: e.target.value })}
                required
                value={formData.owner_user_id}
              />
            {createError ? (
                <Alert severity="error" sx={{ mb: 1 }}>{createError}</Alert>
              ) : null}
            </Box>
          </DialogContent>
          <DialogActions>
            <Button disabled={createLoading} onClick={handleCloseDialog}>İptal</Button>
            <Button disabled={createLoading} onClick={handleSubmit} variant="contained">{createLoading ? "Oluşturuluyor..." : "Oluştur"}</Button>
          </DialogActions>
        </Dialog>

        {/* Sürüm Oluşturma Dialogu */}
        <Dialog
          aria-labelledby="version-dialog-title"
          maxWidth="sm"
          onClose={() => { if (!versionLoading) setVersionDialogOpen(false); }}
          open={versionDialogOpen}
          fullWidth
        >
          <DialogTitle id="version-dialog-title">
            Yeni Sürüm Oluştur — {activeItem?.name}
          </DialogTitle>
          <DialogContent>
            <Box sx={{ display: "grid", gap: 3, pt: 2 }}>
              <TextField
                autoFocus
                fullWidth
                label="Eşik Değeri (0-100)"
                onChange={(e) => setVersionForm({ ...versionForm, threshold: Number(e.target.value) })}
                required
                type="number"
                value={versionForm.threshold}
              />
              <TextField
                fullWidth
                label="Ağırlık"
                onChange={(e) => setVersionForm({ ...versionForm, weight: Number(e.target.value) })}
                required
                type="number"
                value={versionForm.weight}
              />
              <FormControl fullWidth>
                <InputLabel id="version-criticality-label">Kritiklik</InputLabel>
                <Select
                  label="Kritiklik"
                  labelId="version-criticality-label"
                  onChange={(e) => setVersionForm({ ...versionForm, criticality: e.target.value })}
                  value={versionForm.criticality}
                >
                  {Object.entries(criticalityLabels).map(([value, label]) => (
                    <MenuItem key={value} value={value}>{label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
              {/* SQL editor for CUSTOM_SQL version */}
              {activeItem?.ruleType === "CUSTOM_SQL" ? (
                <Box sx={{ display: "grid", gap: 2 }}>
                  <Typography color="text.secondary" variant="body2">
                    SQL sorgusunu düzenleyin ve yeni sürüm oluşturun.
                  </Typography>
                  {sqlLoading ? (
                    <Skeleton height={120} />
                  ) : (
                    <TextField
                      fullWidth
                      label="SQL Sorgusu"
                      multiline
                      minRows={6}
                      maxRows={16}
                      onChange={(e) => { setSqlText(e.target.value); setSqlError(null); }}
                      placeholder="SELECT ... -- Salt okunur SQL sorgusunu giriniz"
                      required
                      error={!!sqlError}
                      helperText={sqlError ?? "SELECT ile başlamalı; DROP, DELETE, INSERT, UPDATE içermemelidir."}
                      sx={{ "& .MuiInputBase-input": { fontFamily: "monospace", fontSize: 13 } }}
                      value={sqlText}
                    />
                  )}
                  <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: "1fr 1fr" }}>
                    <TextField
                      fullWidth
                      label="Zaman Aşımı (sn)"
                      onChange={(e) => setSqlTimeout(Number(e.target.value))}
                      type="number"
                      value={sqlTimeout}
                    />
                    <TextField
                      fullWidth
                      label="Satır Limiti"
                      onChange={(e) => setSqlRowLimit(Number(e.target.value))}
                      type="number"
                      value={sqlRowLimit}
                    />
                  </Box>
                </Box>
              ) : null}
              {actionError ? (
                <Alert severity="error">{actionError}</Alert>
              ) : null}
            </Box>
          </DialogContent>
          <DialogActions>
            <Button disabled={versionLoading} onClick={() => setVersionDialogOpen(false)}>İptal</Button>
            <Button disabled={versionLoading} onClick={handleCreateVersion} variant="contained">
              {versionLoading ? "Oluşturuluyor..." : "Sürüm Oluştur"}
            </Button>
          </DialogActions>
        </Dialog>

        {/* Test Sonucu Dialogu */}
        <Dialog
          aria-labelledby="test-result-dialog-title"
          maxWidth="sm"
          onClose={() => setTestResultOpen(false)}
          open={testResultOpen}
          fullWidth
        >
          <DialogTitle id="test-result-dialog-title">Test Sonucu</DialogTitle>
          <DialogContent>
            {testResult ? (
              <Box sx={{ display: "grid", gap: 2, pt: 2 }}>
                <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: "1fr 1fr" }}>
                  <Box>
                    <Typography color="text.secondary" variant="caption">Kontrol Edilen</Typography>
                    <Typography variant="body1">{testResult.checked_count.toLocaleString("tr-TR")}</Typography>
                  </Box>
                  <Box>
                    <Typography color="text.secondary" variant="caption">Başarılı</Typography>
                    <Typography variant="body1" sx={{ color: "success.main" }}>{testResult.passed_count.toLocaleString("tr-TR")}</Typography>
                  </Box>
                  <Box>
                    <Typography color="text.secondary" variant="caption">Başarısız</Typography>
                    <Typography variant="body1" sx={{ color: "error.main" }}>{testResult.failed_count.toLocaleString("tr-TR")}</Typography>
                  </Box>
                  <Box>
                    <Typography color="text.secondary" variant="caption">Değerlendirilemeyen</Typography>
                    <Typography variant="body1">{testResult.not_evaluated_count.toLocaleString("tr-TR")}</Typography>
                  </Box>
                </Box>
                <Box>
                  <Typography color="text.secondary" variant="caption">Başarı Oranı</Typography>
                  <Typography variant="h6">
                    {testResult.success_rate !== null ? `${testResult.success_rate.toFixed(2)}%` : "—"}
                  </Typography>
                </Box>
                {testResult.preview_score !== null && (
                  <Box>
                    <Typography color="text.secondary" variant="caption">Önizleme Skoru</Typography>
                    <Typography variant="h6">{testResult.preview_score.toFixed(2)}</Typography>
                  </Box>
                )}
                <Box>
                  <Typography color="text.secondary" variant="caption">Durum</Typography>
                  <StatusBadge label={testResult.status} tone={testResult.status === "SUCCESS" ? "success" : "unknown"} />
                </Box>
                {testResult.message && (
                  <Box>
                    <Typography color="text.secondary" variant="caption">Mesaj</Typography>
                    <Typography variant="body2">{testResult.message}</Typography>
                  </Box>
                )}
                <Box>
                  <Typography color="text.secondary" variant="caption">Kayıt Limiti</Typography>
                  <Typography variant="body2">{testResult.record_limit.toLocaleString("tr-TR")}</Typography>
                </Box>
              </Box>
            ) : (
              <Box sx={{ py: 4, textAlign: "center" }}>
                <LoaderCircle aria-hidden="true" size={24} />
                <Typography>Test sonucu yükleniyor...</Typography>
              </Box>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setTestResultOpen(false)}>Kapat</Button>
          </DialogActions>
        </Dialog>

        {/* Aktivasyon Dialogu */}
        <Dialog
          aria-labelledby="activate-dialog-title"
          maxWidth="sm"
          onClose={() => { if (!activateLoading) setActivateDialogOpen(false); }}
          open={activateDialogOpen}
          fullWidth
        >
          <DialogTitle id="activate-dialog-title">Kuralı Aktifleştir</DialogTitle>
          <DialogContent>
            <Typography sx={{ pt: 2 }}>
              <strong>{activeItem?.name}</strong> kuralını aktifleştirmek istediğinize emin misiniz?
              {activeItem?.criticality === "CRITICAL" && (
                <Alert severity="warning" sx={{ mt: 2 }}>
                  Kritik kural aktivasyonu onay gerektirebilir. Lütfen "Onaya Gönder" eylemini kullanın.
                </Alert>
              )}
            </Typography>
            {actionError ? <Alert severity="error" sx={{ mt: 2 }}>{actionError}</Alert> : null}
          </DialogContent>
          <DialogActions>
            <Button disabled={activateLoading} onClick={() => setActivateDialogOpen(false)}>İptal</Button>
            <Button disabled={activateLoading} onClick={handleActivate} variant="contained">
              {activateLoading ? "Aktifleştiriliyor..." : "Aktifleştir"}
            </Button>
          </DialogActions>
        </Dialog>

        {/* Onay İsteği Dialogu */}
        <Dialog
          aria-labelledby="approval-request-dialog-title"
          maxWidth="sm"
          onClose={() => { if (!approvalRequestLoading) setApprovalRequestDialogOpen(false); }}
          open={approvalRequestDialogOpen}
          fullWidth
        >
          <DialogTitle id="approval-request-dialog-title">Onay İsteği Gönder</DialogTitle>
          <DialogContent>
            <Typography sx={{ pt: 2 }}>
              <strong>{activeItem?.name}</strong> kuralı için onay isteği gönderilecek. Bu işlem kuralı onay sürecine alır.
            </Typography>
            {actionError ? <Alert severity="error" sx={{ mt: 2 }}>{actionError}</Alert> : null}
          </DialogContent>
          <DialogActions>
            <Button disabled={approvalRequestLoading} onClick={() => setApprovalRequestDialogOpen(false)}>İptal</Button>
            <Button disabled={approvalRequestLoading} onClick={handleRequestApproval} variant="contained">
              {approvalRequestLoading ? "Gönderiliyor..." : "Onaya Gönder"}
            </Button>
          </DialogActions>
        </Dialog>

        {/* Onay Kararı Dialogu */}
        <Dialog
          aria-labelledby="decision-dialog-title"
          maxWidth="sm"
          onClose={() => { if (!decisionLoading) setDecisionDialogOpen(false); }}
          open={decisionDialogOpen}
          fullWidth
        >
          <DialogTitle id="decision-dialog-title">Onay Kararı — {activeItem?.name}</DialogTitle>
          <DialogContent>
            <Box sx={{ display: "grid", gap: 3, pt: 2 }}>
              <FormControl fullWidth>
                <InputLabel id="decision-label">Karar</InputLabel>
                <Select
                  label="Karar"
                  labelId="decision-label"
                  onChange={(e) => setDecision(e.target.value as "APPROVE" | "REJECT")}
                  value={decision}
                >
                  <MenuItem value="APPROVE">Onayla</MenuItem>
                  <MenuItem value="REJECT">Reddet</MenuItem>
                </Select>
              </FormControl>
              <TextField
                autoFocus
                fullWidth
                label="Gerekçe Kodu"
                onChange={(e) => setDecisionReason(e.target.value)}
                required
                value={decisionReason}
              />
              {actionError ? <Alert severity="error">{actionError}</Alert> : null}
            </Box>
          </DialogContent>
          <DialogActions>
            <Button disabled={decisionLoading} onClick={() => setDecisionDialogOpen(false)}>İptal</Button>
            <Button disabled={decisionLoading} onClick={handleDecideApproval} variant="contained">
              {decisionLoading ? "Kaydediliyor..." : "Kararı Kaydet"}
            </Button>
          </DialogActions>
        </Dialog>

        {/* Onay Geri Çekme Dialogu */}
        <Dialog
          aria-labelledby="withdraw-dialog-title"
          maxWidth="sm"
          onClose={() => { if (!withdrawLoading) setWithdrawDialogOpen(false); }}
          open={withdrawDialogOpen}
          fullWidth
        >
          <DialogTitle id="withdraw-dialog-title">Onayı Geri Çek — {activeItem?.name}</DialogTitle>
          <DialogContent>
            <Box sx={{ display: "grid", gap: 3, pt: 2 }}>
              <Typography>
                Bu onay isteğini geri çekmek istediğinize emin misiniz? Kural taslak durumunda kalacaktır.
              </Typography>
              <TextField
                autoFocus
                fullWidth
                label="Gerekçe Kodu"
                onChange={(e) => setWithdrawReason(e.target.value)}
                required
                value={withdrawReason}
              />
              {actionError ? <Alert severity="error">{actionError}</Alert> : null}
            </Box>
          </DialogContent>
          <DialogActions>
            <Button disabled={withdrawLoading} onClick={() => setWithdrawDialogOpen(false)}>İptal</Button>
            <Button disabled={withdrawLoading} onClick={handleWithdrawApproval} variant="contained">
              {withdrawLoading ? "Geri Çekiliyor..." : "Geri Çek"}
            </Button>
          </DialogActions>
        </Dialog>

        {/* Pasifleştirme Dialogu */}
        <Dialog
          aria-labelledby="passivate-dialog-title"
          maxWidth="sm"
          onClose={() => { if (!passivateLoading) setPassivateDialogOpen(false); }}
          open={passivateDialogOpen}
          fullWidth
        >
          <DialogTitle id="passivate-dialog-title">Kuralı Pasifleştir</DialogTitle>
          <DialogContent>
            <Alert severity="warning" sx={{ mt: 1 }}>
              <Typography sx={{ fontWeight: 700 }}>
                Bu işlem geri alınamaz — pasifleştirilen kural yeni çalıştırmalara dahil edilmez.
              </Typography>
              <Typography variant="body2" sx={{ mt: 1 }}>
                <strong>{activeItem?.name}</strong> kuralını pasifleştirmek istediğinize emin misiniz?
                Geçmiş sonuçlar korunur, ancak kural yeni execution'larda çalıştırılmaz.
              </Typography>
            </Alert>
            {actionError ? <Alert severity="error" sx={{ mt: 2 }}>{actionError}</Alert> : null}
          </DialogContent>
          <DialogActions>
            <Button disabled={passivateLoading} onClick={() => setPassivateDialogOpen(false)}>Vazgeç</Button>
            <Button disabled={passivateLoading} onClick={handlePassivate} variant="contained" color="error">
              {passivateLoading ? "Pasifleştiriliyor..." : "Pasifleştir"}
            </Button>
          </DialogActions>
        </Dialog>

        {state !== "unauthorized" ? (
          <Paper component="section" sx={{ borderRadius: 1.5, p: 4 }} variant="outlined">
            <Box aria-label="Kural filtreleri" sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", md: "minmax(240px, 1.4fr) repeat(3, minmax(150px, .7fr))" } }}>
              <TextField label="Kural ara" onChange={(event) => setQuery(event.target.value)} slotProps={{ input: { startAdornment: <Search aria-hidden="true" size={16} /> } }} value={query} />
              <FormControl><InputLabel id="rule-status-label">Durum</InputLabel><Select label="Durum" labelId="rule-status-label" onChange={(event) => setStatus(event.target.value)} value={status}><MenuItem value="ALL">Tüm durumlar</MenuItem>{Object.entries(statusLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
              <FormControl><InputLabel id="rule-dimension-label">Boyut</InputLabel><Select label="Boyut" labelId="rule-dimension-label" onChange={(event) => setDimension(event.target.value)} value={dimension}><MenuItem value="ALL">Tüm boyutlar</MenuItem>{Object.entries(dimensionLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
              <FormControl><InputLabel id="rule-criticality-label">Kritiklik</InputLabel><Select label="Kritiklik" labelId="rule-criticality-label" onChange={(event) => setCriticality(event.target.value)} value={criticality}><MenuItem value="ALL">Tüm seviyeler</MenuItem>{Object.entries(criticalityLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
            </Box>
          </Paper>
        ) : null}

        {actionError && state === "normal" ? (
          <Alert severity="error" sx={{ mb: 1 }}>{actionError}</Alert>
        ) : null}

        {state === "loading" ? <Box aria-busy="true" aria-label="Kurallar yükleniyor">{Array.from({ length: 5 }, (_, index) => <Skeleton height={84} key={index} />)}</Box> : null}
        {state === "empty" || state === "error" || state === "unauthorized" ? <StateMessage correlationId={correlationId} onRefresh={onRefresh} state={state} /> : null}
        {(state === "normal" || state === "long-content") && effectiveItems.length === 0 ? <StateMessage state="empty" /> : null}
        {(state === "normal" || state === "long-content") && effectiveItems.length > 0 ? (
          <Paper component="section" sx={{ borderRadius: 1.5, overflow: "hidden" }} variant="outlined">
            <Box sx={{ alignItems: "center", borderBottom: 1, borderColor: "divider", display: "flex", justifyContent: "space-between", px: 4, py: 3 }}>
              <Typography component="h2" variant="h3">Kural Envanteri</Typography>
              <Typography color="text.secondary" variant="body2">{effectiveItems.length} kural</Typography>
            </Box>
            <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>
              {effectiveItems.map((item) => (
                <RuleRow
                  item={item}
                  key={item.id}
                  onAction={handleAction}
                  actionLoading={actionLoading}
                  catalogDatasets={catalogDatasets}
                />
              ))}
            </Box>
          </Paper>
        ) : null}
      </Box>
    </AppShell>
  );
}
