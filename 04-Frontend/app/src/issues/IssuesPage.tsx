import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
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
  AlertTriangle,
  BadgeCheck,
  Ban,
  CircleDot,
  CircleEllipsis,
  LoaderCircle,
  MoreVertical,
  RefreshCw,
  Search,
  SearchCheck,
  ShieldAlert,
  UserRoundPen,
  Wrench,
  FileCheck,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import { designTokens, type StatusTone } from "../theme/tokens";
import {
  syntheticIssues,
  type IssueAssigneeOption,
  type IssueListItem,
  type IssuePriority,
  type IssueState,
} from "./model";

interface IssuesPageProps {
  state?: IssueState;
  items?: IssueListItem[];
  correlationId?: string;
  onRefresh?: () => void;
  onStartInvestigation?: (item: IssueListItem) => Promise<void>;
  onLoadAssignmentOptions?: (item: IssueListItem) => Promise<IssueAssigneeOption[]>;
  onReassign?: (
    item: IssueListItem,
    assigneeUserId: string,
    priority: IssuePriority,
  ) => Promise<void>;
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

const statusLabels: Record<string, string> = {
  NEW: "Yeni",
  ASSIGNED: "Atandı",
  INVESTIGATING: "İnceleniyor",
  WAITING_FOR_RESOLUTION: "Çözüm bekliyor",
  RESOLVED: "Çözüldü",
  VERIFIED: "Doğrulandı",
  CLOSED: "Kapatıldı",
  CANCELLED: "İptal edildi",
};

const priorityLabels: Record<string, string> = {
  LOW: "Düşük",
  MEDIUM: "Orta",
  HIGH: "Yüksek",
  CRITICAL: "Kritik",
};

const triggerLabels: Record<string, string> = {
  QUALITY_THRESHOLD: "Kalite eşiği",
  CRITICAL_RULE_FAILURE: "Kritik kontrol",
  TECHNICAL_ERROR: "Teknik olay",
};

const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function localDateTimeValue(): string {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 16);
}

function statusTone(status: string): StatusTone {
  if (status === "RESOLVED" || status === "VERIFIED") return "success";
  if (status === "INVESTIGATING" || status === "ASSIGNED") return "info";
  if (status === "WAITING_FOR_RESOLUTION") return "warning";
  return "unknown";
}

function priorityTone(priority: string): StatusTone {
  if (priority === "CRITICAL") return "critical";
  if (priority === "HIGH") return "warning";
  if (priority === "MEDIUM") return "info";
  return "unknown";
}

function issuePresentation(item: IssueListItem): { icon: LucideIcon; tone: StatusTone } {
  if (item.sourceEventType === "TECHNICAL") return { icon: Wrench, tone: "technical" };
  if (item.priority === "CRITICAL") return { icon: ShieldAlert, tone: "critical" };
  if (item.status === "VERIFIED" || item.status === "RESOLVED") {
    return { icon: BadgeCheck, tone: "success" };
  }
  if (item.status === "CANCELLED") return { icon: Ban, tone: "unknown" };
  if (item.status === "INVESTIGATING") return { icon: CircleEllipsis, tone: "info" };
  if (item.priority === "HIGH") return { icon: AlertTriangle, tone: "warning" };
  return { icon: CircleDot, tone: "info" };
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function IssueRow({
  item,
  mutationPending,
  onReassign,
  onStartInvestigation,
  onResolve,
  onVerify,
  onClose,
}: {
  item: IssueListItem;
  mutationPending: boolean;
  onReassign?: (item: IssueListItem) => void;
  onStartInvestigation?: (item: IssueListItem) => void;
  onResolve?: (item: IssueListItem) => void;
  onVerify?: (item: IssueListItem) => void;
  onClose?: (item: IssueListItem) => void;
}) {
  const [menuAnchor, setMenuAnchor] = useState<HTMLElement | null>(null);
  const presentation = issuePresentation(item);
  const Icon = presentation.icon;
  const hasActions = item.availableActions.length > 0;
  const closeMenu = () => setMenuAnchor(null);
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
          md: "40px minmax(210px, 1fr) minmax(155px, auto)",
          lg: "40px minmax(210px, 1fr) minmax(130px, .58fr) minmax(110px, .48fr) minmax(170px, .72fr) minmax(155px, .65fr) minmax(150px, .6fr)",
        },
        minHeight: 88,
        px: 4,
        py: 3,
        "&:last-child": { borderBottom: 0 },
      }}
    >
      <Box
        aria-hidden="true"
        data-testid="issue-icon-slot"
        sx={(theme) => ({
          alignItems: "center",
          bgcolor: theme.status[`${presentation.tone}Surface`],
          borderRadius: 1,
          color: theme.status[presentation.tone],
          display: "flex",
          height: 40,
          justifyContent: "center",
          width: 40,
        })}
      >
        <Icon size={designTokens.layout.navIconSize} strokeWidth={1.8} />
      </Box>
      <Box sx={{ minWidth: 0 }}>
        <Typography noWrap sx={{ fontWeight: 700 }}>{item.issueNo}</Typography>
        <Typography color="text.secondary" noWrap variant="caption">
          {triggerLabels[item.triggerType] ?? item.triggerType} · {item.occurrenceCount} görülme
        </Typography>
      </Box>
      <Box
        sx={{
          gridColumn: { xs: "2", md: "3", lg: "auto" },
          justifySelf: { md: "end", lg: "start" },
        }}
      >
        <Typography color="text.secondary" sx={{ display: { xs: "block", lg: "none" } }} variant="caption">
          Durum
        </Typography>
        <StatusBadge
          label={statusLabels[item.status] ?? item.status}
          tone={statusTone(item.status)}
        />
      </Box>
      <Box sx={{ gridColumn: { xs: "2", md: "2", lg: "auto" } }}>
        <Typography color="text.secondary" sx={{ display: { xs: "block", lg: "none" } }} variant="caption">
          Öncelik
        </Typography>
        <StatusBadge
          label={priorityLabels[item.priority] ?? item.priority}
          tone={priorityTone(item.priority)}
        />
      </Box>
      <Box sx={{ display: { xs: "none", lg: "block" }, minWidth: 0 }}>
        <Typography noWrap variant="body2">{item.scopeId}</Typography>
        <Typography color="text.secondary" variant="caption">
          {item.scopeType === "SOURCE" ? "Veri kaynağı" : "Dataset"} · {item.sourceEventType === "TECHNICAL" ? "Teknik" : "Kalite"}
        </Typography>
      </Box>
      <Box sx={{ display: { xs: "none", lg: "block" } }}>
        <Typography variant="body2">{formatDate(item.updatedAt)}</Typography>
        <Typography color="text.secondary" variant="caption">
          Son görülme: {formatDate(item.lastSeenAt)}
        </Typography>
      </Box>
      <Box
        sx={{
          gridColumn: { xs: "2", md: "3", lg: "auto" },
          justifySelf: { md: "end", lg: "start" },
        }}
      >
        {hasActions ? (
          <>
            <Tooltip title="Sorun işlemleri">
              <span>
                <IconButton
                  aria-label={`${item.issueNo} işlemleri`}
                  disabled={mutationPending}
                  onClick={(event) => setMenuAnchor(event.currentTarget)}
                  size="small"
                >
                  {mutationPending
                    ? <LoaderCircle aria-hidden="true" size={18} />
                    : <MoreVertical aria-hidden="true" size={18} />}
                </IconButton>
              </span>
            </Tooltip>
            <Menu
              anchorEl={menuAnchor}
              onClose={closeMenu}
              open={Boolean(menuAnchor)}
            >
              {item.availableActions.includes("START_INVESTIGATION") ? (
                <MenuItem
                  onClick={() => {
                    closeMenu();
                    onStartInvestigation?.(item);
                  }}
                >
                  <ListItemIcon><SearchCheck aria-hidden="true" size={16} /></ListItemIcon>
                  <ListItemText>İncelemeye al</ListItemText>
                </MenuItem>
              ) : null}
              {item.availableActions.includes("REASSIGN") ? (
                <MenuItem
                  onClick={() => {
                    closeMenu();
                    onReassign?.(item);
                  }}
                >
                  <ListItemIcon><UserRoundPen aria-hidden="true" size={16} /></ListItemIcon>
                  <ListItemText>Yeniden ata</ListItemText>
                </MenuItem>
              ) : null}
              {item.availableActions.includes("RESOLVE") ? (
                <MenuItem
                  onClick={() => {
                    closeMenu();
                    onResolve?.(item);
                  }}
                >
                  <ListItemIcon><FileCheck aria-hidden="true" size={16} /></ListItemIcon>
                  <ListItemText>Çözüm kaydet</ListItemText>
                </MenuItem>
              ) : null}
              {item.availableActions.includes("VERIFY") ? (
                <MenuItem
                  onClick={() => {
                    closeMenu();
                    onVerify?.(item);
                  }}
                >
                  <ListItemIcon><ShieldCheck aria-hidden="true" size={16} /></ListItemIcon>
                  <ListItemText>Doğrula</ListItemText>
                </MenuItem>
              ) : null}
              {item.availableActions.includes("CLOSE") ? (
                <MenuItem
                  onClick={() => {
                    closeMenu();
                    onClose?.(item);
                  }}
                >
                  <ListItemIcon><BadgeCheck aria-hidden="true" size={16} /></ListItemIcon>
                  <ListItemText>Kapat</ListItemText>
                </MenuItem>
              ) : null}
            </Menu>
          </>
        ) : (
          <Typography
            aria-label="Kullanılabilir eylem yok"
            color="text.secondary"
            sx={{ display: { xs: "none", lg: "block" } }}
            variant="body2"
          >
            —
          </Typography>
        )}
      </Box>
    </Box>
  );
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

export function IssuesPage({
  state = "normal",
  items = syntheticIssues,
  correlationId,
  onLoadAssignmentOptions,
  onRefresh,
  onReassign,
  onResolve,
  onStartInvestigation,
  onVerify,
  onClose,
}: IssuesPageProps) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("ALL");
  const [priority, setPriority] = useState("ALL");
  const [period, setPeriod] = useState("ALL");
  const [pendingIssueId, setPendingIssueId] = useState<string>();
  const [assignmentItem, setAssignmentItem] = useState<IssueListItem>();
  const [assignmentOptions, setAssignmentOptions] = useState<IssueAssigneeOption[]>([]);
  const [assignmentOptionsState, setAssignmentOptionsState] = useState<
    "idle" | "loading" | "ready" | "error"
  >("idle");
  const [selectedAssigneeId, setSelectedAssigneeId] = useState("");
  const [selectedPriority, setSelectedPriority] = useState<IssuePriority>("MEDIUM");
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  const [resolutionItem, setResolutionItem] = useState<IssueListItem>();
  const [resolutionRootCause, setResolutionRootCause] = useState("");
  const [resolutionCorrectiveAction, setResolutionCorrectiveAction] = useState("");
  const [resolutionEvidenceRef, setResolutionEvidenceRef] = useState("");
  const [resolutionCompletedAt, setResolutionCompletedAt] = useState(localDateTimeValue());
  const [resolutionInitialCompletedAt, setResolutionInitialCompletedAt] = useState(
    resolutionCompletedAt,
  );
  const [resolutionConfirmDiscard, setResolutionConfirmDiscard] = useState(false);
  const [verificationItem, setVerificationItem] = useState<IssueListItem>();
  const [verificationReferenceId, setVerificationReferenceId] = useState("");
  const [closeItem, setCloseItem] = useState<IssueListItem>();
  const [actionFeedback, setActionFeedback] = useState<{
    severity: "success" | "error";
    message: string;
  }>();
  const newestTime = items.length
    ? Math.max(...items.map((item) => new Date(item.updatedAt).getTime()))
    : 0;
  const visibleItems = useMemo(
    () => items.filter((item) => {
      const searchable = `${item.issueNo} ${item.scopeId}`.toLocaleLowerCase("tr-TR");
      const ageDays = (newestTime - new Date(item.updatedAt).getTime()) / 86_400_000;
      return searchable.includes(query.toLocaleLowerCase("tr-TR"))
        && (status === "ALL" || item.status === status)
        && (priority === "ALL" || item.priority === priority)
        && (period === "ALL" || (period === "LATEST_DAY" ? ageDays < 1 : ageDays <= 7));
    }),
    [items, newestTime, period, priority, query, status],
  );
  const effectiveItems = state === "long-content"
    ? Array.from({ length: 4 }, (_, group) => items.map((item) => ({
      ...item,
      id: `${item.id}-${group + 1}`,
      issueNo: `${item.issueNo}-${group + 1}`,
    }))).flat()
    : visibleItems;
  const resetFilters = () => {
    setQuery("");
    setStatus("ALL");
    setPriority("ALL");
    setPeriod("ALL");
  };
  const startInvestigation = async (item: IssueListItem) => {
    if (!onStartInvestigation || pendingIssueId) return;
    setPendingIssueId(item.id);
    setActionFeedback(undefined);
    try {
      await onStartInvestigation(item);
      setActionFeedback({
        severity: "success",
        message: `${item.issueNo} incelemeye alındı.`,
      });
    } catch (error) {
      setActionFeedback({
        severity: "error",
        message: error instanceof Error
          ? error.message
          : "İşlem tamamlanamadı. Sorunu yenileyip yeniden deneyin.",
      });
    } finally {
      setPendingIssueId(undefined);
    }
  };
  const loadAssignmentOptions = async (item: IssueListItem) => {
    if (!onLoadAssignmentOptions) return;
    setAssignmentOptionsState("loading");
    try {
      const options = await onLoadAssignmentOptions(item);
      setAssignmentOptions(options);
      setAssignmentOptionsState("ready");
    } catch (error) {
      setAssignmentOptions([]);
      setAssignmentOptionsState("error");
      setActionFeedback({
        severity: "error",
        message: error instanceof Error
          ? error.message
          : "Atama seçenekleri yüklenemedi. Yeniden deneyin.",
      });
    }
  };
  const openAssignment = (item: IssueListItem) => {
    setAssignmentItem(item);
    setSelectedAssigneeId("");
    setSelectedPriority(item.priority);
    setAssignmentOptions([]);
    setActionFeedback(undefined);
    void loadAssignmentOptions(item);
  };
  const closeAssignment = () => {
    setAssignmentItem(undefined);
    setAssignmentOptions([]);
    setAssignmentOptionsState("idle");
    setSelectedAssigneeId("");
    setConfirmDiscard(false);
  };
  const requestAssignmentClose = () => {
    if (
      assignmentItem
      && (selectedAssigneeId || selectedPriority !== assignmentItem.priority)
    ) {
      setConfirmDiscard(true);
      return;
    }
    closeAssignment();
  };
  const openResolution = (item: IssueListItem) => {
    const completedAt = localDateTimeValue();
    setResolutionItem(item);
    setResolutionRootCause("");
    setResolutionCorrectiveAction("");
    setResolutionEvidenceRef("");
    setResolutionCompletedAt(completedAt);
    setResolutionInitialCompletedAt(completedAt);
    setActionFeedback(undefined);
  };
  const closeResolution = () => {
    setResolutionItem(undefined);
    setResolutionRootCause("");
    setResolutionCorrectiveAction("");
    setResolutionEvidenceRef("");
    setResolutionConfirmDiscard(false);
  };
  const requestResolutionClose = () => {
    if (
      resolutionItem
      && (
        resolutionRootCause
        || resolutionCorrectiveAction
        || resolutionEvidenceRef
        || resolutionCompletedAt !== resolutionInitialCompletedAt
      )
    ) {
      setResolutionConfirmDiscard(true);
      return;
    }
    closeResolution();
  };
  const submitResolution = async () => {
    if (!resolutionItem || !onResolve || pendingIssueId) return;
    const completedAt = new Date(resolutionCompletedAt);
    if (
      !resolutionRootCause.trim()
      || !resolutionCorrectiveAction.trim()
      || !uuidPattern.test(resolutionEvidenceRef.trim())
      || Number.isNaN(completedAt.getTime())
      || completedAt > new Date()
    ) return;
    setPendingIssueId(resolutionItem.id);
    setActionFeedback(undefined);
    try {
      await onResolve(
        resolutionItem,
        resolutionRootCause.trim(),
        resolutionCorrectiveAction.trim(),
        resolutionEvidenceRef.trim(),
        completedAt.toISOString(),
      );
      setActionFeedback({
        severity: "success",
        message: `${resolutionItem.issueNo} çözüm kaydı oluşturuldu.`,
      });
      closeResolution();
    } catch (error) {
      setActionFeedback({
        severity: "error",
        message: error instanceof Error
          ? error.message
          : "Çözüm kaydedilemedi. Sorunu yenileyip yeniden deneyin.",
      });
    } finally {
      setPendingIssueId(undefined);
    }
  };
  const openVerification = (item: IssueListItem) => {
    setVerificationItem(item);
    setVerificationReferenceId("");
    setActionFeedback(undefined);
  };
  const closeVerification = () => {
    setVerificationItem(undefined);
    setVerificationReferenceId("");
  };
  const submitVerification = async () => {
    if (!verificationItem || !onVerify || pendingIssueId) return;
    if (!verificationReferenceId.trim()) return;
    setPendingIssueId(verificationItem.id);
    setActionFeedback(undefined);
    try {
      await onVerify(verificationItem, verificationReferenceId.trim());
      setActionFeedback({
        severity: "success",
        message: `${verificationItem.issueNo} doğrulandı.`,
      });
      closeVerification();
    } catch (error) {
      setActionFeedback({
        severity: "error",
        message: error instanceof Error
          ? error.message
          : "Doğrulama tamamlanamadı. Sorunu yenileyip yeniden deneyin.",
      });
    } finally {
      setPendingIssueId(undefined);
    }
  };
  const openClose = (item: IssueListItem) => {
    setCloseItem(item);
    setActionFeedback(undefined);
  };
  const closeClose = () => {
    setCloseItem(undefined);
  };
  const submitClose = async () => {
    if (!closeItem || !onClose || pendingIssueId) return;
    setPendingIssueId(closeItem.id);
    setActionFeedback(undefined);
    try {
      await onClose(closeItem);
      setActionFeedback({
        severity: "success",
        message: `${closeItem.issueNo} kapatıldı.`,
      });
      closeClose();
    } catch (error) {
      setActionFeedback({
        severity: "error",
        message: error instanceof Error
          ? error.message
          : "Kapatma tamamlanamadı. Sorunu yenileyip yeniden deneyin.",
      });
    } finally {
      setPendingIssueId(undefined);
    }
  };
  const submitAssignment = async () => {
    if (!assignmentItem || !selectedAssigneeId || !onReassign || pendingIssueId) return;
    setPendingIssueId(assignmentItem.id);
    setActionFeedback(undefined);
    try {
      await onReassign(assignmentItem, selectedAssigneeId, selectedPriority);
      setActionFeedback({
        severity: "success",
        message: `${assignmentItem.issueNo} yeniden atandı.`,
      });
      closeAssignment();
    } catch (error) {
      setActionFeedback({
        severity: "error",
        message: error instanceof Error
          ? error.message
          : "Atama tamamlanamadı. Sorunu yenileyip yeniden deneyin.",
      });
    } finally {
      setPendingIssueId(undefined);
    }
  };

  return (
    <AppShell currentPage="Sorunlar">
      <Box sx={(theme) => ({ display: "grid", gap: 5, margin: "0 auto", maxWidth: theme.appLayout.contentMaxWidth, p: { xs: 3, md: 4, lg: 6 }, width: "100%" })}>
        <Box sx={{ alignItems: { md: "center" }, display: "flex", flexDirection: { xs: "column", md: "row" }, gap: 3, justifyContent: "space-between" }}>
          <Box>
            <Typography component="h1" variant="h1">Sorunlar</Typography>
            <Typography color="text.secondary">Yetkili kapsamınızdaki kalite ve teknik sorunları inceleyin ve yönetin</Typography>
          </Box>
          {state !== "unauthorized" ? <Button onClick={onRefresh} startIcon={<RefreshCw aria-hidden="true" size={16} />} variant="contained">Yenile</Button> : null}
        </Box>

        {state !== "unauthorized" ? (
          <Paper component="section" sx={{ borderRadius: 1.5, p: 4 }} variant="outlined">
            <Box aria-label="Sorun filtreleri" sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(180px, 1fr))", lg: "minmax(230px, 1.35fr) repeat(4, minmax(145px, .7fr))" } }}>
              <TextField label="Sorun ara" onChange={(event) => setQuery(event.target.value)} slotProps={{ input: { startAdornment: <Search aria-hidden="true" size={16} /> } }} value={query} />
              <FormControl><InputLabel id="issue-status-label">Durum</InputLabel><Select label="Durum" labelId="issue-status-label" onChange={(event) => setStatus(event.target.value)} value={status}><MenuItem value="ALL">Tüm durumlar</MenuItem>{Object.entries(statusLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
              <FormControl><InputLabel id="issue-priority-label">Öncelik</InputLabel><Select label="Öncelik" labelId="issue-priority-label" onChange={(event) => setPriority(event.target.value)} value={priority}><MenuItem value="ALL">Tüm öncelikler</MenuItem>{Object.entries(priorityLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
              <FormControl><InputLabel id="issue-period-label">Tarih</InputLabel><Select label="Tarih" labelId="issue-period-label" onChange={(event) => setPeriod(event.target.value)} value={period}><MenuItem value="ALL">Tüm tarihler</MenuItem><MenuItem value="LATEST_DAY">Son güncellenen gün</MenuItem><MenuItem value="LAST_7_DAYS">Son 7 gün</MenuItem></Select></FormControl>
              <FormControl><InputLabel id="issue-scope-label">Kapsam</InputLabel><Select disabled label="Kapsam" labelId="issue-scope-label" value="AUTHORIZED"><MenuItem value="AUTHORIZED">Yetkili kapsam</MenuItem></Select></FormControl>
            </Box>
            <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 3 }}>
              <Button onClick={resetFilters} size="small">Filtreleri temizle</Button>
            </Box>
          </Paper>
        ) : null}

        {actionFeedback ? (
          <Alert aria-live="polite" severity={actionFeedback.severity}>
            {actionFeedback.message}
          </Alert>
        ) : null}
        <Dialog
          aria-describedby="assignment-dialog-description"
          fullWidth
          maxWidth="sm"
          onClose={requestAssignmentClose}
          open={Boolean(assignmentItem) && !confirmDiscard}
        >
          <DialogTitle>Sorunu yeniden ata</DialogTitle>
          <DialogContent sx={{ display: "grid", gap: 4, pt: 2 }}>
            <Typography color="text.secondary" id="assignment-dialog-description">
              {assignmentItem?.issueNo} için yeni sorumlu ve öncelik seçin.
            </Typography>
            <Typography color="text.secondary" variant="caption">
              Kaydedildiğinde sorun Atandı durumuna döner ve değişiklik geçmişe yazılır.
            </Typography>
            {assignmentOptionsState === "loading" ? (
              <Box aria-label="Atama seçenekleri yükleniyor" sx={{ display: "grid", gap: 2 }}>
                <Skeleton height={56} />
                <Skeleton height={56} />
              </Box>
            ) : null}
            {assignmentOptionsState === "error" && assignmentItem ? (
              <Alert
                action={
                  <Button
                    color="inherit"
                    onClick={() => void loadAssignmentOptions(assignmentItem)}
                  >
                    Yeniden dene
                  </Button>
                }
                severity="error"
              >
                Atama seçenekleri yüklenemedi.
              </Alert>
            ) : null}
            {assignmentOptionsState === "ready" ? (
              <>
                {assignmentOptions.length ? (
                  <FormControl>
                    <InputLabel id="assignment-user-label">Yeni sorumlu</InputLabel>
                    <Select
                      label="Yeni sorumlu"
                      labelId="assignment-user-label"
                      onChange={(event) => setSelectedAssigneeId(event.target.value)}
                      value={selectedAssigneeId}
                    >
                      {assignmentOptions.map((option) => (
                        <MenuItem key={option.userId} value={option.userId}>
                          {option.displayName}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                ) : (
                  <Alert severity="info">
                    Bu kapsam için atanabilir kullanıcı bulunamadı.
                  </Alert>
                )}
                <FormControl>
                  <InputLabel id="assignment-priority-label">Öncelik</InputLabel>
                  <Select
                    label="Öncelik"
                    labelId="assignment-priority-label"
                    onChange={(event) => (
                      setSelectedPriority(event.target.value as IssuePriority)
                    )}
                    value={selectedPriority}
                  >
                    {Object.entries(priorityLabels).map(([value, label]) => (
                      <MenuItem key={value} value={value}>{label}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </>
            ) : null}
          </DialogContent>
          <DialogActions>
            <Button onClick={requestAssignmentClose}>Vazgeç</Button>
            <Button
              disabled={
                assignmentOptionsState !== "ready"
                || !selectedAssigneeId
                || pendingIssueId === assignmentItem?.id
              }
              onClick={() => void submitAssignment()}
              variant="contained"
            >
              {pendingIssueId === assignmentItem?.id ? "Kaydediliyor" : "Kaydet"}
            </Button>
          </DialogActions>
        </Dialog>
        <Dialog
          aria-describedby="resolution-dialog-description"
          fullWidth
          maxWidth="sm"
          onClose={requestResolutionClose}
          open={Boolean(resolutionItem) && !resolutionConfirmDiscard}
        >
          <DialogTitle>Çözüm kaydet</DialogTitle>
          <DialogContent sx={{ display: "grid", gap: 4, pt: 2 }}>
            <Typography color="text.secondary" id="resolution-dialog-description">
              {resolutionItem?.issueNo} için kök neden ve düzeltici faaliyeti kaydedin.
            </Typography>
            <Typography color="text.secondary" variant="caption">
              Kaydedildiğinde sorun Çözüldü durumuna geçer ve değişiklik geçmişe yazılır.
            </Typography>
            <TextField
              label="Kök neden"
              maxRows={6}
              minRows={3}
              multiline
              onChange={(event) => setResolutionRootCause(event.target.value)}
              required
              slotProps={{ htmlInput: { maxLength: 4000 } }}
              value={resolutionRootCause}
            />
            <TextField
              label="Düzeltici faaliyet"
              maxRows={6}
              minRows={3}
              multiline
              onChange={(event) => setResolutionCorrectiveAction(event.target.value)}
              required
              slotProps={{ htmlInput: { maxLength: 4000 } }}
              value={resolutionCorrectiveAction}
            />
            <TextField
              error={Boolean(resolutionEvidenceRef) && !uuidPattern.test(resolutionEvidenceRef)}
              helperText={
                resolutionEvidenceRef && !uuidPattern.test(resolutionEvidenceRef)
                  ? "Geçerli bir UUID girin."
                  : "Ham kayıt veya hassas veri yerine güvenli kanıt referansı kullanın."
              }
              label="Kanıt referansı (UUID)"
              onChange={(event) => setResolutionEvidenceRef(event.target.value)}
              placeholder="00000000-0000-0000-0000-000000000000"
              required
              value={resolutionEvidenceRef}
            />
            <TextField
              error={
                !resolutionCompletedAt
                || new Date(resolutionCompletedAt) > new Date()
              }
              helperText={
                !resolutionCompletedAt || new Date(resolutionCompletedAt) > new Date()
                  ? "Tamamlanma zamanı gelecekte olamaz."
                  : "Yerel saat, kayıtta UTC olarak saklanır."
              }
              label="Tamamlanma zamanı"
              onChange={(event) => setResolutionCompletedAt(event.target.value)}
              required
              slotProps={{ htmlInput: { max: localDateTimeValue() } }}
              type="datetime-local"
              value={resolutionCompletedAt}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={requestResolutionClose}>Vazgeç</Button>
            <Button
              disabled={
                !resolutionRootCause.trim()
                || !resolutionCorrectiveAction.trim()
                || !uuidPattern.test(resolutionEvidenceRef.trim())
                || !resolutionCompletedAt
                || new Date(resolutionCompletedAt) > new Date()
                || pendingIssueId === resolutionItem?.id
              }
              onClick={() => void submitResolution()}
              variant="contained"
            >
              {pendingIssueId === resolutionItem?.id ? "Kaydediliyor" : "Kaydet"}
            </Button>
          </DialogActions>
        </Dialog>
        <Dialog
          aria-describedby="verification-dialog-description"
          fullWidth
          maxWidth="sm"
          onClose={closeVerification}
          open={Boolean(verificationItem)}
        >
          <DialogTitle>Çözümü doğrula</DialogTitle>
          <DialogContent sx={{ display: "grid", gap: 4, pt: 2 }}>
            <Typography color="text.secondary" id="verification-dialog-description">
              {verificationItem?.issueNo} çözümünü doğrulayın. Farklı bir güvenilir aktör tarafından onaylanmalıdır.
            </Typography>
            <Typography color="text.secondary" variant="caption">
              Doğrulandığında sorun Doğrulandı durumuna geçer ve değişiklik geçmişe yazılır.
            </Typography>
            <TextField
              label="Doğrulama referansı (UUID)"
              onChange={(event) => setVerificationReferenceId(event.target.value)}
              placeholder="00000000-0000-0000-0000-000000000000"
              value={verificationReferenceId}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={closeVerification}>Vazgeç</Button>
            <Button
              disabled={
                !verificationReferenceId.trim()
                || pendingIssueId === verificationItem?.id
              }
              onClick={() => void submitVerification()}
              variant="contained"
            >
              {pendingIssueId === verificationItem?.id ? "Doğrulanıyor" : "Doğrula"}
            </Button>
          </DialogActions>
        </Dialog>
        <Dialog
          aria-describedby="close-dialog-description"
          fullWidth
          maxWidth="sm"
          onClose={closeClose}
          open={Boolean(closeItem)}
        >
          <DialogTitle>Sorunu kapat</DialogTitle>
          <DialogContent sx={{ display: "grid", gap: 4, pt: 2 }}>
            <Typography color="text.secondary" id="close-dialog-description">
              {closeItem?.issueNo} sorununu kapatıyorsunuz. Kapatma işlemi geri alınamaz.
            </Typography>
            <Typography color="text.secondary" variant="caption">
              Kapatıldığında sorun Kapatıldı durumuna geçer ve değişiklik geçmişe yazılır.
            </Typography>
          </DialogContent>
          <DialogActions>
            <Button onClick={closeClose}>Vazgeç</Button>
            <Button
              disabled={pendingIssueId === closeItem?.id}
              onClick={() => void submitClose()}
              variant="contained"
            >
              {pendingIssueId === closeItem?.id ? "Kapatılıyor" : "Kapat"}
            </Button>
          </DialogActions>
        </Dialog>
        <Dialog
          aria-describedby="discard-assignment-description"
          onClose={() => setConfirmDiscard(false)}
          open={confirmDiscard}
        >
          <DialogTitle>Değişiklikler kaydedilmedi</DialogTitle>
          <DialogContent>
            <Typography id="discard-assignment-description">
              Kaydedilmemiş atama değişikliklerinden vazgeçilsin mi?
            </Typography>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setConfirmDiscard(false)}>Forma dön</Button>
            <Button color="error" onClick={closeAssignment}>Değişiklikleri sil</Button>
          </DialogActions>
        </Dialog>
        <Dialog
          aria-describedby="discard-resolution-description"
          onClose={() => setResolutionConfirmDiscard(false)}
          open={resolutionConfirmDiscard}
        >
          <DialogTitle>Değişiklikler kaydedilmedi</DialogTitle>
          <DialogContent>
            <Typography id="discard-resolution-description">
              Kaydedilmemiş çözüm değişikliklerinden vazgeçilsin mi?
            </Typography>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setResolutionConfirmDiscard(false)}>Forma dön</Button>
            <Button color="error" onClick={closeResolution}>Değişiklikleri sil</Button>
          </DialogActions>
        </Dialog>
        {state === "loading" ? <Box aria-busy="true" aria-label="Sorunlar yükleniyor">{Array.from({ length: 6 }, (_, index) => <Skeleton height={88} key={index} />)}</Box> : null}
        {state === "empty" || state === "error" || state === "unauthorized" ? <StateMessage correlationId={correlationId} onRefresh={onRefresh} state={state} /> : null}
        {(state === "normal" || state === "long-content") && effectiveItems.length === 0 ? <StateMessage state="empty" /> : null}
        {(state === "normal" || state === "long-content") && effectiveItems.length > 0 ? (
          <Paper component="section" sx={{ borderRadius: 1.5, overflow: "hidden" }} variant="outlined">
            <Box sx={{ alignItems: "center", borderBottom: 1, borderColor: "divider", display: "flex", justifyContent: "space-between", px: 4, py: 3 }}>
              <Typography component="h2" variant="h3">Sorun Envanteri</Typography>
              <Typography color="text.secondary" variant="body2">{effectiveItems.length} kayıt · en fazla 100</Typography>
            </Box>
            <Box
              aria-hidden="true"
              sx={{
                borderBottom: 1,
                borderColor: "divider",
                color: "text.secondary",
                display: { xs: "none", lg: "grid" },
                fontSize: "caption.fontSize",
                fontWeight: 700,
                gap: 3,
                gridTemplateColumns: "40px minmax(210px, 1fr) minmax(130px, .58fr) minmax(110px, .48fr) minmax(170px, .72fr) minmax(155px, .65fr) minmax(150px, .6fr)",
                px: 4,
                py: 2,
              }}
            >
              <Box />
              <Box>Sorun</Box>
              <Box>Durum</Box>
              <Box>Öncelik</Box>
              <Box>Kapsam ve tür</Box>
              <Box>Son hareket</Box>
              <Box>İşlem</Box>
            </Box>
            <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>
              {effectiveItems.map((item) => (
                <IssueRow
                  item={item}
                  key={item.id}
                  mutationPending={pendingIssueId === item.id}
                  onReassign={openAssignment}
                  onResolve={openResolution}
                  onVerify={openVerification}
                  onClose={openClose}
                  onStartInvestigation={(selected) => void startInvestigation(selected)}
                />
              ))}
            </Box>
          </Paper>
        ) : null}
      </Box>
    </AppShell>
  );
}
