from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ChatMessage:
    """A traceable chat message with stable IDs and metadata."""

    role: str
    content: str
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp_utc: str = field(default_factory=_utc_now_iso)
    trace_id: Optional[str] = None
    parent_message_id: Optional[str] = None
    model: Optional[str] = None
    reasoning_level: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_openai_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ChatMessage":
        return ChatMessage(**data)


@dataclass
class ChatHistory:
    """Stores and persists chat messages while preserving lineage."""

    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    messages: List[ChatMessage] = field(default_factory=list)

    def add(
        self,
        role: str,
        content: str,
        trace_id: Optional[str] = None,
        parent_message_id: Optional[str] = None,
        model: Optional[str] = None,
        reasoning_level: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatMessage:
        message = ChatMessage(
            role=role,
            content=content,
            trace_id=trace_id,
            parent_message_id=parent_message_id,
            model=model,
            reasoning_level=reasoning_level,
            metadata=metadata or {},
        )
        self.messages.append(message)
        return message

    def to_provider_messages(self, include_system: bool = True) -> List[Dict[str, str]]:
        if include_system:
            return [m.to_openai_dict() for m in self.messages]
        return [m.to_openai_dict() for m in self.messages if m.role != "system"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "messages": [m.to_dict() for m in self.messages],
        }

    def save_json(self, path: str | Path) -> None:
        p = Path(path)
        p.write_text(json.dumps(self.to_dict(), ensure_ascii=True, indent=2), encoding="utf-8")

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ChatHistory":
        return ChatHistory(
            conversation_id=data["conversation_id"],
            messages=[ChatMessage.from_dict(m) for m in data.get("messages", [])],
        )

    @staticmethod
    def load_json(path: str | Path) -> "ChatHistory":
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        return ChatHistory.from_dict(data)
