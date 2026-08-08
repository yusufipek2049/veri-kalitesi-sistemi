import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { Link } from "react-router-dom";
import { fetchScores, ScoreApiError } from "./api";
import { scoresFromApi, type ScoreListItem, type ScoreState } from "./model";
import { AppShell } from "../components/AppShell";

const scopeLabel: Record<string, string> = {
  RULE: "Kural",
  DATASET: "Veri Kümesi",
  DIMENSION: "Boyut",
  SOURCE: "Kaynak",
  ENTERPRISE: "Kurum",
};

const statusColor = (status: string): "success" | "warning" | "error" | "default" => {
  switch (status) {
    case "CALCULATED":
      return "success";
    case "PARTIAL":
      return "warning";
    case "NOT_CALCULATED":
    case "NOT_CALCULATED_TECHNICAL_ERROR":
    case "CONFIG_ERROR":
      return "error";
    default:
      return "default";
  }
};

const levelColor = (level: string | null): "success" | "warning" | "error" | "default" => {
  switch (level) {
    case "GOOD":
      return "success";
    case "ACCEPTABLE":
      return "warning";
    case "RISKY":
    case "CRITICAL":
      return "error";
    default:
      return "default";
  }
};

export function ScoresPage() {
  const [state, setState] = useState<ScoreState>("loading");
  const [scores, setScores] = useState<ScoreListItem[]>([]);
  const [errorKind, setErrorKind] = useState<string | null>(null);

  const load = useCallback(async (signal: AbortSignal) => {
    setState("loading");
    setErrorKind(null);
    try {
      const response = await fetchScores({ limit: 100 }, signal);
      const items = scoresFromApi(response);
      if (items.length === 0) {
        setState("empty");
      } else {
        setScores(items);
        setState("normal");
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      if (error instanceof ScoreApiError) {
        if (error.kind === "unauthorized" || error.kind === "forbidden") {
          setState("unauthorized");
        } else {
          setErrorKind(error.kind);
          setState("error");
        }
      } else {
        setErrorKind("technical");
        setState("error");
      }
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const content = useMemo(() => {
    if (state === "loading") {
      return (
        <Box sx={{ alignItems: "center", display: "flex", justifyContent: "center", py: 10 }}>
          <CircularProgress aria-label="Skorlar yükleniyor" />
        </Box>
      );
    }
    if (state === "unauthorized") {
      return <Alert severity="warning">Bu sayfayı görüntüleme yetkiniz yok.</Alert>;
    }
    if (state === "error") {
      return <Alert severity="error">Skorlar yüklenemedi ({errorKind}).</Alert>;
    }
    if (state === "empty") {
      return <Alert severity="info">Henüz yayınlanmış skor bulunmuyor.</Alert>;
    }
    return (
      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Skor ID</TableCell>
              <TableCell>Kapsam</TableCell>
              <TableCell>Değer</TableCell>
              <TableCell>Seviye</TableCell>
              <TableCell>Durum</TableCell>
              <TableCell>Yayın</TableCell>
              <TableCell>Hesaplama</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {scores.map((score) => (
              <TableRow key={score.id} hover>
                <TableCell>
                  <Link to={`/scores/${score.id}`}>{score.id.slice(0, 8)}…</Link>
                </TableCell>
                <TableCell>
                  <Chip label={scopeLabel[score.scopeType] ?? score.scopeType} size="small" />
                  {score.scopeId ? ` ${score.scopeId.slice(0, 8)}` : ""}
                </TableCell>
                <TableCell>{score.scoreValue !== null ? score.scoreValue.toFixed(2) : "—"}</TableCell>
                <TableCell>
                  {score.level ? (
                    <Chip color={levelColor(score.level)} label={score.level} size="small" />
                  ) : (
                    "—"
                  )}
                </TableCell>
                <TableCell>
                  <Chip color={statusColor(score.scoreStatus)} label={score.scoreStatus} size="small" />
                </TableCell>
                <TableCell>{score.publicationId ? "Yayında" : "—"}</TableCell>
                <TableCell>{new Date(score.calculatedAt).toLocaleString("tr-TR")}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    );
  }, [state, scores, errorKind]);

  return (
    <AppShell currentPage="Skorlar">
      <Stack sx={{ gap: 4, p: { md: 4, lg: 6 } }}>
        <Typography variant="h4">Skorlar</Typography>
        {content}
      </Stack>
    </AppShell>
  );
}
