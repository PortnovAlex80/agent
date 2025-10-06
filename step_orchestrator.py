#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
import yaml

STEPS_FILE = "steps.yaml"
INDEX_FILE = ".step_index"

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
        pass

def rpc_result(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}

def rpc_error(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}

# ====== Реализация инструментов ======

def tool_get_next_step():
    steps, err = try_load_steps()
    if err is not None:
        return None, err
    idx = load_index()
    if idx < len(steps):
        return steps[idx], None
    return None, None  # step=None => шагов больше нет

def tool_mark_step_complete():
    steps, err = try_load_steps()
    if err is not None:
        return False, err
    idx = load_index()
    if idx < len(steps):
        save_index(idx + 1)
    return True, None

def tool_reset_steps():
    """
    Всегда сбрасывает указатель на начало.
    Возвращает (ok: bool, err: str|None).
    """
    steps, err = try_load_steps()
    if err is not None:
        return False, err
    save_index(0)
    return True, None

# ====== Диспетчер MCP ======

def handle(req):
    req_id = req.get("id")
    method = req.get("method")
    params = req.get("params") or {}

    # initialize
    if method == "initialize":
        return rpc_result(req_id, {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "step_orchestrator", "version": "1.1.0"},
            "capabilities": {
                "tools": {}
            }
        })

    # tools/list
    if method == "tools/list":
        return rpc_result(req_id, {
            "tools": [
                {
                    "name": "get_next_step",
                    "description": "Return the current step (one-line command) or null if finished.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                },
                {
                    "name": "mark_step_complete",
                    "description": "Advance the step pointer by one.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                },
                {
                    "name": "reset_steps",
                    "description": "Reset step pointer to the beginning.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            ]
        })

    # tools/call
    if method == "tools/call":
        name = params.get("name")

        if name == "get_next_step":
            step, err = tool_get_next_step()
            if err:
                return rpc_result(req_id, {"content": [{"type": "text", "text": ERR_STEPS}]})
            payload = "null" if step is None else step
            return rpc_result(req_id, {"content": [{"type": "text", "text": payload}]})

        if name == "mark_step_complete":
            ok, err = tool_mark_step_complete()
            if err:
                return rpc_result(req_id, {"content": [{"type": "text", "text": ERR_STEPS}]})
            return rpc_result(req_id, {"content": [{"type": "text", "text": "ok"}]})

        if name == "reset_steps":
            ok, err = tool_reset_steps()
            if err:
                return rpc_result(req_id, {"content": [{"type": "text", "text": ERR_STEPS}]})
            return rpc_result(req_id, {"content": [{"type": "text", "text": "ok"}]})

        return rpc_error(req_id, -32601, f"Tool not found: {name}")

    # Прямые методы (удобно для локальных тестов)
    if method == "get_next_step":
        step, err = tool_get_next_step()
        if err:
            return rpc_error(req_id, -32000, ERR_STEPS)
        return rpc_result(req_id, {"step": step})

    if method == "mark_step_complete":
        ok, err = tool_mark_step_complete()
        if err:
            return rpc_error(req_id, -32000, ERR_STEPS)
        return rpc_result(req_id, {"status": "ok"})

    if method == "reset_steps":
        ok, err = tool_reset_steps()
        if err:
            return rpc_error(req_id, -32000, ERR_STEPS)
        return rpc_result(req_id, {"status": "ok"})

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
