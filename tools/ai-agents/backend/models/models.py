"""
数据模型定义 - AI 智能体独立版
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()


class RequirementsSession(db.Model):
    """需求分析会话模型"""

    __tablename__ = "requirements_sessions"

    id = db.Column(db.String(50), primary_key=True)  # UUID
    project_name = db.Column(db.String(255))
    session_status = db.Column(
        db.String(50), default="active"
    )  # active, paused, completed, archived
    current_stage = db.Column(
        db.String(50), default="initial"
    )  # initial, clarification, consensus, documentation
    user_context = db.Column(db.Text)  # JSON string - 用户上下文信息
    ai_context = db.Column(db.Text)  # JSON string - AI分析上下文
    consensus_content = db.Column(db.Text)  # JSON string - 达成共识的需求内容
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # 索引优化
    __table_args__ = (
        db.Index("idx_requirements_session_status", "session_status"),
        db.Index("idx_requirements_session_stage", "current_stage"),
        db.Index("idx_requirements_session_created", "created_at"),
        db.Index("idx_requirements_session_updated", "updated_at"),
    )

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "project_name": self.project_name,
            "session_status": self.session_status,
            "current_stage": self.current_stage,
            "user_context": (
                json.loads(self.user_context) if self.user_context else {}
            ),
            "ai_context": json.loads(self.ai_context) if self.ai_context else {},
            "consensus_content": (
                json.loads(self.consensus_content) if self.consensus_content else {}
            ),
            "created_at": (
                self.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                if self.created_at
                else None
            ),
            "updated_at": (
                self.updated_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                if self.updated_at
                else None
            ),
        }

    @property
    def assistant_type(self):
        """获取助手类型"""
        try:
            if not self.user_context:
                return "lisa"
            ctx = json.loads(self.user_context)
            return ctx.get("assistant_type", "lisa")
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to parse user_context: {e}")
            return "lisa"

    @classmethod
    def from_dict(cls, data):
        """从字典创建实例"""
        return cls(
            id=data.get("id"),
            project_name=data.get("project_name"),
            session_status=data.get("session_status", "active"),
            current_stage=data.get("current_stage", "initial"),
            user_context=json.dumps(data.get("user_context", {})),
            ai_context=json.dumps(data.get("ai_context", {})),
            consensus_content=json.dumps(data.get("consensus_content", {})),
        )

    def update_context(self, user_context=None, ai_context=None, consensus_content=None):
        """更新上下文信息"""
        if user_context is not None:
            self.user_context = json.dumps(user_context)
        if ai_context is not None:
            self.ai_context = json.dumps(ai_context)
        if consensus_content is not None:
            self.consensus_content = json.dumps(consensus_content)
        self.updated_at = datetime.utcnow()


class RequirementsMessage(db.Model):
    """需求分析消息模型"""

    __tablename__ = "requirements_messages"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.String(50),
        db.ForeignKey("requirements_sessions.id"),
        nullable=False,
        index=True,
    )
    message_type = db.Column(
        db.String(20), nullable=False
    )  # user, assistant, system
    content = db.Column(db.Text, nullable=False)
    message_metadata = db.Column(db.Text)  # JSON string - 额外的消息元数据
    attached_files = db.Column(db.Text)  # JSON string - 文件附件信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 索引优化
    __table_args__ = (
        db.Index("idx_requirements_message_session", "session_id", "created_at"),
        db.Index("idx_requirements_message_type", "session_id", "message_type"),
        db.Index("idx_requirements_message_created", "created_at"),
    )

    # 关系
    session = db.relationship(
        "RequirementsSession", backref=db.backref("messages", lazy=True)
    )

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "message_type": self.message_type,
            "content": self.content,
            "metadata": json.loads(self.message_metadata) if self.message_metadata else {},
            "attached_files": json.loads(self.attached_files) if self.attached_files else None,
            "created_at": (
                self.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                if self.created_at
                else None
            ),
        }

    @classmethod
    def from_dict(cls, data):
        """从字典创建实例"""
        return cls(
            session_id=data.get("session_id"),
            message_type=data.get("message_type"),
            content=data.get("content"),
            message_metadata=json.dumps(data.get("metadata", {})),
        )

    @classmethod
    def get_by_session(cls, session_id, limit=None, offset=None):
        """获取指定会话的消息"""
        query = (
            cls.query.filter_by(session_id=session_id)
            .order_by(cls.created_at.asc())
        )
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        return query.all()


class RequirementsAIConfig(db.Model):
    """需求分析AI配置模型 - 用户自定义版"""
    
    __tablename__ = "requirements_ai_configs"
    
    id = db.Column(db.Integer, primary_key=True)
    config_name = db.Column(db.String(255), nullable=False)  # 用户自定义配置名称
    api_key = db.Column(db.Text, nullable=False)
    base_url = db.Column(db.String(500), nullable=False)  # 改为必填
    model_name = db.Column(db.String(100), nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # 基础元数据
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "config_name": self.config_name,
            "api_key_masked": self._mask_api_key(self.api_key),  # 只返回脱敏的密钥
            "base_url": self.base_url,
            "model_name": self.model_name,
            "is_default": self.is_default,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def _mask_api_key(self, api_key):
        """脱敏显示API密钥"""
        if not api_key:
            return ""
        if len(api_key) <= 8:
            return "*" * len(api_key)
        return api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
    
    def get_config_for_ai_service(self):
        """获取AI服务所需的配置信息（包含完整API密钥）"""
        return {
            "api_key": self.api_key,
            "base_url": self.base_url,
            "model_name": self.model_name
        }
    
    @classmethod
    def get_default_config(cls):
        """获取默认配置"""
        return cls.query.filter_by(is_default=True, is_active=True).first()
    
    @classmethod
    def get_all_active_configs(cls):
        """获取所有启用的配置"""
        return cls.query.filter_by(is_active=True).order_by(cls.created_at.desc()).all()
