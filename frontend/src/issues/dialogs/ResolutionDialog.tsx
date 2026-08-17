import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Skeleton,
  TextField,
  Typography,
} from "@mui/material";
import {
  localDateTimeValue,
  type IssueActionFeedback,
} from "../labels";
import {
  issueEvidenceOptions,
  type IssueEvidenceCandidate,
  type IssueEvidenceOption,
  type IssueEvidenceRecord,
  type IssueListItem,
} from "../model";
import { DiscardConfirmDialog } from "./DiscardConfirmDialog";
import { EvidenceUploadPanel } from "./EvidenceUploadPanel";

type EvidenceState = "idle" | "loading" | "ready" | "error";

interface ResolutionDialogProps {
  item?: IssueListItem;
  pendingIssueId?: string;
  onLoadEvidence?: (item: IssueListItem) => Promise<{
    records: IssueEvidenceRecord[];
    candidates: IssueEvidenceCandidate[];
  }>;
  onCaptureEvidence?: (
    item: IssueListItem,
    candidateKey: string,
  ) => Promise<IssueEvidenceRecord>;
  onUploadEvidence?: (
    item: IssueListItem, file: File, label: string, classification: string,
    onProgress: (percentage: number) => void,
  ) => Promise<IssueEvidenceRecord>;
  onDownloadEvidence?: (item: IssueListItem, evidenceId: string) => Promise<void>;
  onResolve?: (
    item: IssueListItem,
    rootCause: string,
    correctiveAction: string,
    evidenceReferenceId: string,
    completedAt: string,
  ) => Promise<void>;
  onNotify: (feedback: IssueActionFeedback | undefined) => void;
  setPendingIssueId: (id: string | undefined) => void;
  onClose: () => void;
}

function ResolutionEvidenceSection({
  evidenceState,
  evidenceOptions,
  selection,
  onSelect,
  onRetry,
}: {
  evidenceState: EvidenceState;
  evidenceOptions: IssueEvidenceOption[];
  selection: string;
  onSelect: (value: string) => void;
  onRetry: () => void;
}) {
  if (evidenceState === "loading") {
    return (
      <Box aria-label="Kanıtlar yükleniyor" sx={{ display: "grid", gap: 2 }}>
        <Skeleton height={56} />
      </Box>
    );
  }
  if (evidenceState === "error") {
    return (
      <Alert
        action={<Button color="inherit" onClick={onRetry}>Yeniden dene</Button>}
        severity="error"
      >
        Kanıtlar yüklenemedi.
      </Alert>
    );
  }
  if (evidenceState !== "ready") return null;
  if (!evidenceOptions.length) {
    return (
      <Alert severity="warning">
        Bu sorun için kanıt bulunamadı. Kapsamdaki kuralı çalıştırıp
        yeniden deneyin; kanıt olmadan çözüm kaydedilemez.
      </Alert>
    );
  }
  return (
    <FormControl>
      <InputLabel id="resolution-evidence-label">Kanıt</InputLabel>
      <Select
        label="Kanıt"
        labelId="resolution-evidence-label"
        onChange={(event) => onSelect(event.target.value)}
        value={selection}
      >
        {evidenceOptions.map((option) => (
          <MenuItem key={option.value} value={option.value}>
            {option.label}
          </MenuItem>
        ))}
      </Select>
      <Typography color="text.secondary" sx={{ mt: 1 }} variant="caption">
        Kanıtlar kural çalıştırmasının sonuç ve loglarından gelir; seçim
        kaydedildiğinde çözüm o kanıda bağlanır.
      </Typography>
    </FormControl>
  );
}

// Aday seçildiyse önce kalıcı kanıt kaydına dönüştürülür; çözüm ancak
// gerçek bir kanıt kaydının kimliğine bağlanabilir.
async function captureOrSelectEvidenceId(
  item: IssueListItem,
  selected: IssueEvidenceOption,
  onCaptureEvidence?: ResolutionDialogProps["onCaptureEvidence"],
): Promise<string> {
  if (selected.kind === "record") return selected.record.evidenceId;
  if (!onCaptureEvidence) {
    throw new Error("Kanıt kaydı oluşturulamıyor. Sayfayı yenileyip yeniden deneyin.");
  }
  const captured = await onCaptureEvidence(item, selected.candidate.candidateKey);
  return captured.evidenceId;
}

function canSubmitResolution({
  target,
  onResolve,
  pendingIssueId,
  rootCause,
  correctiveAction,
  selected,
  completedAtDate,
}: {
  target?: IssueListItem;
  onResolve?: ResolutionDialogProps["onResolve"];
  pendingIssueId?: string;
  rootCause: string;
  correctiveAction: string;
  selected?: IssueEvidenceOption;
  completedAtDate: Date;
}): boolean {
  return Boolean(
    target && onResolve && !pendingIssueId
    && rootCause.trim()
    && correctiveAction.trim()
    && selected
    && !Number.isNaN(completedAtDate.getTime())
    && completedAtDate <= new Date(),
  );
}

function useResolutionForm({
  item,
  pendingIssueId,
  onLoadEvidence,
  onCaptureEvidence,
  onResolve,
  onNotify,
  setPendingIssueId,
  onClose,
}: ResolutionDialogProps) {
  const [rootCause, setRootCause] = useState("");
  const [correctiveAction, setCorrectiveAction] = useState("");
  const [evidenceSelection, setEvidenceSelection] = useState("");
  const [evidenceOptions, setEvidenceOptions] = useState<IssueEvidenceOption[]>([]);
  const [evidenceState, setEvidenceState] = useState<EvidenceState>("idle");
  const [uploadedEvidence, setUploadedEvidence] = useState<IssueEvidenceRecord[]>([]);
  const [completedAt, setCompletedAt] = useState(localDateTimeValue());
  const [initialCompletedAt, setInitialCompletedAt] = useState(completedAt);
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  const loadEvidence = useCallback(async (target: IssueListItem) => {
    if (!onLoadEvidence) {
      setEvidenceOptions([]);
      setEvidenceState("ready");
      return;
    }
    setEvidenceState("loading");
    try {
      const { records, candidates } = await onLoadEvidence(target);
      setUploadedEvidence(records.filter((record) => record.kind === "UPLOADED_FILE"));
      setEvidenceOptions(issueEvidenceOptions(records, candidates));
      setEvidenceState("ready");
    } catch {
      setEvidenceOptions([]);
      setEvidenceState("error");
    }
  }, [onLoadEvidence]);
  useEffect(() => {
    if (!item) return;
    setRootCause("");
    setCorrectiveAction("");
    setEvidenceSelection("");
    setEvidenceOptions([]);
    setEvidenceState("idle");
    setUploadedEvidence([]);
    const now = localDateTimeValue();
    setCompletedAt(now);
    setInitialCompletedAt(now);
    setConfirmDiscard(false);
    void loadEvidence(item);
  }, [item, loadEvidence]);
  const requestClose = () => {
    if (
      rootCause
      || correctiveAction
      || evidenceSelection
      || completedAt !== initialCompletedAt
    ) {
      setConfirmDiscard(true);
      return;
    }
    setConfirmDiscard(false);
    onClose();
  };
  const submit = async () => {
    const target = item;
    const completedAtDate = new Date(completedAt);
    const selected = evidenceOptions.find((option) => option.value === evidenceSelection);
    if (!canSubmitResolution({
      target, onResolve, pendingIssueId, rootCause, correctiveAction, selected, completedAtDate,
    }) || !target || !onResolve || !selected) return;
    setPendingIssueId(target.id);
    onNotify(undefined);
    try {
      const evidenceId = await captureOrSelectEvidenceId(target, selected, onCaptureEvidence);
      await onResolve(
        target,
        rootCause.trim(),
        correctiveAction.trim(),
        evidenceId,
        completedAtDate.toISOString(),
      );
      onNotify({
        severity: "success",
        message: `${target.issueNo} çözüm kaydı oluşturuldu.`,
      });
      onClose();
    } catch (error) {
      onNotify({
        severity: "error",
        message: error instanceof Error
          ? error.message
          : "Çözüm kaydedilemedi. Sorunu yenileyip yeniden deneyin.",
      });
    } finally {
      setPendingIssueId(undefined);
    }
  };
  return {
    completedAt,
    completedAtInvalid: !completedAt || new Date(completedAt) > new Date(),
    confirmDiscard,
    correctiveAction,
    evidenceOptions,
    evidenceSelection,
    evidenceState,
    loadEvidence,
    requestClose,
    rootCause,
    setCompletedAt,
    setConfirmDiscard,
    setCorrectiveAction,
    setEvidenceSelection,
    setRootCause,
    submit,
    uploadedEvidence,
    setUploadedEvidence,
  };
}

export function ResolutionDialog(props: ResolutionDialogProps) {
  const { item, pendingIssueId, onDownloadEvidence, onUploadEvidence, onNotify, onClose } = props;
  const form = useResolutionForm(props);
  return (
    <>
      <Dialog
        aria-describedby="resolution-dialog-description"
        fullWidth
        maxWidth="sm"
        onClose={form.requestClose}
        open={Boolean(item) && !form.confirmDiscard}
      >
        <DialogTitle>Çözüm kaydet</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 4, pt: 2 }}>
          <Typography color="text.secondary" id="resolution-dialog-description">
            {item?.issueNo} için kök neden ve düzeltici faaliyeti kaydedin.
          </Typography>
          <Typography color="text.secondary" variant="caption">
            Kaydedildiğinde sorun Çözüldü durumuna geçer ve değişiklik geçmişe yazılır.
          </Typography>
          <TextField
            label="Kök neden"
            maxRows={6}
            minRows={3}
            multiline
            onChange={(event) => form.setRootCause(event.target.value)}
            required
            slotProps={{ htmlInput: { maxLength: 4000 } }}
            value={form.rootCause}
          />
          <TextField
            label="Düzeltici faaliyet"
            maxRows={6}
            minRows={3}
            multiline
            onChange={(event) => form.setCorrectiveAction(event.target.value)}
            required
            slotProps={{ htmlInput: { maxLength: 4000 } }}
            value={form.correctiveAction}
          />
          <EvidenceUploadPanel
            item={item}
            onDownloadEvidence={onDownloadEvidence}
            onNotify={onNotify}
            onUploadEvidence={onUploadEvidence}
            onUploaded={(record) => {
              form.setUploadedEvidence((current) => [...current, record]);
              window.setTimeout(() => { if (item) void form.loadEvidence(item); }, 500);
            }}
            uploadedEvidence={form.uploadedEvidence}
          />
          <ResolutionEvidenceSection
            evidenceOptions={form.evidenceOptions}
            evidenceState={form.evidenceState}
            onSelect={form.setEvidenceSelection}
            onRetry={() => { if (item) void form.loadEvidence(item); }}
            selection={form.evidenceSelection}
          />
          <TextField
            error={form.completedAtInvalid}
            helperText={
              form.completedAtInvalid
                ? "Tamamlanma zamanı gelecekte olamaz."
                : "Yerel saat, kayıtta UTC olarak saklanır."
            }
            label="Tamamlanma zamanı"
            onChange={(event) => form.setCompletedAt(event.target.value)}
            required
            slotProps={{ htmlInput: { max: localDateTimeValue() } }}
            type="datetime-local"
            value={form.completedAt}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={form.requestClose}>Vazgeç</Button>
          <Button
            disabled={
              !form.rootCause.trim()
              || !form.correctiveAction.trim()
              || form.evidenceState !== "ready"
              || !form.evidenceSelection
              || form.completedAtInvalid
              || pendingIssueId === item?.id
            }
            onClick={() => void form.submit()}
            variant="contained"
          >
            {pendingIssueId === item?.id ? "Kaydediliyor" : "Kaydet"}
          </Button>
        </DialogActions>
      </Dialog>
      <DiscardConfirmDialog
        description="Kaydedilmemiş çözüm değişikliklerinden vazgeçilsin mi?"
        descriptionId="discard-resolution-description"
        onDiscard={() => {
          form.setConfirmDiscard(false);
          onClose();
        }}
        onStay={() => form.setConfirmDiscard(false)}
        open={form.confirmDiscard}
      />
    </>
  );
}
