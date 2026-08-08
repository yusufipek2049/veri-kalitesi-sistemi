import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import { fetchScoreDetail, reproduceScore, ScoreApiError } from "./api";
import { scoreDetailFromApi, type ScoreDetail, type ScoreState } from "./model";
import { AppShell } from "../components/AppShell";

type ReproductionState = "idle" | "loading" | "match" | "mismatch" | "error";

export function ScoreDetailPage() {
  const { scoreId } = useParams<{ scoreId: string }>();
  const [state, setState] = useState<ScoreState>("loading");
  const [detail, setDetail] = useState<ScoreDetail | null>(null);
  const [reproduction, setReproduction] = useState<ReproductionState>("idle");
  const [errorKind, setErrorKind] = useState<string | null>(null);

  const load = useCallback(
    async (signal: AbortSignal) => {
      if (!scoreId) return;
      setState("loading");
      try {
        const response = await fetchScoreDetail(scoreId, signal);
        setDetail(scoreDetailFromApi(response));
        setState("normal");
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
    },
    [scoreId],
  );

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const handleReproduce = async () => {
    if (!scoreId) return;
    setReproduction("loading");
    try {
      const result = await reproduceScore(scoreId);
      setReproduction(result.matches ? "match" : "mismatch");
    } catch {
      setReproduction("error");
    }
  };

  if (state === "loading") {
    return (
      <AppShell currentPage="Skor Detayı">
        <Box sx={{ alignItems: "center", display: "flex", justifyContent: "center", py: 10 }}>
          <CircularProgress aria-label="Skor yükleniyor" />
        </Box>
      </AppShell>
    );
  }

  if (state === "unauthorized") {
    return (
      <AppShell currentPage="Skor Detayı">
        <Alert severity="warning">Bu skoru görüntüleme yetkiniz yok.</Alert>
      </AppShell>
    );
  }

  if (state === "error" || !detail) {
    return (
      <AppShell currentPage="Skor Detayı">
        <Alert severity="error">Skor yüklenemedi ({errorKind}).</Alert>
      </AppShell>
    );
  }

  const { item } = detail;

  return (
    <AppShell currentPage="Skor Detayı">
      <Stack sx={{ gap: 4, p: { md: 4, lg: 6 } }}>
        <Typography variant="h4">Skor Detayı</Typography>
        <Paper sx={{ p: 4, variant: "outlined" }}>
          <Stack sx={{ gap: 2 }}>
            <Typography variant="body2" color="text.secondary">Skor ID</Typography>
            <Typography variant="body1">{item.id}</Typography>
            <Typography variant="body2" color="text.secondary">Kapsam</Typography>
            <Typography variant="body1">
              <Chip label={item.scopeType} size="small" />
              {item.scopeId ? ` — ${item.scopeId}` : ""}
            </Typography>
            <Typography variant="body2" color="text.secondary">Değer / Seviye</Typography>
            <Typography variant="h5">
              {item.scoreValue !== null ? item.scoreValue.toFixed(2) : "—"}
              {item.level ? ` (${item.level})` : ""}
            </Typography>
            <Typography variant="body2" color="text.secondary">Durum</Typography>
            <Chip label={item.scoreStatus} size="small" />
            {detail.publication && (
              <>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>Yayın</Typography>
                <Typography variant="body1">
                  {detail.publication.period} — {detail.publication.status}
                </Typography>
              </>
            )}
            {detail.availableActions.includes("reproduce") && (
              <Box sx={{ mt: 2 }}>
                <Button
                  disabled={reproduction === "loading"}
                  onClick={handleReproduce}
                  variant="outlined"
                >
                  {reproduction === "loading" ? "Yeniden üretiliyor…" : "Yeniden Üret"}
                </Button>
                {reproduction === "match" && (
                  <Alert severity="success" sx={{ mt: 1 }}>Yeniden üretim eşleşti.</Alert>
                )}
                {reproduction === "mismatch" && (
                  <Alert severity="warning" sx={{ mt: 1 }}>Yeniden üretim eşleşmedi.</Alert>
                )}
                {reproduction === "error" && (
                  <Alert severity="error" sx={{ mt: 1 }}>Yeniden üretim başarısız.</Alert>
                )}
              </Box>
            )}
          </Stack>
        </Paper>
      </Stack>
    </AppShell>
  );
}
