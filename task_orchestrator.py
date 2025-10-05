#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
import yaml

STEPS_FILE = "steps.yaml"
INDEX_FILE = ".step_index"

# Единое сообщение об ошибке для шагов (по контракту)
ERR_STEPS = "steps.yaml not found or invalid"

# ====== Утилиты ======

def try_load_steps():
    """
    Пытается загрузить и расплющить шаги из steps.yaml.
    Не бросает исключений. Возвращает (steps_list | None, error_message | None).
    """
    try:
        with open(STEPS_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict) or "stages" not in data or not isinstance(data["stages"], list):
            return None, ERR_STEPS
        flat = []
        for stage in data["stages"]:
            steps = stage.get("steps", [])
            if not isinstance(steps, list):
                return None, ERR_STEPS
            for s in steps:
                if s is None:
                    continue
                flat.append(str(s))
        return flat, None
    except FileNotFoundError:
        return None, ERR_STEPS
    except yaml.YAMLError:
        return None, ERR_STEPS
    except Exception:
        return None, ERR_STEPS

def load_index():
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            t = f.read().strip()
            i = int(t) if t else 0
            return i if i >= 0 else 0
    except Exception:
        return 0

def save_index(i):
    try:
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            f.write(str(i))
    except Exception:
        # не роняем процесс
        pass

def rpc_result(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}

def rpc_error(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}

# ====== Реализация наших «инструментов» ======

def tool_get_next_task():
    steps, err = try_load_steps()
    if err is not None:
        # Для tools/call вернём контент-текст с ошибкой, а прямой метод — JSON-RPC error
        return None, err
    idx = load_index()
    if idx < len(steps):
        return steps[idx], None
    return None, None  # task=None => шагов больше нет

def tool_mark_task_complete():
    steps, err = try_load_steps()
    if err is not None:
        return False, err
    idx = load_index()
    if idx < len(steps):
        save_index(idx + 1)
    return True, None

def tool_reset_tasks():
    """
    Теперь всегда сбрасывает указатель на начало.
    Возвращает (ok: bool, skipped: bool, err: str|None).
    skipped теперь всегда False, потому что сброс всегда выполняется.
    """
    steps, err = try_load_steps()
    if err is not None:
        return False, False, err
    save_index(0)
    return True, False, None

# ====== Диспетчер MCP ======

def handle(req):
    req_id = req.get("id")
    method = req.get("method")
    params = req.get("params") or {}

    # --- MCP base: initialize ---
    # Клиент шлёт первым делом initialize; отвечаем версией протокола и возможностями.
    # Протоколная дата-версия «2024-11-05» используется в примерах SDK и совместима с клиентами.
    # См. также концепт-спеки MCP (initialize/tools/list/tools/call).
    if method == "initialize":
        return rpc_result(req_id, {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "task_orchestrator", "version": "1.1.0"},
            "capabilities": {
                "tools": {}
            }
        })

    # --- MCP tools/list ---
    # Возвращаем список инструментов с inputSchema (JSON Schema объект).
    if method == "tools/list":
        return rpc_result(req_id, {
            "tools": [
                {
                    "name": "get_next_task",
                    "description": "Return the current step (one-line command) or null if finished.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                },
                {
                    "name": "mark_task_complete",
                    "description": "Advance the step pointer by one.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                },
                {
                    "name": "reset_tasks",
                    "description": "Reset step pointer to the beginning ONLY if the sequence is finished.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            ]
        })

    # --- MCP tools/call ---
    if method == "tools/call":
        name = params.get("name")
        # arguments = params.get("arguments") or {}  # сейчас без аргументов

        if name == "get_next_task":
            task, err = tool_get_next_task()
            if err:
                # В некоторых клиентах важно вернуть text-контент, иначе падают валидации.
                return rpc_result(req_id, {
                    "content": [{"type": "text", "text": ERR_STEPS}]
                })
            # task=None → всё завершено
            payload = "null" if task is None else task
            return rpc_result(req_id, {
                "content": [{"type": "text", "text": payload}]
            })

        if name == "mark_task_complete":
            ok, err = tool_mark_task_complete()
            if err:
                return rpc_result(req_id, {
                    "content": [{"type": "text", "text": ERR_STEPS}]
                })
            return rpc_result(req_id, {
                "content": [{"type": "text", "text": "ok"}]
            })

        if name == "reset_tasks":
            ok, skipped, err = tool_reset_tasks()
            if err:
                return rpc_result(req_id, {
                    "content": [{"type": "text", "text": ERR_STEPS}]
                })
            text = "ok" if ok else "skipped"
            return rpc_result(req_id, {
                "content": [{"type": "text", "text": text}]
            })

        return rpc_error(req_id, -32601, f"Tool not found: {name}")

    # --- Поддержка прямых методов для ручного теста (необязательно для MCP) ---
    if method == "get_next_task":
        task, err = tool_get_next_task()
        if err:
            return rpc_error(req_id, -32000, ERR_STEPS)
        return rpc_result(req_id, {"task": task})

    if method == "mark_task_complete":
        ok, err = tool_mark_task_complete()
        if err:
            return rpc_error(req_id, -32000, ERR_STEPS)
        return rpc_result(req_id, {"status": "ok"})

    if method == "reset_tasks":
        ok, skipped, err = tool_reset_tasks()
        if err:
            return rpc_error(req_id, -32000, ERR_STEPS)
        return rpc_result(req_id, {"status": "ok" if ok else "skipped"})

    # --- Неизвестный метод ---
    return rpc_error(req_id, -32601, f"Method not found: {method}")

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            print(json.dumps({"jsonrpc": "2.0", "id": None,
                              "error": {"code": -32700, "message": "Parse error"}}, ensure_ascii=False), flush=True)
            continue
        try:
            resp = handle(req)
        except Exception:
            resp = rpc_error(req.get("id"), -32000, "Internal error")
        print(json.dumps(resp, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    main()
