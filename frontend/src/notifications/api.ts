import { developmentFetch } from "../development/fetch";
import type {
  ChannelsApiResponse,
  DeliveryDetailApiResponse,
  InboxApiResponse,
  NotificationChannel,
  NotificationDelivery,
  NotificationSubscription,
  SubscriptionsApiResponse,
  UnreadCountApiResponse,
} from "./model";
import {
  channelFromApi,
  deliveryFromApi,
  inboxFromApi,
  subscriptionFromApi,
} from "./model";

export interface InboxResult {
  deliveries: NotificationDelivery[];
  totalUnread: number;
  cursor: string | null;
  hasMore: boolean;
}

export async function fetchInbox(params?: {
  status?: string;
  eventType?: string;
  limit?: number;
  cursor?: string;
}): Promise<InboxResult> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.eventType) searchParams.set("event_type", params.eventType);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.cursor) searchParams.set("cursor", params.cursor);
  const qs = searchParams.toString();
  const url = `/api/v1/notifications/inbox${qs ? `?${qs}` : ""}`;
  const response = await developmentFetch(url);
  const json = (await response.json()) as InboxApiResponse;
  return inboxFromApi(json);
}

export async function fetchUnreadCount(): Promise<number> {
  const response = await developmentFetch("/api/v1/notifications/inbox/unread-count");
  const json = (await response.json()) as UnreadCountApiResponse;
  return json.unread_count;
}

export async function markDeliveryRead(deliveryId: string): Promise<NotificationDelivery> {
  const response = await developmentFetch(
    `/api/v1/notifications/deliveries/${encodeURIComponent(deliveryId)}/read`,
    { method: "POST" }
  );
  const json = (await response.json()) as DeliveryDetailApiResponse;
  return deliveryFromApi(json.delivery);
}

export async function fetchSubscriptions(params?: {
  eventType?: string;
}): Promise<NotificationSubscription[]> {
  const searchParams = new URLSearchParams();
  if (params?.eventType) searchParams.set("event_type", params.eventType);
  const qs = searchParams.toString();
  const url = `/api/v1/notifications/subscriptions${qs ? `?${qs}` : ""}`;
  const response = await developmentFetch(url);
  const json = (await response.json()) as SubscriptionsApiResponse;
  return json.items.map(subscriptionFromApi);
}

export async function fetchChannels(): Promise<NotificationChannel[]> {
  const response = await developmentFetch("/api/v1/notifications/channels");
  const json = (await response.json()) as ChannelsApiResponse;
  return json.items.map(channelFromApi);
}
