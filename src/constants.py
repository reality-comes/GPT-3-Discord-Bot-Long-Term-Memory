from dataclasses import dataclass
from dotenv import load_dotenv
import os
import dacite
import yaml
from typing import Dict, List

load_dotenv()

@dataclass(frozen=True)
class Presets:
    trump: str
    charlie: str

@dataclass(frozen=True)
class Config:
    name: str
    presets: Presets
    postInstructions: str


# load config.yaml
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
CONFIG: Config = dacite.from_dict(
    Config, yaml.safe_load(open(os.path.join(SCRIPT_DIR, "config.yaml"), "r"))
)

DEFAULT_BOT_NAME = CONFIG.name
BOT_POST_INSTRUCTIONS = CONFIG.postInstructions

DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
DISCORD_CLIENT_ID = os.environ["DISCORD_CLIENT_ID"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

ALLOWED_SERVER_IDS: List[int] = []
server_ids = os.environ["ALLOWED_SERVER_IDS"].split(",")
for s in server_ids:
    ALLOWED_SERVER_IDS.append(int(s))

# Send Messages, Send Messages in Threads, Manage Messages, Read Message History
BOT_INVITE_URL = f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&permissions=328565073920&scope=bot"

SECONDS_DELAY_RECEIVING_MSG = (
    3  # give a delay for the bot to respond so it can catch multiple messages
)
MAX_MESSAGE_HISTORY = 15
MAX_CHARS_PER_REPLY_MSG = (
    1500  # discord has a 2k limit, we just break message into 1.5k
)
# time in seconds - messages older than this will be ignored when processing
MAX_MESSAGE_TIME_DELTA = 60 * 60 * 3  # 3 hours

DB_FILE = os.path.join(SCRIPT_DIR, "..", "db.sqlite3")

# DEFAULTS
DEFAULT_MODEL = "gpt-4o"
DEFAULT_TEMPERATURE = 1.1
DEFAULT_FREQUENCY_PENALTY = 0.1
DEFAULT_PRESENCE_PENALTY = 0.1
BOT_DEFAULT_PROMPT = CONFIG.presets.trump

PROMPT_PRESET_KEYS = CONFIG.presets.__dict__.keys()