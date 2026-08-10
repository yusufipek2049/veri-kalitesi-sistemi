export type NotificationDeliveryStatus =
  | "PENDING"
  | "SENDING"
  | "DELIVERED"
  | "FAILED"
  | "UNDELIVERABLE"
  | "REROUTED"
  | "READ";

export type NotificationEventType =
  | "QUALITY_THRESHOLD"
  | "CRITICAL_RULE_FAILURE"
  | "TECHNICAL_ERROR"
  | "ISSUE_ASSIGNED";

export interface NotificationDelivery {
  deliveryId: string;
  eventId: string;
  recipientUserId: string;
  channelId: string;
  status: NotificationDeliveryStatus;
  attemptCount: number;
  createdAt: string;
  updatedAt: string;
  deliveredAt: string | null;
  readAt: string | null;
}

export interface NotificationSubscription {
  subscriptionId: string;
  eventType: NotificationEventType;
  channelId: string;
  status: "ACTIVE" | "INACTIVE";
  scopeType: string | null;
  scopeId: string | null;
}

export interface NotificationChannel {
  channelId: string;
  name: string;
  channelType: string;
  status: "ACTIVE" | "INACTIVE";
}

export interface InboxApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  total_unread: number;
  cursor: string | null;
  has_more: boolean;
  items: Array<{
    delivery_id: string;
    event_id: string;
    recipient_user_id: string;
    channel_id: string;
    status: NotificationDeliveryStatus;
    attempt_count: number;
    created_at: string;
    updated_at: string;
    delivered_at: string | null;
    read_at: string | null;
  }>;
}

export interface UnreadCountApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  unread_count: number;
}

export interface DeliveryDetailApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  delivery: {
    delivery_id: string;
    event_id: string;
    recipient_user_id: string;
    channel_id: string;
    status: NotificationDeliveryStatus;
    attempt_count: number;
    created_at: string;
    updated_at: string;
    delivered_at: string | null;
    read_at: string | null;
  };
}

export interface SubscriptionsApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  items: Array<{
    subscription_id: string;
    event_type: NotificationEventType;
    channel_id: string;
    status: string;
    scope_type: string | null;
    scope_id: string | null;
  }>;
}

export interface ChannelsApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  items: Array<{
    channel_id: string;
    name: string;
    channel_type: string;
    status: string;
  }>;
}

export function deliveryFromApi(raw: {
  delivery_id: string;
  event_id: string;
  recipient_user_id: string;
  channel_id: string;
  status: NotificationDeliveryStatus;
  attempt_count: number;
  created_at: string;
  updated_at: string;
  delivered_at: string | null;
  read_at: string | null;
}): NotificationDelivery {
  return {
    deliveryId: raw.delivery_id,
    eventId: raw.event_id,
    recipientUserId: raw.recipient_user_id,
    channelId: raw.channel_id,
    status: raw.status,
    attemptCount: raw.attempt_count,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
    deliveredAt: raw.delivered_at,
    readAt: raw.read_at,
  };
}

export function inboxFromApi(raw: InboxApiResponse): {
  deliveries: NotificationDelivery[];
  totalUnread: number;
  cursor: string | null;
  hasMore: boolean;
} {
  return {
    deliveries: raw.items.map(deliveryFromApi),
    totalUnread: raw.total_unread,
    cursor: raw.cursor,
    hasMore: raw.has_more,
  };
}

export function subscriptionFromApi(raw: {
  subscription_id: string;
  event_type: NotificationEventType;
  channel_id: string;
  status: string;
  scope_type: string | null;
  scope_id: string | null;
}): NotificationSubscription {
  return {
    subscriptionId: raw.subscription_id,
    eventType: raw.event_type,
    channelId: raw.channel_id,
    status: raw.status as "ACTIVE" | "INACTIVE",
    scopeType: raw.scope_type,
    scopeId: raw.scope_id,
  };
}

export function channelFromApi(raw: {
  channel_id: string;
  name: string;
  channel_type: string;
  status: string;
}): NotificationChannel {
  return {
    channelId: raw.channel_id,
    name: raw.name,
    channelType: raw.channel_type,
    status: raw.status as "ACTIVE" | "INACTIVE",
  };
}
