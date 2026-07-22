"""Sentetik veri servisleri için ortak güvenilir aktör denetimi."""

from datetime import datetime

from veri_kalitesi.identity import ActorContext, is_trusted_actor_context
from veri_kalitesi.synthetic_data.errors import (
    SyntheticDataAuthorizationError,
    SyntheticDataValidationError,
)
from veri_kalitesi.synthetic_data.models import SyntheticRunAccessPolicy


def validate_synthetic_access_policy(policy: SyntheticRunAccessPolicy) -> None:
    if not policy.version.strip() or not policy.actor_policy_version.strip():
        raise SyntheticDataValidationError("Synthetic access policy versions are required.")
    if not policy.requester_roles or any(not role.strip() for role in policy.requester_roles):
        raise SyntheticDataValidationError("Synthetic requester roles are required.")
    if not policy.allowed_actor_types:
        raise SyntheticDataValidationError("Synthetic actor types are required.")


def authorize_synthetic_actor(
    context: ActorContext | None,
    *,
    dataset_id: str,
    at: datetime,
    access_policy: SyntheticRunAccessPolicy,
    operation: str,
) -> ActorContext:
    if not is_trusted_actor_context(context):
        raise SyntheticDataAuthorizationError("Trusted actor context is required.")
    assert context is not None
    if context.issued_at > at or context.expires_at <= at:
        raise SyntheticDataAuthorizationError("Actor context is not currently valid.")
    if context.policy_version != access_policy.actor_policy_version:
        raise SyntheticDataAuthorizationError("Actor context policy version is not accepted.")
    if context.actor_type not in access_policy.allowed_actor_types:
        raise SyntheticDataAuthorizationError(
            f"Actor type is not allowed for synthetic {operation}."
        )
    if context.privileged:
        raise SyntheticDataAuthorizationError(
            f"Privileged context is not allowed for synthetic {operation}."
        )
    if context.roles.isdisjoint(access_policy.requester_roles):
        raise SyntheticDataAuthorizationError(
            "Actor does not have the required synthetic data role."
        )
    if not context.can_view_enterprise and dataset_id not in context.permitted_dataset_ids:
        raise SyntheticDataAuthorizationError("Actor does not have the required dataset scope.")
    return context
