import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Alert,
  Box,
  CircularProgress,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import { fetchScoreComparison, ScoreApiError } from "./api";
import { comparisonFromApi, type ScoreComparisonResult, type ScoreState } from "./model";
import { AppShell } from "../components/AppShell";

const comparisonLabel: Record<string, string> = {
  COMPARABLE: "Karşılaştırılabilir",
  NOT_COMPARABLE: "Karşılaştırılamaz",
  UNKNOWN: "Belirsiz",
};

export function ScoreComparisonPage() {
  const [searchParams] = useSearchParams();
  const currentId = searchParams.get("current") ?? "";
  const previousId = searchParams.get("previous") ?? "";
  const [state, setState] = useState<ScoreState>("loading");
  const [result, setResult] = useState<ScoreComparisonResult | null>(null);
  const [errorKind, setErrorKind] = useState<string | null>(null);

  const load = useCallback(
    async (signal: AbortSignal) => {
      if (!currentId || !previousId) {
        setState("empty");
        return;
      }
      setState("loading");
      setErrorKind(null);
      try {
        const response = await fetchScoreComparison(currentId, previousId, signal);
        setResult(comparisonFromApi(response));
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
    [currentId, previousId],
  );

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  if (state === "loading") {
    return (
      <AppShell currentPage="Skor Karşılaştırma">
        <Box sx={{ alignItems: "center", display: "flex", justifyContent: "center", py: 10 }}>
          <CircularProgress aria-label="Karşılaştırma yükleniyor" />
        </Box>
      </AppShell>
    );
  }

  if (state === "unauthorized") {
    return (
      <AppShell currentPage="Skor Karşılaştırma">
        <Alert severity="warning">Bu sayfayı görüntüleme yetkiniz yok.</Alert>
      </AppShell>
    );
  }

  if (state === "error") {
    return (
      <AppShell currentPage="Skor Karşılaştırma">
        <Alert severity="error">Karşılaştırma yüklenemedi ({errorKind}).</Alert>
      </AppShell>
    );
  }

  if (state === "empty" || !result) {
    return (
      <AppShell currentPage="Skor Karşılaştırma">
        <Alert severity="info">Karşılaştırma için iki skor ID gerekli.</Alert>
      </AppShell>
    );
  }

  return (
    <AppShell currentPage="Skor Karşılaştırma">
      <Stack sx={{ gap: 4, p: { md: 4, lg: 6 } }}>
        <Typography variant="h4">Skor Karşılaştırma</Typography>
        <Paper sx={{ p: 4, variant: "outlined" }}>
          <Stack sx={{ gap: 2 }}>
            <Typography variant="body2" color="text.secondary">Durum</Typography>
            <Typography variant="h6">
              {comparisonLabel[result.comparisonStatus] ?? result.comparisonStatus}
            </Typography>
            <Typography variant="body2" color="text.secondary">Mevcut Skor</Typography>
            <Typography variant="body1">{result.currentScoreId}</Typography>
            <Typography variant="body2" color="text.secondary">Önceki Skor</Typography>
            <Typography variant="body1">{result.previousScoreId}</Typography>
            {result.deltaValue !== null && (
              <>
                <Typography variant="body2" color="text.secondary">Fark</Typography>
                <Typography variant="h6">
                  {result.deltaValue > 0 ? "+" : ""}
                  {result.deltaValue.toFixed(2)}
                </Typography>
              </>
            )}
            {result.deltaValue === null && result.comparisonStatus !== "COMPARABLE" && (
              <Alert severity="info">Delta hesaplanamadı.</Alert>
            )}
            {result.reasonCodes.length > 0 && (
              <>
                <Typography variant="body2" color="text.secondary">Neden Kodları</Typography>
                <Typography variant="body2">{result.reasonCodes.join(", ")}</Typography>
              </>
            )}
          </Stack>
        </Paper>
      </Stack>
    </AppShell>
  );
}
