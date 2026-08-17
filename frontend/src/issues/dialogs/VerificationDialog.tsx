import { useEffect, useState } from "react";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Typography,
} from "@mui/material";
import type { IssueActionFeedback } from "../labels";
import type { IssueListItem } from "../model";

export function VerificationDialog({
  item,
  pendingIssueId,
  onVerify,
  onNotify,
  setPendingIssueId,
  onClose,
}: {
  item?: IssueListItem;
  pendingIssueId?: string;
  onVerify?: (item: IssueListItem, verificationReferenceId: string) => Promise<void>;
  onNotify: (feedback: IssueActionFeedback | undefined) => void;
  setPendingIssueId: (id: string | undefined) => void;
  onClose: () => void;
}) {
  const [referenceId, setReferenceId] = useState("");
  useEffect(() => {
    if (!item) return;
    setReferenceId("");
  }, [item]);
  const submit = async () => {
    if (!item || !onVerify || pendingIssueId || !referenceId.trim()) return;
    setPendingIssueId(item.id);
    onNotify(undefined);
    try {
      await onVerify(item, referenceId.trim());
      onNotify({
        severity: "success",
        message: `${item.issueNo} doğrulandı.`,
      });
      onClose();
    } catch (error) {
      onNotify({
        severity: "error",
        message: error instanceof Error
          ? error.message
          : "Doğrulama tamamlanamadı. Sorunu yenileyip yeniden deneyin.",
      });
    } finally {
      setPendingIssueId(undefined);
    }
  };

  return (
    <Dialog
      aria-describedby="verification-dialog-description"
      fullWidth
      maxWidth="sm"
      onClose={onClose}
      open={Boolean(item)}
    >
      <DialogTitle>Çözümü doğrula</DialogTitle>
      <DialogContent sx={{ display: "grid", gap: 4, pt: 2 }}>
        <Typography color="text.secondary" id="verification-dialog-description">
          {item?.issueNo} çözümünü doğrulayın. Farklı bir güvenilir aktör tarafından onaylanmalıdır.
        </Typography>
        <Typography color="text.secondary" variant="caption">
          Doğrulandığında sorun Doğrulandı durumuna geçer ve değişiklik geçmişe yazılır.
        </Typography>
        <TextField
          label="Doğrulama referansı (UUID)"
          onChange={(event) => setReferenceId(event.target.value)}
          placeholder="00000000-0000-0000-0000-000000000000"
          value={referenceId}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Vazgeç</Button>
        <Button
          disabled={
            !referenceId.trim()
            || pendingIssueId === item?.id
          }
          onClick={() => void submit()}
          variant="contained"
        >
          {pendingIssueId === item?.id ? "Doğrulanıyor" : "Doğrula"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
