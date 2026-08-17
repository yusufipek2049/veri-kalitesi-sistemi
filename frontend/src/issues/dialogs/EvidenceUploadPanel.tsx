import { useEffect, useState } from "react";
import {
  Box,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  TextField,
  Typography,
} from "@mui/material";
import type { IssueActionFeedback } from "../labels";
import type { IssueEvidenceRecord, IssueListItem } from "../model";

export function EvidenceUploadPanel({
  item,
  uploadedEvidence,
  onUploadEvidence,
  onDownloadEvidence,
  onUploaded,
  onNotify,
}: {
  item?: IssueListItem;
  uploadedEvidence: IssueEvidenceRecord[];
  onUploadEvidence?: (
    item: IssueListItem, file: File, label: string, classification: string,
    onProgress: (percentage: number) => void,
  ) => Promise<IssueEvidenceRecord>;
  onDownloadEvidence?: (item: IssueListItem, evidenceId: string) => Promise<void>;
  onUploaded: (record: IssueEvidenceRecord) => void;
  onNotify: (feedback: IssueActionFeedback | undefined) => void;
}) {
  const [uploadFile, setUploadFile] = useState<File>();
  const [uploadLabel, setUploadLabel] = useState("");
  const [uploadClassification, setUploadClassification] = useState("INTERNAL");
  const [uploadProgress, setUploadProgress] = useState<number>();
  useEffect(() => {
    if (!item) return;
    setUploadFile(undefined);
    setUploadLabel("");
    setUploadProgress(undefined);
  }, [item]);
  const submit = async () => {
    if (!item || !uploadFile || !uploadLabel.trim() || !onUploadEvidence) return;
    setUploadProgress(1);
    try {
      const record = await onUploadEvidence(
        item, uploadFile, uploadLabel.trim(), uploadClassification, setUploadProgress,
      );
      setUploadProgress(100);
      setUploadFile(undefined);
      setUploadLabel("");
      onUploaded(record);
    } catch (error) {
      setUploadProgress(undefined);
      onNotify({ severity: "error", message: error instanceof Error
        ? error.message : "Kanıt dosyası yüklenemedi." });
    }
  };

  return (
    <Paper
      aria-label="Kanıt dosyası yükleme alanı"
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        event.preventDefault();
        const selected = event.dataTransfer.files[0];
        if (selected) setUploadFile(selected);
      }}
      sx={{ border: "1px dashed", borderColor: "divider", display: "grid", gap: 2, p: 3 }}
      variant="outlined"
    >
      <Typography sx={{ fontWeight: 600 }}>Kanıt yükle</Typography>
      <Typography color="text.secondary" variant="caption">
        PNG, JPEG, PDF, TXT veya LOG · En fazla 20 MB. Ham müşteri verisi yüklemeyin.
      </Typography>
      <Button component="label" variant="outlined">
        Dosya seç
        <input
          accept=".png,.jpg,.jpeg,.pdf,.txt,.log,image/png,image/jpeg,application/pdf,text/plain"
          hidden
          onChange={(event) => setUploadFile(event.target.files?.[0])}
          type="file"
        />
      </Button>
      {uploadFile ? <Typography variant="body2">{uploadFile.name}</Typography> : null}
      <TextField
        label="Kanıt başlığı"
        onChange={(event) => setUploadLabel(event.target.value)}
        slotProps={{ htmlInput: { maxLength: 200 } }}
        value={uploadLabel}
      />
      <FormControl>
        <InputLabel id="evidence-classification-label">Sınıflandırma</InputLabel>
        <Select
          label="Sınıflandırma"
          labelId="evidence-classification-label"
          onChange={(event) => setUploadClassification(event.target.value)}
          value={uploadClassification}
        >
          <MenuItem value="INTERNAL">Kurum içi</MenuItem>
          <MenuItem value="CONFIDENTIAL">Gizli</MenuItem>
          <MenuItem value="RESTRICTED">Kısıtlı</MenuItem>
        </Select>
      </FormControl>
      <Button
        disabled={!uploadFile || !uploadLabel.trim() || uploadProgress === 1}
        onClick={() => void submit()}
        variant="contained"
      >
        {uploadProgress !== undefined && uploadProgress < 100
          ? `Yükleniyor %${uploadProgress}` : "Kanıtı yükle"}
      </Button>
      <Box aria-live="polite">
        {uploadProgress === 100 ? "Yükleme tamamlandı, güvenlik taraması sürüyor." : null}
      </Box>
      {uploadedEvidence.map((record) => (
        <Box key={record.evidenceId} sx={{ alignItems: "center", display: "flex", gap: 1 }}>
          <Typography sx={{ flex: 1 }} variant="body2">
            {record.originalFilename ?? record.label} · {record.scanStatus ?? "PENDING_SCAN"}
          </Typography>
          {record.scanStatus === "AVAILABLE" && onDownloadEvidence && item ? (
            <Button onClick={() => void onDownloadEvidence(item, record.evidenceId)}>
              İndir
            </Button>
          ) : null}
        </Box>
      ))}
    </Paper>
  );
}
