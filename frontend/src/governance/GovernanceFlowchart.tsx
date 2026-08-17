import { Box, Chip, Paper, Stack, Typography } from "@mui/material";
import type { GovernanceApprovalItem } from "./model";
import {
  governanceRequestTypeLabels,
  governanceStatusLabels,
} from "./model";

/**
 * Tek bir yönetişim talebinin yaşam döngüsünü akış şeması olarak gösterir.
 * Her düğüm bir adımı temsil eder; aktif adım vurgulanır, geçmiş adımlar işaretlenir.
 */

interface FlowNode {
  id: string;
  label: string;
  statuses: string[];
  kind: "start" | "step" | "decision" | "terminal-success" | "terminal-fail" | "terminal-neutral";
}

type NodeState = "completed" | "active" | "inactive";

const mainFlow: FlowNode[] = [
  { id: "created", label: "Talep Oluşturuldu", statuses: [], kind: "start" },
  { id: "pending", label: "Onay Bekliyor", statuses: ["PENDING"], kind: "step" },
  { id: "decision", label: "Karar", statuses: [], kind: "decision" },
];

/** Her terminal durum için ulaşılan düğüm zincirini tanımlar. */
const statusPaths: Record<string, { completed: string[]; active: string }> = {
  PENDING: { completed: [], active: "pending" },
  APPROVED: { completed: ["created", "pending", "decision"], active: "approved" },
  APPLIED: { completed: ["created", "pending", "decision", "approved"], active: "applied" },
  APPLICATION_FAILED: { completed: ["created", "pending", "decision", "approved"], active: "failed" },
  REJECTED: { completed: ["created", "pending", "decision"], active: "rejected" },
  WITHDRAWN: { completed: ["created", "pending"], active: "withdrawn" },
  EXPIRED: { completed: ["created", "pending"], active: "expired" },
  INVALIDATED: { completed: ["created", "pending"], active: "invalidated" },
};

const allBranchNodes: Record<string, FlowNode> = {
  approved: { id: "approved", label: "Onaylandı", statuses: ["APPROVED"], kind: "step" },
  applied: { id: "applied", label: "Uygulandı", statuses: ["APPLIED"], kind: "terminal-success" },
  failed: { id: "failed", label: "Uygulama Başarısız", statuses: ["APPLICATION_FAILED"], kind: "terminal-fail" },
  rejected: { id: "rejected", label: "Reddedildi", statuses: ["REJECTED"], kind: "terminal-fail" },
  withdrawn: { id: "withdrawn", label: "Geri Çekildi", statuses: ["WITHDRAWN"], kind: "terminal-neutral" },
  expired: { id: "expired", label: "Süresi Geçti", statuses: ["EXPIRED"], kind: "terminal-neutral" },
  invalidated: { id: "invalidated", label: "Geçersizleştirildi", statuses: ["INVALIDATED"], kind: "terminal-neutral" },
};

function resolveNodeState(nodeId: string, itemStatus: string): NodeState {
  const path = statusPaths[itemStatus];
  if (!path) return "inactive";
  if (path.active === nodeId) return "active";
  if (path.completed.includes(nodeId)) return "completed";
  return "inactive";
}

const nodeColors: Record<FlowNode["kind"], { bg: string; border: string; text: string }> = {
  start: { bg: "#e3f2fd", border: "#1565c0", text: "#0d47a1" },
  step: { bg: "#fff3e0", border: "#e65100", text: "#bf360c" },
  decision: { bg: "#f3e5f5", border: "#6a1b9a", text: "#4a148c" },
  "terminal-success": { bg: "#e8f5e9", border: "#2e7d32", text: "#1b5e20" },
  "terminal-fail": { bg: "#ffebee", border: "#c62828", text: "#b71c1c" },
  "terminal-neutral": { bg: "#eceff1", border: "#546e7a", text: "#37474f" },
};

function FlowNodeBox({ node, state }: { node: FlowNode; state: NodeState }) {
  const colors = nodeColors[node.kind];
  const isDiamond = node.kind === "decision";
  const opacity = state === "inactive" ? 0.4 : 1;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", minWidth: 110, opacity, position: "relative" }}>
      <Box
        sx={{
          bgcolor: state !== "inactive" ? colors.bg : "#fafafa",
          border: `2px solid ${state !== "inactive" ? colors.border : "#bdbdbd"}`,
          borderRadius: isDiamond ? 1 : node.kind === "start" ? "50%" : 2,
          color: state === "inactive" ? "#9e9e9e" : colors.text,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontWeight: state === "active" ? 700 : 500,
          minHeight: isDiamond ? 52 : 44,
          minWidth: isDiamond ? 52 : 44,
          px: 1.5,
          py: 0.75,
          position: "relative",
          textAlign: "center",
          transition: "all 0.2s ease",
          ...(state === "active" && { boxShadow: `0 0 0 3px ${colors.border}33` }),
        }}
      >
        <Typography sx={{ fontSize: "0.7rem", fontWeight: "inherit", lineHeight: 1.2 }}>
          {node.label}
        </Typography>
        {state === "completed" && <CheckBadge />}
        {state === "active" && <ActiveDot color={colors.border} />}
      </Box>
    </Box>
  );
}

function CheckBadge() {
  return (
    <Box
      sx={{
        alignItems: "center",
        bgcolor: "#2e7d32",
        borderRadius: "50%",
        color: "#fff",
        display: "flex",
        fontSize: "0.65rem",
        height: 16,
        justifyContent: "center",
        position: "absolute",
        right: -6,
        top: -6,
        width: 16,
      }}
    >
      ✓
    </Box>
  );
}

function ActiveDot({ color }: { color: string }) {
  return (
    <Box
      sx={{
        bgcolor: color,
        borderRadius: "50%",
        height: 10,
        position: "absolute",
        right: -4,
        top: -4,
        width: 10,
      }}
    />
  );
}

function Arrow({ state }: { state: NodeState }) {
  const color = state === "inactive" ? "#bdbdbd" : state === "completed" ? "#2e7d32" : "#e65100";
  return (
    <Box
      sx={{
        color,
        display: "flex",
        flexShrink: 0,
        fontSize: "1.1rem",
        fontWeight: 700,
        mx: 0.25,
        mt: -1,
        alignItems: "center",
      }}
    >
      →
    </Box>
  );
}

function BranchArrow() {
  return (
    <Box sx={{ color: "#bdbdbd", fontSize: "0.9rem", fontWeight: 700, mx: 0.25, mt: -1, transform: "rotate(90deg)" }}>
      →
    </Box>
  );
}

function formatFlowDateTime(value: string | null): string {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "";
  return parsed.toLocaleString("tr-TR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getActiveBranchNodes(itemStatus: string): string[] {
  if (itemStatus === "APPROVED" || itemStatus === "APPLIED") return ["approved", "applied"];
  if (itemStatus === "APPLICATION_FAILED") return ["approved", "failed"];
  if (itemStatus === "REJECTED") return ["rejected"];
  if (itemStatus === "WITHDRAWN") return ["withdrawn"];
  if (itemStatus === "EXPIRED") return ["expired"];
  if (itemStatus === "INVALIDATED") return ["invalidated"];
  return [];
}

function FlowHeader({ item }: { item: GovernanceApprovalItem }) {
  const chipColor =
    item.status === "APPLIED" || item.status === "APPROVED"
      ? "success"
      : item.status === "REJECTED" || item.status === "APPLICATION_FAILED"
        ? "error"
        : item.status === "PENDING"
          ? "warning"
          : "default";

  return (
    <Stack direction="row" sx={{ alignItems: "center", justifyContent: "space-between", mb: 1.5 }}>
      <Stack direction="row" sx={{ gap: 1, alignItems: "center" }}>
        <Typography sx={{ fontWeight: 700, fontSize: "0.85rem" }}>
          {governanceRequestTypeLabels[item.requestType] ?? item.requestType}
        </Typography>
        <Typography color="text.secondary" sx={{ fontSize: "0.75rem" }}>
          {item.objectName}
        </Typography>
      </Stack>
      <Chip
        label={governanceStatusLabels[item.status] ?? item.status}
        size="small"
        color={chipColor as "success" | "error" | "warning" | "default"}
      />
    </Stack>
  );
}

function FlowTimestamps({ item }: { item: GovernanceApprovalItem }) {
  return (
    <Stack direction="row" sx={{ gap: 2, mt: 1.5, flexWrap: "wrap" }}>
      <Typography color="text.secondary" sx={{ fontSize: "0.65rem" }}>
        Talep: {formatFlowDateTime(item.requestedAt)}
      </Typography>
      {item.decidedAt ? (
        <Typography color="text.secondary" sx={{ fontSize: "0.65rem" }}>
          Karar: {formatFlowDateTime(item.decidedAt)}
        </Typography>
      ) : null}
      {item.expiresAt ? (
        <Typography color="text.secondary" sx={{ fontSize: "0.65rem" }}>
          Son tarih: {formatFlowDateTime(item.expiresAt)}
        </Typography>
      ) : null}
      {item.makerActorId ? (
        <Typography color="text.secondary" sx={{ fontSize: "0.65rem" }}>
          Maker: {item.makerActorId}
        </Typography>
      ) : null}
      {item.checkerActorId ? (
        <Typography color="text.secondary" sx={{ fontSize: "0.65rem" }}>
          Checker: {item.checkerActorId}
        </Typography>
      ) : null}
    </Stack>
  );
}

function FlowRow({ item }: { item: GovernanceApprovalItem }) {
  const activeBranches = getActiveBranchNodes(item.status);

  return (
    <Box sx={{ display: "flex", alignItems: "center", flexWrap: "nowrap" }}>
      {mainFlow.map((node, index) => (
        <Box key={node.id} sx={{ display: "flex", alignItems: "center" }}>
          {index > 0 && <Arrow state={resolveNodeState(node.id, item.status)} />}
          <FlowNodeBox node={node} state={resolveNodeState(node.id, item.status)} />
        </Box>
      ))}

      {activeBranches.map((branchId) => {
        const branchNode = allBranchNodes[branchId];
        if (!branchNode) return null;
        const isSideBranch = branchNode.kind === "terminal-neutral" || branchId === "rejected";
        const ArrowComponent = isSideBranch ? BranchArrow : Arrow;
        return (
          <Box key={branchId} sx={{ display: "flex", alignItems: "center" }}>
            <ArrowComponent state={resolveNodeState(branchId, item.status)} />
            <FlowNodeBox node={branchNode} state={resolveNodeState(branchId, item.status)} />
          </Box>
        );
      })}
    </Box>
  );
}

function FlowItemCard({ item }: { item: GovernanceApprovalItem }) {
  return (
    <Paper
      elevation={0}
      sx={{
        border: "1px solid",
        borderColor: "divider",
        overflow: "auto",
        p: 2,
        borderRadius: 2,
      }}
    >
      <FlowHeader item={item} />
      <FlowRow item={item} />
      <FlowTimestamps item={item} />
    </Paper>
  );
}

interface GovernanceFlowchartProps {
  items: GovernanceApprovalItem[];
}

export function GovernanceFlowchart({ items }: GovernanceFlowchartProps) {
  if (items.length === 0) return null;

  return (
    <Stack sx={{ gap: 2 }}>
      {items.map((item) => (
        <FlowItemCard key={item.approvalRequestId} item={item} />
      ))}
    </Stack>
  );
}
