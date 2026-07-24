/** Geliştirme modu kullanıcı seçim ekranı. */

import { Box, Button, Card, CardContent, Typography, Chip, Stack, CircularProgress } from "@mui/material";
import { useDevelopmentUser } from "./UserContext";

const ROLE_COLORS: Record<string, "primary" | "success" | "warning" | "info" | "error" | "default"> = {
  DATA_VIEWER: "info",
  DATA_STEWARD: "primary",
  DATA_OWNER: "success",
  DATA_GOVERNANCE_SPECIALIST: "warning",
  DATA_ENGINEER: "secondary",
  AUDIT_VIEWER: "error",
};

function getRoleColor(role: string): "primary" | "success" | "warning" | "info" | "error" | "default" {
  return ROLE_COLORS[role] ?? "default";
}

export function DevelopmentLoginPage() {
  const { availableUsers, setCurrentUser, isLoading } = useDevelopmentUser();

  if (isLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box
      sx={(theme) => ({
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        bgcolor: theme.palette.background.default,
        p: 3,
      })}
    >
      <Typography variant="h4" sx={{ mb: 1, fontWeight: 700 }}>
        Veri Kalitesi Sistemi
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Geliştirme modu — kullanıcı seçin
      </Typography>

      <Stack spacing={2} sx={{ maxWidth: 500, width: "100%" }}>
        {availableUsers.map((user) => (
          <Card
            key={user.user_id}
            sx={{
              cursor: "pointer",
              transition: "box-shadow 0.2s",
              "&:hover": { boxShadow: 6 },
            }}
            onClick={() => setCurrentUser(user)}
          >
            <CardContent>
              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                {user.display_name}
              </Typography>
              <Stack direction="row" spacing={1} sx={{ mt: 1 }} flexWrap="wrap" useFlexGap>
                {user.roles.split(" / ").map((role) => (
                  <Chip
                    key={role}
                    label={role}
                    size="small"
                    color={getRoleColor(role)}
                    variant="outlined"
                  />
                ))}
              </Stack>
            </CardContent>
          </Card>
        ))}
      </Stack>

      <Typography variant="caption" color="text.disabled" sx={{ mt: 4 }}>
        Bu ekran yalnız geliştirme ortamında görünür. Gerçek IdP/SSO bağlantısı değildir.
      </Typography>
    </Box>
  );
}

export function DevelopmentUserSwitcher() {
  const { currentUser, clearCurrentUser } = useDevelopmentUser();

  if (!currentUser) return null;

  return (
    <Box
      sx={(theme) => ({
        position: "fixed",
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: theme.zIndex.snackbar,
        bgcolor: theme.palette.warning.light,
        color: theme.palette.warning.contrastText,
        px: 2,
        py: 0.5,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 2,
        fontSize: "0.75rem",
      })}
    >
      <span>Geliştirme: <strong>{currentUser.display_name}</strong></span>
      <Chip
        label="Kullanıcı değiştir"
        size="small"
        color="warning"
        onClick={clearCurrentUser}
        sx={{ cursor: "pointer", fontWeight: 600 }}
      />
    </Box>
  );
}