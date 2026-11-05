"""小型使用说明库：按匹配短语长度排序检索，无需向量服务。"""
import json
import re
from pathlib import Path

DOCUMENTS = json.loads(Path(__file__).with_name('knowledge.json').read_text(encoding='utf-8'))

def retrieve(message: str) -> dict | None:
    query = re.sub(r'[\W_]+', '', message).lower()
    query = query.replace('干嘛', '干什么').replace('做嘛', '做什么').replace('啥', '什么')
    matches = [(len(phrase), document) for document in DOCUMENTS for phrase in document['phrases']
               if (query == phrase if document.get('exact') else phrase in query)]
    return max(matches, key=lambda item:item[0])[1] if matches else None
