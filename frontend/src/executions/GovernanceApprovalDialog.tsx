import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, Typography } from "@mui/material";
import { Link } from "react-router-dom";

export interface GovernancePrompt {
  requestType: "EXECUTION_MANUAL_START" | "EXECUTION_CANCEL";
  objectId: string;
  reasonCode: string;
  proposedChanges: Record<string, unknown>;
  description: string;
}

export interface GovernancePromptResult {
  ok: boolean;
  message: string;
}

export function governancePromptForStart(ruleVersionIds: string[]): GovernancePrompt {
  return {
    requestType: "EXECUTION_MANUAL_START",
    objectId: "manual-execution",
    reasonCode: "EXECUTION.MANUAL.START",
    proposedChanges: { rule_version_ids: ruleVersionIds, execution_mode: "OFFICIAL" },
    description: `${ruleVersionIds.length} kural sürümü için kritik manuel çalıştırma`,
  };
}

export function governancePromptForCancel(executionId: string, reason: string): GovernancePrompt {
  return {
    requestType: "EXECUTION_CANCEL",
    objectId: executionId,
    reasonCode: "EXECUTION.CANCEL",
    proposedChanges: { reason },
    description: `${executionId} çalıştırmasının iptali`,
  };
}

interface GovernanceApprovalDialogProps {
  prompt: GovernancePrompt | null;
  submitting: boolean;
  result: GovernancePromptResult | null;
  canCreate: boolean;
  onClose: () => void;
  onSubmit: () => void;
}

/** Kritik çalıştırma 409'unda maker/checker onay talebine yönlendiren dialog. */
export function GovernanceApprovalDialog({
  prompt,
  submitting,
  result,
  canCreate,
  onClose,
  onSubmit,
}: GovernanceApprovalDialogProps) {
  return (
    <Dialog onClose={onClose} open={prompt !== null}>
      <DialogTitle>Yönetişim onayı gerekli</DialogTitle>
      <DialogContent sx={{ display: "grid", gap: 2, minWidth: { sm: 440 }, pt: "16px !important" }}>
        <Typography variant="body2">
          Bu eylem kritik (CRITICAL) bir dataset'i hedefliyor ve doğrudan çalıştırılamaz.
          Maker-checker akışı gereği önce yönetişim onay talebi açılır; talep DATA_OWNER
          tarafından onaylanır ve DATA_GOVERNANCE_SPECIALIST tarafından uygulanır.
        </Typography>
        {prompt ? (
          <Typography color="text.secondary" variant="body2">
            Talep: {prompt.description}
          </Typography>
        ) : null}
        {result ? (
          <Alert severity={result.ok ? "success" : "error"}>
            {result.message}
            {result.ok ? (
              <Stack component="span" sx={{ mt: 1 }}>
                <Link to="/governance">Yönetişim Görevleri ekranına git</Link>
              </Stack>
            ) : null}
          </Alert>
        ) : null}
        {!canCreate && !result ? (
          <Alert severity="info">
            Talebi yalnız DATA_STEWARD veya DATA_GOVERNANCE_SPECIALIST rolündeki kullanıcılar açabilir.
          </Alert>
        ) : null}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{result?.ok ? "Kapat" : "Vazgeç"}</Button>
        {!result ? (
          <Button disabled={!canCreate || submitting} onClick={onSubmit} variant="contained">
            Onaya Gönder
          </Button>
        ) : null}
      </DialogActions>
    </Dialog>
  );
}
