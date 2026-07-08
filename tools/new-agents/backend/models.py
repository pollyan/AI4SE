from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class LlmConfig(db.Model):
    __tablename__ = 'llm_config'

    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(64), unique=True, nullable=False)
    api_key = db.Column(db.Text, nullable=False)
    base_url = db.Column(db.Text, nullable=False)
    model = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'config_key': self.config_key,
            'base_url': self.base_url,
            'model': self.model,
            'description': self.description
            # Note: api_key is intentionally not returned for security
        }


class AgentRun(db.Model):
    __tablename__ = "agent_runs"

    id = db.Column(db.String(36), primary_key=True)
    workflow_id = db.Column(db.String(64), nullable=False, index=True)
    agent_id = db.Column(db.String(64), nullable=False, index=True)
    current_stage_id = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(32), nullable=False, default="active")
    model = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )

    messages = db.relationship(
        "AgentMessage",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="AgentMessage.sequence_index",
    )
    artifacts = db.relationship(
        "AgentArtifact",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="AgentArtifact.stage_id",
    )
    context_summaries = db.relationship(
        "AgentContextSummary",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by=(
            "AgentContextSummary.source_type,"
            "AgentContextSummary.source_stage_id,"
            "AgentContextSummary.summary_type"
        ),
    )
    turn_metrics = db.relationship(
        "AgentRunTurnMetric",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="AgentRunTurnMetric.created_at",
    )
    artifact_comments = db.relationship(
        "AgentArtifactComment",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="AgentArtifactComment.created_at_ms",
    )
    artifact_section_locks = db.relationship(
        "AgentArtifactSectionLock",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="AgentArtifactSectionLock.created_at_ms",
    )
    artifact_audit_events = db.relationship(
        "AgentArtifactAuditEvent",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by=(
            "AgentArtifactAuditEvent.created_at_ms,"
            "AgentArtifactAuditEvent.id"
        ),
    )
    story_handoff_packets = db.relationship(
        "AgentStoryHandoffPacket",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by=(
            "AgentStoryHandoffPacket.created_at_ms,"
            "AgentStoryHandoffPacket.id"
        ),
    )


class AgentMessage(db.Model):
    __tablename__ = "agent_messages"
    __table_args__ = (
        db.UniqueConstraint(
            "run_id",
            "sequence_index",
            name="uq_agent_messages_run_sequence",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(
        db.String(36),
        db.ForeignKey("agent_runs.id"),
        nullable=False,
        index=True,
    )
    role = db.Column(db.String(32), nullable=False)
    content = db.Column(db.Text, nullable=False)
    sequence_index = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    run = db.relationship("AgentRun", back_populates="messages")


class AgentArtifact(db.Model):
    __tablename__ = "agent_artifacts"
    __table_args__ = (
        db.UniqueConstraint(
            "run_id",
            "stage_id",
            name="uq_agent_artifacts_run_stage",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(
        db.String(36),
        db.ForeignKey("agent_runs.id"),
        nullable=False,
        index=True,
    )
    stage_id = db.Column(db.String(64), nullable=False)
    current_version_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )

    run = db.relationship("AgentRun", back_populates="artifacts")
    versions = db.relationship(
        "AgentArtifactVersion",
        back_populates="artifact",
        cascade="all, delete-orphan",
        order_by="AgentArtifactVersion.version_number",
    )


class AgentArtifactVersion(db.Model):
    __tablename__ = "agent_artifact_versions"
    __table_args__ = (
        db.UniqueConstraint(
            "artifact_id",
            "version_number",
            name="uq_agent_artifact_versions_artifact_version",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    artifact_id = db.Column(
        db.Integer,
        db.ForeignKey("agent_artifacts.id"),
        nullable=False,
        index=True,
    )
    version_number = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    artifact_data = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    artifact = db.relationship("AgentArtifact", back_populates="versions")


class AgentContextSummary(db.Model):
    __tablename__ = "agent_context_summaries"
    __table_args__ = (
        db.UniqueConstraint(
            "run_id",
            "source_type",
            "source_stage_id",
            "summary_type",
            name="uq_agent_context_summaries_source",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(
        db.String(36),
        db.ForeignKey("agent_runs.id"),
        nullable=False,
        index=True,
    )
    source_type = db.Column(db.String(32), nullable=False)
    source_stage_id = db.Column(db.String(64), nullable=False)
    summary_type = db.Column(db.String(64), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )

    run = db.relationship("AgentRun", back_populates="context_summaries")


class AgentRunTurnMetric(db.Model):
    __tablename__ = "agent_run_turn_metrics"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(
        db.String(36),
        db.ForeignKey("agent_runs.id"),
        nullable=False,
        index=True,
    )
    workflow_id = db.Column(db.String(64), nullable=False, index=True)
    stage_id = db.Column(db.String(64), nullable=False, index=True)
    model = db.Column(db.String(128), nullable=False)
    provider = db.Column(db.String(128), nullable=False, default="unknown", index=True)
    status = db.Column(db.String(32), nullable=False, index=True)
    error_code = db.Column(db.String(64))
    duration_ms = db.Column(db.Integer, nullable=False)
    input_chars = db.Column(db.Integer, nullable=False, default=0)
    output_chars = db.Column(db.Integer, nullable=False, default=0)
    estimated_tokens = db.Column(db.Integer, nullable=False, default=0)
    contract_retry_count = db.Column(db.Integer, nullable=False, default=0)
    diagnostic_phase = db.Column(db.String(64))
    diagnostic_field_path = db.Column(db.Text)
    diagnostic_validator = db.Column(db.String(128))
    diagnostic_public_reason = db.Column(db.Text)
    diagnostic_retryable = db.Column(db.Boolean)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    run = db.relationship("AgentRun", back_populates="turn_metrics")


class AgentRuntimeConfigIssue(db.Model):
    __tablename__ = "agent_runtime_config_issues"

    id = db.Column(db.Integer, primary_key=True)
    workflow_id = db.Column(db.String(64), nullable=False, index=True)
    stage_id = db.Column(db.String(64), nullable=False, index=True)
    error_code = db.Column(db.String(64), nullable=False, index=True)
    issue_scope = db.Column(db.String(64), nullable=False, index=True)
    route = db.Column(db.String(128), nullable=False)
    request_id = db.Column(db.String(64), nullable=False, index=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class AgentArtifactComment(db.Model):
    __tablename__ = "agent_artifact_comments"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(
        db.String(36),
        db.ForeignKey("agent_runs.id"),
        nullable=False,
        index=True,
    )
    client_id = db.Column(db.String(128), nullable=False)
    stage_id = db.Column(db.String(64), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    artifact_excerpt = db.Column(db.Text, nullable=False)
    anchor_text = db.Column(db.Text)
    created_at_ms = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(32), nullable=False, default="open")
    resolved_at_ms = db.Column(db.Integer)
    replies_json = db.Column(db.Text, nullable=False, default="[]")

    run = db.relationship("AgentRun", back_populates="artifact_comments")


class AgentArtifactSectionLock(db.Model):
    __tablename__ = "agent_artifact_section_locks"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(
        db.String(36),
        db.ForeignKey("agent_runs.id"),
        nullable=False,
        index=True,
    )
    client_id = db.Column(db.String(128), nullable=False)
    stage_id = db.Column(db.String(64), nullable=False, index=True)
    heading = db.Column(db.Text, nullable=False)
    section_anchor = db.Column(db.Text)
    content = db.Column(db.Text, nullable=False)
    created_at_ms = db.Column(db.Integer, nullable=False)

    run = db.relationship("AgentRun", back_populates="artifact_section_locks")


class AgentArtifactAuditEvent(db.Model):
    __tablename__ = "agent_artifact_audit_events"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(
        db.String(36),
        db.ForeignKey("agent_runs.id"),
        nullable=False,
        index=True,
    )
    stage_id = db.Column(db.String(64), nullable=False, index=True)
    event_type = db.Column(db.String(64), nullable=False, index=True)
    summary = db.Column(db.Text, nullable=False)
    created_at_ms = db.Column(db.Integer, nullable=False)

    run = db.relationship("AgentRun", back_populates="artifact_audit_events")


class AgentStoryHandoffPacket(db.Model):
    __tablename__ = "agent_story_handoff_packets"
    __table_args__ = (
        db.UniqueConstraint(
            "run_id",
            "source_stage_id",
            "source_artifact_version",
            "story_id",
            name="uq_agent_story_handoff_packets_source_story",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(
        db.String(36),
        db.ForeignKey("agent_runs.id"),
        nullable=False,
        index=True,
    )
    source_workflow_id = db.Column(db.String(64), nullable=False, index=True)
    source_stage_id = db.Column(db.String(64), nullable=False, index=True)
    source_artifact_version = db.Column(db.Integer, nullable=False)
    source_artifact_digest = db.Column(db.String(128), nullable=False)
    story_id = db.Column(db.String(64), nullable=False, index=True)
    packet_json = db.Column(db.JSON, nullable=False)
    created_at_ms = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    run = db.relationship("AgentRun", back_populates="story_handoff_packets")


class AgentTestAssetCollection(db.Model):
    __tablename__ = "agent_test_asset_collections"
    __table_args__ = (
        db.UniqueConstraint(
            "run_id",
            "source_stage_id",
            name="uq_agent_test_asset_collections_run_stage",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(
        db.String(36),
        db.ForeignKey("agent_runs.id"),
        nullable=False,
        index=True,
    )
    workflow_id = db.Column(db.String(64), nullable=False, index=True)
    source_stage_id = db.Column(db.String(64), nullable=False)
    source_artifact_version = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )

    run = db.relationship("AgentRun")
    test_cases = db.relationship(
        "AgentTestCaseAsset",
        back_populates="collection",
        cascade="all, delete-orphan",
        order_by="AgentTestCaseAsset.case_id",
    )
    test_points = db.relationship(
        "AgentTestPointAsset",
        back_populates="collection",
        cascade="all, delete-orphan",
        order_by="AgentTestPointAsset.test_point",
    )
    risk_matrix = db.relationship(
        "AgentRiskMatrixAsset",
        back_populates="collection",
        cascade="all, delete-orphan",
        order_by="AgentRiskMatrixAsset.risk",
    )
    issues = db.relationship(
        "AgentTestAssetIssue",
        back_populates="collection",
        cascade="all, delete-orphan",
        order_by="AgentTestAssetIssue.id",
    )
    intent_tester_mappings = db.relationship(
        "AgentTestAssetIntentTesterMapping",
        back_populates="collection",
        cascade="all, delete-orphan",
        order_by="AgentTestAssetIntentTesterMapping.source_case_id",
    )


class AgentTestCaseAsset(db.Model):
    __tablename__ = "agent_test_case_assets"
    __table_args__ = (
        db.UniqueConstraint(
            "collection_id",
            "case_id",
            name="uq_agent_test_case_assets_collection_case",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    collection_id = db.Column(
        db.Integer,
        db.ForeignKey("agent_test_asset_collections.id"),
        nullable=False,
        index=True,
    )
    case_id = db.Column(db.String(64), nullable=False)
    current_version_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )

    collection = db.relationship("AgentTestAssetCollection", back_populates="test_cases")
    versions = db.relationship(
        "AgentTestCaseVersion",
        back_populates="test_case",
        cascade="all, delete-orphan",
        order_by="AgentTestCaseVersion.version_number",
    )


class AgentTestCaseVersion(db.Model):
    __tablename__ = "agent_test_case_versions"
    __table_args__ = (
        db.UniqueConstraint(
            "test_case_id",
            "version_number",
            name="uq_agent_test_case_versions_case_version",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    test_case_id = db.Column(
        db.Integer,
        db.ForeignKey("agent_test_case_assets.id"),
        nullable=False,
        index=True,
    )
    version_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(16), nullable=False)
    dimension = db.Column(db.Text, nullable=False)
    test_point = db.Column(db.Text, nullable=False)
    risk = db.Column(db.Text, nullable=False)
    precondition = db.Column(db.Text, nullable=False)
    steps = db.Column(db.Text, nullable=False)
    test_data = db.Column(db.Text, nullable=False)
    expected_result = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    test_case = db.relationship("AgentTestCaseAsset", back_populates="versions")


class AgentTestPointAsset(db.Model):
    __tablename__ = "agent_test_point_assets"
    __table_args__ = (
        db.UniqueConstraint(
            "collection_id",
            "test_point",
            name="uq_agent_test_point_assets_collection_point",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    collection_id = db.Column(
        db.Integer,
        db.ForeignKey("agent_test_asset_collections.id"),
        nullable=False,
        index=True,
    )
    test_point = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(16), nullable=False)
    risk = db.Column(db.Text, nullable=False)
    test_cases_json = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(32), nullable=False)

    collection = db.relationship("AgentTestAssetCollection", back_populates="test_points")


class AgentRiskMatrixAsset(db.Model):
    __tablename__ = "agent_risk_matrix_assets"
    __table_args__ = (
        db.UniqueConstraint(
            "collection_id",
            "risk",
            name="uq_agent_risk_matrix_assets_collection_risk",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    collection_id = db.Column(
        db.Integer,
        db.ForeignKey("agent_test_asset_collections.id"),
        nullable=False,
        index=True,
    )
    risk = db.Column(db.Text, nullable=False)
    test_cases_json = db.Column(db.Text, nullable=False)
    test_points_json = db.Column(db.Text, nullable=False)
    priorities_json = db.Column(db.Text, nullable=False)
    dimensions_json = db.Column(db.Text, nullable=False)
    coverage_statuses_json = db.Column(db.Text, nullable=False)
    is_manual = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(32), nullable=False, default="open")
    owner = db.Column(db.Text, nullable=False, default="")
    note = db.Column(db.Text, nullable=False, default="")

    collection = db.relationship("AgentTestAssetCollection", back_populates="risk_matrix")


class AgentTestAssetIssue(db.Model):
    __tablename__ = "agent_test_asset_issues"

    id = db.Column(db.Integer, primary_key=True)
    collection_id = db.Column(
        db.Integer,
        db.ForeignKey("agent_test_asset_collections.id"),
        nullable=False,
        index=True,
    )
    issue_type = db.Column(db.String(64), nullable=False)
    case_id = db.Column(db.String(64))
    test_point = db.Column(db.Text)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(16), nullable=False, default="pending")

    collection = db.relationship("AgentTestAssetCollection", back_populates="issues")


class AgentTestAssetIntentTesterMapping(db.Model):
    __tablename__ = "agent_test_asset_intent_tester_mappings"
    __table_args__ = (
        db.UniqueConstraint(
            "collection_id",
            "source_case_id",
            name="uq_agent_test_asset_intent_tester_collection_case",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    collection_id = db.Column(
        db.Integer,
        db.ForeignKey("agent_test_asset_collections.id"),
        nullable=False,
        index=True,
    )
    source_case_id = db.Column(db.String(64), nullable=False)
    intent_tester_case_id = db.Column(db.Integer, nullable=False)
    intent_tester_case_name = db.Column(db.Text, nullable=False, default="")
    latest_execution_id = db.Column(db.String(128))
    latest_execution_status = db.Column(db.String(32))
    latest_execution_mode = db.Column(db.String(32))
    latest_execution_browser = db.Column(db.String(32))
    latest_execution_start_time = db.Column(db.Text)
    latest_execution_end_time = db.Column(db.Text)
    latest_execution_duration = db.Column(db.Float)
    latest_execution_error_message = db.Column(db.Text)
    latest_execution_result_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )

    collection = db.relationship(
        "AgentTestAssetCollection",
        back_populates="intent_tester_mappings",
    )
