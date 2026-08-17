import { Tab, Tabs } from "@mui/material";
import { Link, useLocation } from "react-router-dom";

export const notificationTabs = [
  { label: "Gelen Kutusu", path: "/notifications" },
  { label: "Tercihler", path: "/notifications/preferences" },
  { label: "Kanallar", path: "/notifications/channels" },
  { label: "Teslimatlar", path: "/notifications/deliveries" },
];

export function NotificationTabs() {
  const location = useLocation();
  const currentTab = notificationTabs.findIndex((tab) => tab.path === location.pathname);

  return (
    <Tabs
      aria-label="Bildirim alt navigasyonu"
      allowScrollButtonsMobile
      scrollButtons="auto"
      sx={{ borderBottom: 1, borderColor: "divider" }}
      value={currentTab >= 0 ? currentTab : false}
      variant="scrollable"
    >
      {notificationTabs.map((tab) => (
        <Tab
          component={Link}
          key={tab.path}
          label={tab.label}
          sx={{ fontWeight: 600, textTransform: "none" }}
          to={tab.path}
        />
      ))}
    </Tabs>
  );
}
