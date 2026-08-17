import { Box, Typography } from "@mui/material";
import { Link } from "react-router-dom";
import { StatusBadge } from "../components/StatusBadge";
import { designTokens } from "../theme/tokens";
import {
  criticalityLabels,
  criticalityTone,
  dimensionLabels,
  ruleIcon,
  ruleTypeLabels,
  statusLabels,
  statusTone,
} from "./labels";
import type { RuleAction, RuleListItem } from "./model";
import { RuleActionMenu } from "./RuleActionMenu";

interface RuleRowProps {
  item: RuleListItem;
  onAction: (item: RuleListItem, action: RuleAction) => void;
  actionLoading: string | null;
  catalogDatasets?: { id: string; name: string; namespace: string }[];
}

function RuleRowMeta({ item }: { item: RuleListItem }) {
  return (
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
  );
}

export function RuleRow({ item, onAction, actionLoading, catalogDatasets }: RuleRowProps) {
  const datasetName = catalogDatasets?.find((ds) => ds.id === item.datasetId);
  const Icon = ruleIcon(item.ruleType);

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
      <RuleRowMeta item={item} />
      <RuleActionMenu
        item={item}
        loading={actionLoading === item.id}
        onAction={onAction}
      />
    </Box>
  );
}
