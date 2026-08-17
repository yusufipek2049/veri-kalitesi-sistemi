import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Typography,
} from "@mui/material";
import { LoaderCircle } from "lucide-react";
import { StatusBadge } from "../../components/StatusBadge";
import type { RuleTestResult } from "../model";

interface TestResultDialogProps {
  open: boolean;
  result: RuleTestResult | null;
  onClose: () => void;
}

function TestResultCounts({ result }: { result: RuleTestResult }) {
  return (
    <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: "1fr 1fr" }}>
      <Box>
        <Typography color="text.secondary" variant="caption">Kontrol Edilen</Typography>
        <Typography variant="body1">{result.checked_count.toLocaleString("tr-TR")}</Typography>
      </Box>
      <Box>
        <Typography color="text.secondary" variant="caption">Başarılı</Typography>
        <Typography variant="body1" sx={{ color: "success.main" }}>{result.passed_count.toLocaleString("tr-TR")}</Typography>
      </Box>
      <Box>
        <Typography color="text.secondary" variant="caption">Başarısız</Typography>
        <Typography variant="body1" sx={{ color: "error.main" }}>{result.failed_count.toLocaleString("tr-TR")}</Typography>
      </Box>
      <Box>
        <Typography color="text.secondary" variant="caption">Değerlendirilemeyen</Typography>
        <Typography variant="body1">{result.not_evaluated_count.toLocaleString("tr-TR")}</Typography>
      </Box>
    </Box>
  );
}

export function TestResultDialog({ open, result, onClose }: TestResultDialogProps) {
  return (
    <Dialog
      aria-labelledby="test-result-dialog-title"
      maxWidth="sm"
      onClose={onClose}
      open={open}
      fullWidth
    >
      <DialogTitle id="test-result-dialog-title">Test Sonucu</DialogTitle>
      <DialogContent>
        {result ? (
          <Box sx={{ display: "grid", gap: 2, pt: 2 }}>
            <TestResultCounts result={result} />
            <Box>
              <Typography color="text.secondary" variant="caption">Başarı Oranı</Typography>
              <Typography variant="h6">
                {result.success_rate !== null ? `${result.success_rate.toFixed(2)}%` : "—"}
              </Typography>
            </Box>
            {result.preview_score !== null && (
              <Box>
                <Typography color="text.secondary" variant="caption">Önizleme Skoru</Typography>
                <Typography variant="h6">{result.preview_score.toFixed(2)}</Typography>
              </Box>
            )}
            <Box>
              <Typography color="text.secondary" variant="caption">Durum</Typography>
              <StatusBadge label={result.status} tone={result.status === "SUCCESS" ? "success" : "unknown"} />
            </Box>
            {result.message && (
              <Box>
                <Typography color="text.secondary" variant="caption">Mesaj</Typography>
                <Typography variant="body2">{result.message}</Typography>
              </Box>
            )}
            <Box>
              <Typography color="text.secondary" variant="caption">Kayıt Limiti</Typography>
              <Typography variant="body2">{result.record_limit.toLocaleString("tr-TR")}</Typography>
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
        <Button onClick={onClose}>Kapat</Button>
      </DialogActions>
    </Dialog>
  );
}
