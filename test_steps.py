#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import subprocess
import sys
import yaml


def call_step_orchestrator(method):
    """Отправляем JSON-RPC запрос инструменту и получаем ответ."""
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method
    }
    try:
        proc = subprocess.run(
            ["python3", "step_orchestrator.py"],
            input=json.dumps(req) + "\n",
            capture_output=True,
            text=True,
            timeout=5
        )
        if proc.returncode != 0:
            print(f"Ошибка выполнения {method}: {proc.stderr.strip()}")
            return None
        response = json.loads(proc.stdout.strip())
        return response
    except Exception as e:
        print(f"Ошибка при вызове метода {method}: {e}")
        return None


def test_steps():
    print("🔍 Проверка steps.yaml ...")
    with open("steps.yaml", "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    stages = data.get("stages", [])
    steps = [step for s in stages for step in s.get("steps", [])]
    assert len(steps) > 0, "steps.yaml не содержит шагов"
    print(f"✅ Найдено {len(steps)} шагов")

    first_step = steps[0]

    print("\n🧩 Тестирование step_orchestrator ...")
    for i, step in enumerate(steps):
        resp = call_step_orchestrator("get_next_step")
        assert resp and "result" in resp, f"❌ Нет ответа для get_next_step на шаге {i+1}"
        current = resp["result"]["step"]
        assert current == step, f"❌ Ожидалось '{step}', получено '{current}'"
        print(f"✓ Шаг {i+1}: {current}")
        call_step_orchestrator("mark_step_complete")

    # Проверка конца
    resp = call_step_orchestrator("get_next_step")
    assert resp["result"]["step"] is None, "❌ После последнего шага step должен быть null"
    print("\n🎉 Все шаги корректно прочитаны и завершены!")

    # 🔁 Проверка сброса
    print("\n🔁 Проверка reset_steps (сброс к началу)...")
    resp_reset = call_step_orchestrator("reset_steps")
    assert resp_reset and "result" in resp_reset, "❌ Нет ответа от reset_steps"
    status = resp_reset["result"].get("status")
    assert status == "ok", f"❌ Ожидалось 'ok' от reset_steps, получено '{status}'"
    print("✓ Сброс выполнен: ok")

    # Проверяем, что после сброса снова доступен первый шаг
    resp2 = call_step_orchestrator("get_next_step")
    assert resp2 and "result" in resp2, "❌ Нет ответа после reset_steps"
    current2 = resp2["result"]["step"]
    assert current2 == first_step, f"❌ После сброса ожидался первый шаг '{first_step}', получено '{current2}'"
    print(f"✅ После сброса первый шаг снова: {current2}")


if __name__ == "__main__":
    try:
        test_steps()
    except AssertionError as e:
        print(e)
        sys.exit(1)
