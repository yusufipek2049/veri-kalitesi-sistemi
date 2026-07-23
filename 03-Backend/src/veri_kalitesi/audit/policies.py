"""Uygulama audit olaylari icin merkezi redaksiyon allowlist'i."""

from veri_kalitesi.audit.models import AuditRedactionPolicy


def build_default_redaction_policy() -> AuditRedactionPolicy:
    return AuditRedactionPolicy(
        version="AUDIT_REDACTION_V3",
        allowed_fields_by_action={
            "LDAP_AUTHENTICATION": frozenset(
                {
                    "mapping_policy_version",
                    "mapped_role_count",
                    "mapped_source_count",
                    "mapped_dataset_count",
                    "can_view_enterprise",
                    "throttle_policy_version",
                    "throttle_key_policy_version",
                    "failure_count",
                    "blocked",
                    "blocked_scope_count",
                    "reason_code",
                }
            ),
            "IDENTITY_SESSION": frozenset(
                {
                    "session_policy_version",
                    "status",
                    "reason_code",
                }
            ),
            "DASHBOARD_SCOPE_AUTHORIZATION": frozenset(
                {
                    "policy_version",
                    "permitted_source_count",
                    "can_view_enterprise",
                    "reason_code",
                }
            ),
            "AUDIT_RECORDS_VIEW_AUTHORIZATION": frozenset(
                {
                    "policy_version",
                    "reason_code",
                }
            ),
            "AUDIT_RECORDS_VIEWED": frozenset(
                {
                    "policy_version",
                    "query_reason_code",
                    "filter_count",
                    "page_size",
                    "returned_count",
                    "integrity_valid",
                }
            ),
            "REPORT_PREVIEW_AUTHORIZATION": frozenset(
                {
                    "policy_version",
                    "reason_code",
                }
            ),
            "REPORT_PREVIEW_VIEWED": frozenset(
                {
                    "policy_version",
                    "report_type",
                    "query_reason_code",
                    "requested_source_count",
                    "returned_source_count",
                    "calculated_source_count",
                    "window_days",
                    "masking_mode",
                }
            ),
            "INCIDENT_RESPONSE_AUTHORIZATION": frozenset(
                {
                    "policy_version",
                    "reason_code",
                }
            ),
            "SECURITY_INCIDENT_RECORDED": frozenset(
                {
                    "policy_version",
                    "source",
                    "severity",
                    "event_code",
                    "scope_type",
                    "status",
                }
            ),
            "PERSONAL_DATA_BREACH_SUSPICION_RECORDED": frozenset(
                {
                    "policy_version",
                    "origin",
                    "data_category_count",
                    "assessment_status",
                    "evaluation_deadline_at",
                    "processor_notification_evidence_present",
                    "containment_action_code",
                }
            ),
            "PERSONAL_DATA_BREACH_DECISION_RECORDED": frozenset(
                {
                    "policy_version",
                    "decision",
                    "decision_reason_code",
                    "deadline_status",
                    "evidence_present",
                    "external_notification_dispatched",
                }
            ),
            "PERSONAL_DATA_BREACH_TIMELINE_VIEWED": frozenset(
                {
                    "policy_version",
                    "query_reason_code",
                    "assessment_status",
                    "deadline_status",
                    "timeline_event_count",
                    "data_category_count",
                    "processor_notification_evidence_present",
                    "external_notification_dispatched",
                }
            ),
            "DATA_SOURCE_CREATED": frozenset({"source_type", "status"}),
            "DATA_SOURCE_CONNECTION_TESTED": frozenset({"succeeded", "duration_ms", "error_class"}),
            "DATA_SOURCE_CONNECTION_REVISION_CREATED": frozenset(
                {"base_revision", "candidate_revision", "policy_version", "status"}
            ),
            "DATA_SOURCE_CONNECTION_REVISION_TESTED": frozenset(
                {
                    "candidate_revision",
                    "revision_status",
                    "source_status",
                    "succeeded",
                    "duration_ms",
                    "error_class",
                    "invalidated_activation_count",
                }
            ),
            "DATA_SOURCE_ACTIVATION_REQUESTED": frozenset(
                {
                    "activation_request_id",
                    "data_source_revision",
                    "policy_version",
                    "status",
                    "target_at",
                    "expires_at",
                    "business_calendar_version",
                }
            ),
            "DATA_SOURCE_ACTIVATION_DECIDED": frozenset(
                {
                    "activation_request_id",
                    "data_source_revision",
                    "policy_version",
                    "status",
                    "source_status",
                }
            ),
            "DATA_SOURCE_ACTIVATION_WITHDRAWN": frozenset(
                {
                    "activation_request_id",
                    "data_source_revision",
                    "policy_version",
                    "status",
                    "source_status",
                }
            ),
            "DATA_SOURCE_ACTIVATION_EXPIRED": frozenset(
                {
                    "activation_request_id",
                    "data_source_revision",
                    "policy_version",
                    "business_calendar_version",
                    "status",
                    "source_status",
                }
            ),
            "DATA_SOURCE_DEACTIVATED": frozenset(
                {"data_source_revision", "policy_version", "status"}
            ),
            "DATA_SOURCE_METADATA_DISCOVERED": frozenset(
                {
                    "succeeded",
                    "duration_ms",
                    "scanned_object_count",
                    "error_class",
                    "added_count",
                    "changed_count",
                    "removed_count",
                    "requires_rule_review",
                }
            ),
            "DATASET_PROFILE_CREATED": frozenset(
                {
                    "profile_id",
                    "method",
                    "sample_ratio",
                    "status",
                    "duration_ms",
                    "error_class",
                    "record_count",
                    "sampled_count",
                }
            ),
            "DATA_PROCESSING_INVENTORY_RECORDED": frozenset(
                {
                    "inventory_version",
                    "classification",
                    "cross_border_transfer",
                    "access_role_count",
                    "recipient_group_count",
                }
            ),
            "QUALITY_RULE_CREATED": frozenset(
                {"rule_version_id", "version_no", "rule_type", "status"}
            ),
            "QUALITY_RULE_VERSION_CREATED": frozenset({"rule_version_id", "version_no"}),
            "QUALITY_RULE_TESTED": frozenset(
                {
                    "rule_version_id",
                    "rule_test_result_id",
                    "status",
                    "record_limit",
                    "checked_count",
                    "passed_count",
                    "failed_count",
                    "error_class",
                    "official_score_included",
                }
            ),
            "QUALITY_RULE_ACTIVATED": frozenset({"rule_version_id", "status"}),
            "QUALITY_RULE_PASSIVATED": frozenset({"rule_version_id", "status"}),
            "QUALITY_RULE_APPROVAL_REQUESTED": frozenset(
                {
                    "rule_version_id",
                    "approval_request_id",
                    "policy_version",
                    "status",
                    "target_at",
                    "expires_at",
                    "business_calendar_version",
                }
            ),
            "QUALITY_RULE_APPROVAL_DECIDED": frozenset(
                {"rule_version_id", "approval_request_id", "policy_version", "status"}
            ),
            "QUALITY_RULE_APPROVAL_WITHDRAWN": frozenset(
                {"rule_version_id", "approval_request_id", "policy_version", "status"}
            ),
            "QUALITY_RULE_APPROVAL_EXPIRED": frozenset(
                {
                    "rule_version_id",
                    "approval_request_id",
                    "policy_version",
                    "business_calendar_version",
                    "status",
                }
            ),
            "SCHEDULE_CREATED": frozenset(
                {
                    "schedule_type",
                    "timezone",
                    "rule_version_count",
                    "next_run_count",
                    "next_run_at",
                }
            ),
            "SCORING_CONFIGURATION_ACTIVATED": frozenset(
                {
                    "version",
                    "threshold_version",
                    "critical_upper_exclusive",
                    "risky_upper_exclusive",
                    "acceptable_upper_exclusive",
                    "dimension_completeness_weight",
                    "dimension_accuracy_weight",
                    "dimension_validity_weight",
                    "dimension_consistency_weight",
                    "dimension_uniqueness_weight",
                    "dimension_timeliness_weight",
                    "dimension_integrity_weight",
                    "criticality_low_weight",
                    "criticality_medium_weight",
                    "criticality_high_weight",
                    "criticality_critical_weight",
                }
            ),
            "SCORING_CONFIGURATION_APPROVAL_REQUESTED": frozenset(
                {
                    "version",
                    "approval_id",
                    "policy_version",
                    "status",
                    "threshold_version",
                    "critical_upper_exclusive",
                    "risky_upper_exclusive",
                    "acceptable_upper_exclusive",
                    "dimension_completeness_weight",
                    "dimension_accuracy_weight",
                    "dimension_validity_weight",
                    "dimension_consistency_weight",
                    "dimension_uniqueness_weight",
                    "dimension_timeliness_weight",
                    "dimension_integrity_weight",
                    "criticality_low_weight",
                    "criticality_medium_weight",
                    "criticality_high_weight",
                    "criticality_critical_weight",
                }
            ),
            "SCORING_CONFIGURATION_APPROVAL_DECIDED": frozenset(
                {
                    "version",
                    "approval_id",
                    "policy_version",
                    "status",
                    "threshold_version",
                    "critical_upper_exclusive",
                    "risky_upper_exclusive",
                    "acceptable_upper_exclusive",
                    "dimension_completeness_weight",
                    "dimension_accuracy_weight",
                    "dimension_validity_weight",
                    "dimension_consistency_weight",
                    "dimension_uniqueness_weight",
                    "dimension_timeliness_weight",
                    "dimension_integrity_weight",
                    "criticality_low_weight",
                    "criticality_medium_weight",
                    "criticality_high_weight",
                    "criticality_critical_weight",
                }
            ),
            "PARTIAL_SCORE_POLICY_APPROVAL_REQUESTED": frozenset(
                {
                    "dataset_id",
                    "policy_version",
                    "approval_policy_version",
                    "status",
                    "allow_official_partial_score",
                    "minimum_coverage_ratio",
                    "required_critical_rule_count",
                    "required_partition_count",
                    "maximum_missing_record_ratio",
                    "maximum_technical_error_ratio",
                    "minimum_successful_rule_ratio",
                    "effective_from",
                }
            ),
            "PARTIAL_SCORE_POLICY_APPROVAL_DECIDED": frozenset(
                {
                    "dataset_id",
                    "policy_version",
                    "approval_policy_version",
                    "status",
                    "allow_official_partial_score",
                    "minimum_coverage_ratio",
                    "required_critical_rule_count",
                    "required_partition_count",
                    "maximum_missing_record_ratio",
                    "maximum_technical_error_ratio",
                    "minimum_successful_rule_ratio",
                    "effective_from",
                }
            ),
            "PARTIAL_SCORE_POLICY_APPROVAL_WITHDRAWN": frozenset(
                {
                    "dataset_id",
                    "policy_version",
                    "approval_policy_version",
                    "status",
                    "allow_official_partial_score",
                    "minimum_coverage_ratio",
                    "required_critical_rule_count",
                    "required_partition_count",
                    "maximum_missing_record_ratio",
                    "maximum_technical_error_ratio",
                    "minimum_successful_rule_ratio",
                    "effective_from",
                }
            ),
            "SYNTHETIC_GENERATION_RUN_REQUESTED": frozenset(
                {
                    "dataset_id",
                    "policy_version",
                    "scenario_version",
                    "schema_version",
                    "generator_version",
                    "configuration_version",
                    "requested_record_count",
                    "seed_present",
                    "status",
                    "synthetic_origin",
                    "access_policy_version",
                }
            ),
            "SYNTHETIC_GOLDEN_VALIDATION_RECORDED": frozenset(
                {
                    "dataset_id",
                    "generation_run_id",
                    "ground_truth_version",
                    "validation_class",
                    "validation_status",
                    "reason_codes",
                    "expected_subject_count",
                    "expected_observation_count",
                    "actual_subject_count",
                    "actual_observation_count",
                    "score_tolerance_applied",
                    "synthetic_origin",
                    "access_policy_version",
                }
            ),
            "SYNTHETIC_RUN_FINALIZED": frozenset(
                {
                    "dataset_id",
                    "generation_run_id",
                    "status",
                    "validation_status",
                    "subject_count",
                    "observation_count",
                    "payload_byte_count",
                    "output_digest_present",
                    "validation_reference_present",
                    "retention_policy_id",
                    "synthetic_origin",
                    "access_policy_version",
                }
            ),
        },
    )
