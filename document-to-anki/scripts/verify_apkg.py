#!/usr/bin/env python3
"""对旧式 collection.anki2 APKG 做静态校验；不代表通过 Anki 实际导入/翻面测试。

用法：python scripts/verify_apkg.py "牌组.apkg"
退出码：0 静态检查通过；1 发现问题；2 无法检查或文件格式不受支持。
"""
import json
import re
import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path


def main(filename):
    path = Path(filename)
    problems, warnings = [], []
    if not path.exists():
        print('ERROR: 文件不存在:', path)
        return 2
    try:
        with zipfile.ZipFile(path) as archive:
            broken = archive.testzip()
            if broken:
                problems.append('ZIP CRC 校验失败：' + broken)
            names = set(archive.namelist())
            if 'collection.anki2' not in names:
                print('UNSUPPORTED: 该 APKG 未包含旧式 collection.anki2；请用对应 Anki 工具验证（不能视为失败）。')
                return 2
            if 'media' not in names:
                warnings.append('未见 media 索引（某些无媒体包可能仍可用）')
            if 'media' in names:
                try:
                    media = json.loads(archive.read('media').decode('utf-8'))
                    if not isinstance(media, dict):
                        problems.append('media 索引不是 JSON 对象')
                except Exception as exc:
                    problems.append('media 不是合法 JSON：' + str(exc))
            sql_bytes = archive.read('collection.anki2')
    except (OSError, zipfile.BadZipFile) as exc:
        print('ERROR: 无法打开 APKG：', exc)
        return 2

    with tempfile.TemporaryDirectory() as temp:
        dbfile = Path(temp) / 'collection.anki2'
        dbfile.write_bytes(sql_bytes)
        try:
            con = sqlite3.connect(dbfile)
            integrity = con.execute('PRAGMA integrity_check').fetchone()[0]
            if integrity != 'ok':
                problems.append('SQLite integrity_check 失败：' + integrity)
            col = con.execute('SELECT ver, models, decks, dconf FROM col LIMIT 1').fetchone()
            if not col:
                problems.append('缺少 col 配置信息')
                raise ValueError('缺少 col')
            ver, raw_models, raw_decks, raw_conf = col
            models, decks, dconf = json.loads(raw_models), json.loads(raw_decks), json.loads(raw_conf)
            if not all(isinstance(v, dict) for v in (models, decks, dconf)):
                problems.append('models/decks/dconf 有非对象 JSON')
                raise ValueError('配置结构异常')
            notes = con.execute('SELECT id, mid, flds FROM notes').fetchall()
            cards = con.execute('SELECT id, nid, did, ord FROM cards').fetchall()
            nids = {n[0] for n in notes}
            ds = set(decks)
            for card_id, note_id, deck_id, order in cards:
                if note_id not in nids:
                    problems.append(f'卡片 {card_id} 引用不存在的笔记 {note_id}')
                if str(deck_id) not in ds:
                    problems.append(f'卡片 {card_id} 引用不存在的牌组 {deck_id}')
            for note_id, model_id, fields in notes:
                model = models.get(str(model_id))
                if model is None:
                    problems.append(f'笔记 {note_id} 引用不存在的模型 {model_id}')
                    continue
                definitions = [item['name'] for item in model.get('flds', [])]
                values = fields.split('\x1f')
                if len(values) != len(definitions):
                    problems.append(f'笔记 {note_id} 字段数为 {len(values)}，模型预期 {len(definitions)}')
                if len(values) >= 2 and (not values[0].strip() or not values[1].strip()):
                    problems.append(f'笔记 {note_id} 的前两个字段中存在空值')
            for model_id, model in models.items():
                fields = {item['name'] for item in model.get('flds', [])}
                if not model.get('tmpls'):
                    problems.append(f'模型 {model_id} 没有卡片模板')
                for template in model.get('tmpls', []):
                    front, back = template.get('qfmt', ''), template.get('afmt', '')
                    if not front.strip() or not back.strip():
                        problems.append(f'模型 {model_id} 模板正面/背面存在空值')
                    for field in re.findall(r'\{\{(?:[^{}:]+:)?([^{}]+)\}\}', front + back):
                        if field not in fields and field not in {'FrontSide', 'Tags', 'Deck', 'Subdeck', 'Card', 'Type', 'CardFlag'}:
                            problems.append(f'模型 {model_id} 引用不存在的字段 {field}')
                    if 'Back' in fields and '{{Back}}' not in back:
                        problems.append(f'模型 {model_id} 的背面模板未引用 {{Back}}')
                    if 'Front' in fields and '{{Front}}' not in front:
                        warnings.append(f'模型 {model_id} 正面模板未直接引用 {{Front}}（可能使用了自定义逻辑）')
            for deck_id, deck in decks.items():
                if not isinstance(deck, dict):
                    problems.append(f'牌组 {deck_id} 不是 JSON 对象')
                    continue
                for key in ('id', 'name', 'mod', 'usn', 'desc', 'dyn', 'collapsed', 'conf'):
                    if key not in deck:
                        problems.append(f'牌组 {deck_id} 缺少基本配置字段 {key}')
                for key in ('newToday', 'revToday', 'lrnToday', 'timeToday'):
                    if key not in deck:
                        if ver == 11:
                            problems.append(f'旧式版本 11 的牌组 {deck_id} 缺少 {key}（可能导致导入失败）')
                        else:
                            warnings.append(f'牌组 {deck_id} 缺少 {key}，需核对版本兼容性')
                if str(deck.get('conf')) not in dconf:
                    warnings.append(f'牌组 {deck_id} 的 conf={deck.get("conf")} 未匹配到 dconf（动态牌组可能例外）')
            print(f'版本字段: {ver}  |  笔记: {len(notes)}  |  卡片: {len(cards)}  |  牌组定义: {len(decks)}  |  模型: {len(models)}')
            if not notes or not cards:
                problems.append('包中没有笔记或卡片')
            con.close()
        except (sqlite3.Error, ValueError, KeyError, TypeError) as exc:
            problems.append('解析数据库/JSON 失败：' + str(exc))

    for issue in sorted(set(warnings))[:30]:
        print('WARN:', issue)
    for issue in sorted(set(problems))[:30]:
        print('FAIL:', issue)
    if problems:
        print(f'结果：静态检查失败，共 {len(set(problems))} 项异常。')
        return 1
    print('结果：静态检查通过。注意：尚未证明 Anki 实际导入与翻面显示正常。')
    return 0


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
