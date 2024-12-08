import os
from typing import List
from src.constants import (
  MAX_MESSAGE_HISTORY,
  MAX_MESSAGE_TIME_DELTA
)
import openai
import json
import numpy as np
from numpy.linalg import norm
import re
from time import time,sleep
from uuid import uuid4
from datetime import datetime
from src.base import Message, Prompt, Conversation



notes_history = []


def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()


def save_file(filepath, content):
    with open(filepath, 'w', encoding='utf-8') as outfile:
        outfile.write(content)


def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return json.load(infile)


def save_json(filepath, payload):
    with open(filepath, 'w', encoding='utf-8') as outfile:
        json.dump(payload, outfile, ensure_ascii=False, sort_keys=True, indent=2)


def timestamp_to_datetime(unix_time):
    return datetime.fromtimestamp(unix_time).strftime("%A, %B %d, %Y at %I:%M%p %Z")


def gpt3_embedding(message, engine='text-embedding-ada-002'):
    content = message.content
    response = openai.Embedding.create(input=content,engine=engine)
    vector = response['data'][0]['embedding']  # this is a normal list
    return vector

def gpt3_response_embedding(response_data, engine='text-embedding-ada-002'):
    content = response_data.reply_text
    response = openai.Embedding.create(input=content,engine=engine)
    vector = response['data'][0]['embedding']  # this is a normal list
    return vector

def gpt3_memory_embedding(content, engine='text-embedding-ada-002'):
    content = content.encode(encoding='ASCII',errors='ignore').decode()
    response = openai.Embedding.create(input=content,engine=engine)
    vector = response['data'][0]['embedding']  # this is a normal list
    return vector


def similarity(v1, v2):
    # based upon https://stackoverflow.com/questions/18424228/cosine-similarity-between-2-number-lists
    return np.dot(v1, v2)/(norm(v1)*norm(v2))  # return cosine similarity


def fetch_memories(vector, logs, count):
    scores = list()
    for i in logs:
        if vector == i['vector']:
            # skip this one because it is the same message
            continue
        score = similarity(i['vector'], vector)
        i['score'] = score
        scores.append(i)
    ordered = sorted(scores, key=lambda d: d['score'], reverse=True)
    try:
        ordered = ordered[0:count]
        return ordered
    except:
        return ordered

def add_notes(notes):
    global notes_history
    notes_history.append(notes)
    return notes


def load_convo() -> List[Message]:
    files = os.listdir('./src/chat_logs')
    files = [i for i in files if '.json' in i]  # filter out any non-JSON files
    files = sorted(files, reverse=True)
    result = list()
    for file in files[0:MAX_MESSAGE_HISTORY]:
        data = load_json('./src/chat_logs/%s' % file)
        msg = Message(user=data['speaker'], text=data['message'], timestring=data['timestring'], attachments=data.get('attachments'), timestamp=data['timestamp'])
        result.append(msg)
    # ordered = sorted(result, key=lambda d: d['timestring'], reverse=False)  # sort them all chronologically
    result = [m for m in result if m.text is not None]
    earliest_time = time() - MAX_MESSAGE_TIME_DELTA
    result = [m for m in result if m.timestamp > earliest_time]

    return result

def load_context():
    files = os.listdir('./src/chat_logs')
    files = [i for i in files if '.json' in i]  # filter out any non-JSON files
    result = list()
    for file in files:
        data = load_json('./src/chat_logs/%s' % file)
        result.append(data)
    ordered = sorted(result, key=lambda d: d['timestring'], reverse=False)  # sort them all chronologically
    return ordered[-2]

def load_memory():
    files = os.listdir('./src/notes')
    files = [i for i in files if '.json' in i]  # filter out any non-JSON files
    result = list()
    for file in files:
        data = load_json('./src/notes/%s' % file)
        result.append(data)
    return result
