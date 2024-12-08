from dataclasses import dataclass
from time import time
from typing import Optional, List
from src.constants import (
    DISCORD_CLIENT_ID,
    DEFAULT_BOT_NAME
)

SEPARATOR_TOKEN = "<|endoftext|>"


@dataclass(frozen=True)
class Message:
    user: str
    text: Optional[str] = None
    timestring: Optional[str] = None
    timestamp: Optional[int] = int(time())
    attachments: Optional[List[str]] = None

    def render(self, system=False, bot_name=DEFAULT_BOT_NAME):
        text = self.text if self.text else ""
        text = text.replace(f"<@{DISCORD_CLIENT_ID}>", f"@{bot_name}")
        obj = {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"{self.user} ({self.timestring if self.timestring else ''}) :  {text}"
                }
            ]
        }

        if self.attachments:
            obj["content"].extend([
                {
                    "type": "image_url",
                    "image_url": {
                        "url": img
                    }
                } for img in self.attachments
            ])

        if system:
            obj["role"] = "system"

        return obj


@dataclass
class Conversation:
    messages: List[Message]
    bot_name: str

    def prepend(self, message: Message):
        self.messages.insert(0, message)
        return self

    def render(self):
        return [m.render(bot_name=self.bot_name) for m in self.messages]


@dataclass(frozen=True)
class Prompt:
    header: Message
    convo: Conversation

    def render(self):
        return [
            self.header.render(system=True),
        ] + self.convo.render()
