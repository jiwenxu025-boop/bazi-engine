"""FastAPI 八字排盘 API

启动: python -m uvicorn bazi_engine.api:app --host 0.0.0.0 --port 8080
公网部署: BAZI_PUBLIC=true python -m uvicorn bazi_engine.api:app --host 0.0.0.0 --port 8080
  (公网模式禁用 calibrate，不加载校准数据)

端点:
  GET  /api/chart?name=...&gender=男&year=2007&month=8&day=26&hour=20
  POST /api/batch
  POST /api/chat  (AI 追问，SSE 流式)
  GET  /api/health
"""

import asyncio
import concurrent.futures
import hashlib
import hmac
import json
import os
import re
import threading
from contextlib import suppress
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ._version import __version__
from .chart import build_chart

_IS_PUBLIC = os.getenv("BAZI_PUBLIC", "").lower() in ("1", "true", "yes")
_AI_ENABLED = os.getenv("BAZI_AI_ENABLED", "").lower() in ("1", "true", "yes")
_ADMIN_KEY = os.getenv("BAZI_ADMIN_KEY", "")
_FAVORABLE_QUERY = Query(None)
_MAX_REQUEST_BODY_BYTES = int(os.getenv("BAZI_MAX_REQUEST_BODY_BYTES", "32768"))
_LARGE_REQUEST_BODY_LIMITS = {
    "/api/chat": int(os.getenv("BAZI_MAX_CHAT_BODY_BYTES", "131072")),
    "/api/date-pick": int(os.getenv("BAZI_MAX_DATE_PICK_BODY_BYTES", "262144")),
    "/api/personality/fusion/stream": int(os.getenv("BAZI_MAX_FUSION_BODY_BYTES", "131072")),
}
_MAX_AI_STREAMS = int(os.getenv("BAZI_MAX_AI_STREAMS", "3"))
_AI_STREAM_SLOTS = threading.BoundedSemaphore(max(1, _MAX_AI_STREAMS))
_CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("BAZI_CORS_ORIGINS", "").split(",")
    if origin.strip()
]


class ChartStreamRequest(BaseModel):
    name: str = Field(default="", max_length=40)
    gender: Literal["男", "女"]
    year: int = Field(ge=1900, le=2100)
    month: int = Field(ge=1, le=12)
    day: int = Field(ge=1, le=31)
    hour: int = Field(ge=0, le=23)
    liunian_from: int | None = Field(default=None, ge=1900, le=2100)
    liunian_to: int | None = Field(default=None, ge=1900, le=2100)
    favorable: list[str] | None = None
    life_stage: Literal["auto", "中学", "大学", "深造", "职场", "晚年"] = "auto"
    hour_confirmed: bool = False
    practical: bool = False


class ActivationCodeRequest(BaseModel):
    code: str = Field(min_length=1, max_length=80)


app = FastAPI(title="八字排盘引擎", version=__version__)

# 前端页面路径（支持环境变量覆盖，打包部署时可指定）
_frontend_env = os.getenv("FRONTEND_DIR", "")
_FRONTEND = Path(_frontend_env) if _frontend_env else Path(__file__).resolve().parent.parent.parent / "frontend"

# 静态文件挂载（末尾，让 API 路由优先匹配）

# 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def reject_large_request_bodies(request: Request, call_next):
    response = None
    if request.method in {"POST", "PUT", "PATCH"}:
        content_length = request.headers.get("content-length")
        max_bytes = _LARGE_REQUEST_BODY_LIMITS.get(request.url.path, _MAX_REQUEST_BODY_BYTES)
        if content_length and int(content_length) > max_bytes:
            response = JSONResponse({"error": "请求体过大"}, status_code=413)
    if response is None:
        response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), geolocation=(), microphone=()")
    return response


async def _release_stream_slot(stream):
    try:
        async for event in stream:
            yield event
    finally:
        _AI_STREAM_SLOTS.release()


def _limited_stream_response(stream):
    if not _AI_STREAM_SLOTS.acquire(blocking=False):
        return JSONResponse({"error": "服务繁忙，请稍后重试"}, status_code=429)
    return StreamingResponse(
        _release_stream_slot(stream),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _admin_authorized(request: Request) -> bool:
    if not _ADMIN_KEY:
        return False
    authorization = request.headers.get("authorization", "")
    bearer = authorization.removeprefix("Bearer ").strip()
    candidate = request.headers.get("x-admin-key", "").strip() or bearer
    return bool(candidate) and hmac.compare_digest(candidate, _ADMIN_KEY)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": __version__, "public": _IS_PUBLIC, "ai_enabled": _AI_ENABLED}


@app.get("/api/chart")
def chart_api(
    name: str = Query("", description="姓名（可选）"),
    gender: str = Query(..., pattern="^(男|女)$"),
    year: int = Query(..., ge=1900, le=2100),
    month: int = Query(..., ge=1, le=12),
    day: int = Query(..., ge=1, le=31),
    hour: int = Query(..., ge=0, le=23),
    liunian_from: int | None = Query(None),
    liunian_to: int | None = Query(None),
    favorable: list[str] | None = _FAVORABLE_QUERY,
    calibrate: bool = Query(False),
    life_stage: str = Query("auto", pattern="^(auto|中学|大学|深造|职场|晚年)$"),
    family_level: str = Query("", description="用户已知家境: 宽裕/普通/紧张"),
    father_job: str = Query("", description="父亲职业"),
    mother_job: str = Query("", description="母亲职业"),
    hour_confirmed: bool = Query(False, description="出生时辰是否经用户确认"),
    practical: bool = Query(False, description="实用模式：仅返回白话解读，不包含技术推导"),
):
    ln_range = None
    if liunian_from and liunian_to:
        ln_range = (liunian_from, liunian_to)

    fav_set = set(favorable) if favorable else None

    # 公网模式下强制禁用 calibrate
    use_calibrate = calibrate and not _IS_PUBLIC

    # 家境上下文
    family_context = None
    if family_level:
        family_context = {"economic_level": family_level}
        if father_job:
            family_context["father_occupation"] = father_job
        if mother_job:
            family_context["mother_occupation"] = mother_job

    chart = build_chart(
        name=name or "未知", gender=gender,
        year=year, month=month, day=day, hour=hour,
        liunian_range=ln_range,
        favorable=fav_set,
        calibrate=use_calibrate,
        life_stage_override=life_stage if life_stage != "auto" else "",
        family_context=family_context,
        hour_confirmed=hour_confirmed,
    )
    result = chart.to_dict()

    # 实用模式：剥离技术推导，只保留白话解读
    if practical:
        _strip_technical(result)

    return JSONResponse(content=result)


async def stream_chart(    name, gender, year, month, day, hour,
    ln_range, fav_set, life_stage, hour_confirmed, practical,
):
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def on_llm(year_val: int, signals: list[dict]):
        """LLM审查完成回调：推入队列"""
        loop.call_soon_threadsafe(
            queue.put_nowait,
            ("llm", {"phase": "llm_result", "year": year_val, "signals": signals})
        )

    def on_llm_tok(year_val: int, token: str):
        """LLM审查逐token回调"""
        loop.call_soon_threadsafe(
            queue.put_nowait,
            ("llm_token", {"phase": "llm_token", "year": year_val, "token": token})
        )

    # 用可变容器把 BaziChart 对象从线程传出来，供大运解读等后续步骤使用
    chart_obj_ref: list = []

    def run_build():
        """在线程中执行完整的 build_chart（含LLM审查）"""
        try:
            c = build_chart(
                name=name or "未知", gender=gender,
                year=year, month=month, day=day, hour=hour,
                liunian_range=ln_range,
                favorable=fav_set,
                calibrate=False,
                life_stage_override=life_stage if life_stage != "auto" else "",
                hour_confirmed=hour_confirmed,
                on_llm_result=on_llm,
                on_llm_token=on_llm_tok,
            )
            chart_obj_ref.append(c)
            result = c.to_dict()
            if practical:
                _strip_technical(result)
            loop.call_soon_threadsafe(queue.put_nowait, ("chart", result))
        except Exception as e:
            loop.call_soon_threadsafe(queue.put_nowait, ("error", str(e)))

    # 立即告知前端连接已建立
    yield f"data: {json.dumps({'phase': 'started', 'message': '规则引擎计算中...'})}\n\n"

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    loop.run_in_executor(executor, run_build)

    # 缓冲LLM结果和token（它们在build_chart线程中先到达，前端应先看到rules_done）
    buffered_llm: list[dict] = []
    buffered_llm_tokens: list[dict] = []
    # SSE 心跳：Railway 代理超时通常 30s，每 15s 发一次保活
    _HEARTBEAT_INTERVAL = 15.0

    while True:
        try:
            msg_type, msg_data = await asyncio.wait_for(queue.get(), timeout=_HEARTBEAT_INTERVAL)
        except TimeoutError:
            yield f"data: {json.dumps({'phase': 'heartbeat'})}\n\n"
            continue
        if msg_type == "error":
            yield f"data: {json.dumps({'phase': 'error', 'message': msg_data})}\n\n"
            yield "data: [DONE]\n\n"
            executor.shutdown(wait=False)
            return
        elif msg_type == "llm_token":
            buffered_llm_tokens.append(msg_data)
        elif msg_type == "llm":
            buffered_llm.append(msg_data)
        elif msg_type == "chart":
            chart_data = msg_data
            # 1. 先发规则引擎结果
            yield f"data: {json.dumps({'phase': 'rules_done', 'chart': chart_data})}\n\n"

            # 2. 刷新缓冲的LLM token（逐字推理过程）
            for tok_msg in buffered_llm_tokens:
                yield f"data: {json.dumps(tok_msg)}\n\n"

            # 3. 刷新缓冲的LLM结果
            for llm_msg in buffered_llm:
                yield f"data: {json.dumps(llm_msg)}\n\n"

            # 3. 性格融合报告逐token流式输出（仅融合实际启用时进入）
            chart = chart_obj_ref[0] if chart_obj_ref else None
            fusion_enabled = os.getenv("BAZI_FUSION_ENGINE", "0") == "1"
            fusion_key = os.getenv("DEEPSEEK_API_KEY", "")
            if fusion_enabled and fusion_key and chart_data.get("personality"):
                try:
                    from datetime import date

                    from .personality_fusion import build_fusion_data_package, generate_fusion_report
                    age_info = None
                    if chart and hasattr(chart, 'birth_dt'):
                        today = date.today()
                        age = today.year - chart.birth_dt.year
                        if (today.month, today.day) < (chart.birth_dt.month, chart.birth_dt.day):
                            age -= 1
                        dm = chart_data.get("day_master", {})
                        age_info = {
                            "年龄": age,
                            "日干": dm.get("stem", ""),
                            "五行": dm.get("wuxing", ""),
                            "阴阳": dm.get("yinyang", ""),
                        }
                    pkg = build_fusion_data_package(
                        chart_data.get("personality", {}),
                        chart_data.get("family"),
                        chart_data.get("life_stage", ""),
                        age_info=age_info,
                    )
                    fusion_queue: asyncio.Queue = asyncio.Queue()

                    def on_token(tok: str, _fusion_queue=fusion_queue):
                        loop.call_soon_threadsafe(
                            _fusion_queue.put_nowait, ("token", tok))

                    fusion_done_flag = {"done": False}
                    fusion_meta: dict = {}

                    def run_fusion(
                        _fusion_key=fusion_key,
                        _fusion_queue=fusion_queue,
                        _pkg=pkg,
                        _fusion_done_flag=fusion_done_flag,
                        _fusion_meta=fusion_meta,
                    ):
                        try:
                            if not _fusion_key:
                                loop.call_soon_threadsafe(_fusion_queue.put_nowait, ("fusion_error", "DEEPSEEK_API_KEY未设置"))
                                return
                            full = generate_fusion_report(
                                _pkg,
                                on_chunk=on_token,
                                result_metadata=_fusion_meta,
                            )
                            if full:
                                loop.call_soon_threadsafe(_fusion_queue.put_nowait, ("fusion_done", full))
                            else:
                                loop.call_soon_threadsafe(_fusion_queue.put_nowait, ("fusion_error", "API返回空"))
                            _fusion_done_flag["done"] = True
                        except Exception as e:
                            loop.call_soon_threadsafe(_fusion_queue.put_nowait, ("fusion_error", str(e)))
                            _fusion_done_flag["done"] = True

                    fusion_ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                    loop.run_in_executor(fusion_ex, run_fusion)

                    _fusion_start = loop.time()
                    while True:
                        try:
                            ft, fd = await asyncio.wait_for(fusion_queue.get(), timeout=15.0)
                        except TimeoutError:
                            if fusion_done_flag["done"]:
                                break  # thread finished but queue empty
                            elapsed = loop.time() - _fusion_start
                            if elapsed > 90:
                                yield f"data: {json.dumps({'phase': 'personality_error', 'message': f'融合超时({elapsed:.0f}s)'})}\n\n"
                                fusion_ex.shutdown(wait=False)
                                break
                            continue
                        if ft == "token":
                            yield f"data: {json.dumps({'phase': 'personality_token', 'token': fd})}\n\n"
                            _fusion_start = loop.time()  # reset timeout on activity
                        elif ft == "fusion_done":
                            if fd:
                                yield f"data: {json.dumps({'phase': 'personality_done', 'full': fd, 'meta': fusion_meta})}\n\n"
                            fusion_ex.shutdown(wait=False)
                            break
                        elif ft == "fusion_error":
                            yield f"data: {json.dumps({'phase': 'personality_error', 'message': fd})}\n\n"
                            fusion_ex.shutdown(wait=False)
                            break
                except Exception as e:
                    yield f"data: {json.dumps({'phase': 'personality_error', 'message': f'融合引擎异常: {e}'})}\n\n"
            else:
                detail = []
                if not fusion_enabled:
                    detail.append("BAZI_FUSION_ENGINE未设为1")
                if not fusion_key:
                    detail.append("DEEPSEEK_API_KEY未设置")
                if not chart_data.get("personality"):
                    detail.append("性格数据为空")
                yield f"data: {json.dumps({'phase': 'personality_error', 'message': '融合跳过: ' + '; '.join(detail)})}\n\n"

            # 4. 大运 LLM 解读（v0.14.0: 单次调用，非流式）
            try:
                from .llm_review import DEEPSEEK_KEY, LLM_REVIEW_ENABLED, enrich_dayun_interpretations
                loop_dy = asyncio.get_running_loop()
                dy_queue: asyncio.Queue = asyncio.Queue()
                dy_error: list = []

                def _run_dayun(
                    _chart=chart,
                    _loop_dy=loop_dy,
                    _dy_queue=dy_queue,
                    _dy_error=dy_error,
                ):
                    try:
                        result = enrich_dayun_interpretations(_chart) if _chart else []
                        _loop_dy.call_soon_threadsafe(_dy_queue.put_nowait, result)
                    except Exception as e:
                        _dy_error.append(str(e))
                        _loop_dy.call_soon_threadsafe(_dy_queue.put_nowait, [])

                executor.submit(_run_dayun)
                while True:
                    try:
                        dayun_result = await asyncio.wait_for(dy_queue.get(), timeout=_HEARTBEAT_INTERVAL)
                        break
                    except TimeoutError:
                        yield f"data: {json.dumps({'phase': 'heartbeat'})}\n\n"
                        continue
                if dayun_result:
                    chart.dayun_interpretations = dayun_result
                    yield f"data: {json.dumps({'phase': 'dayun_done', 'interpretations': dayun_result})}\n\n"
                elif dy_error:
                    yield f"data: {json.dumps({'phase': 'dayun_error', 'message': dy_error[0]})}\n\n"
                else:
                    detail = "dayun_modulations为空" if (chart and not getattr(chart, 'dayun_modulations', None)) else (
                        "LLM开关未启用" if not LLM_REVIEW_ENABLED else (
                        "DEEPSEEK_API_KEY未设置" if not DEEPSEEK_KEY else "LLM返回空"))
                    yield f"data: {json.dumps({'phase': 'dayun_error', 'message': detail})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'phase': 'dayun_error', 'message': f'大运解读模块异常: {e}'})}\n\n"

            # 5. 结束
            yield f"data: {json.dumps({'phase': 'done'})}\n\n"
            yield "data: [DONE]\n\n"
            executor.shutdown(wait=False)
            return

@app.get("/api/chart/stream")
async def chart_stream(
    name: str = Query("", description="姓名（可选）"),
    gender: str = Query(..., pattern="^(男|女)$"),
    year: int = Query(..., ge=1900, le=2100),
    month: int = Query(..., ge=1, le=12),
    day: int = Query(..., ge=1, le=31),
    hour: int = Query(..., ge=0, le=23),
    liunian_from: int | None = Query(None),
    liunian_to: int | None = Query(None),
    favorable: list[str] | None = _FAVORABLE_QUERY,
    life_stage: str = Query("auto", pattern="^(auto|中学|大学|深造|职场|晚年)$"),
    hour_confirmed: bool = Query(False),
    practical: bool = Query(False),
):
    """流式排盘 — SSE 端点。

    先返回规则引擎结果（代码层），再流式推送 LLM 推理结果。
    前端可立即渲染规则引擎部分，LLM 结果逐 token 追加。

    SSE 事件类型:
      data: {"phase":"rules_done","chart":{...}}   — 规则引擎完成，可立即渲染
      data: {"phase":"llm_result","year":2026,"signals":[...]}  — 某年LLM审查完成
      data: {"phase":"personality_token","token":"..."}  — 性格报告逐token
      data: {"phase":"personality_done","full":"..."}    — 性格报告完成
      data: {"phase":"done"}                             — 全流程结束
    """

    payload = ChartStreamRequest(
        name=name,
        gender=gender,
        year=year,
        month=month,
        day=day,
        hour=hour,
        liunian_from=liunian_from,
        liunian_to=liunian_to,
        favorable=favorable,
        life_stage=life_stage,
        hour_confirmed=hour_confirmed,
        practical=practical,
    )
    return _chart_stream_response(payload)


def _chart_stream_response(payload: ChartStreamRequest):
    ln_range = None
    if payload.liunian_from and payload.liunian_to:
        ln_range = (payload.liunian_from, payload.liunian_to)
    fav_set = set(payload.favorable) if payload.favorable else None
    return _limited_stream_response(stream_chart(
        payload.name,
        payload.gender,
        payload.year,
        payload.month,
        payload.day,
        payload.hour,
        ln_range,
        fav_set,
        payload.life_stage,
        payload.hour_confirmed,
        payload.practical,
    ))


@app.post("/api/chart/stream")
async def chart_stream_post(payload: ChartStreamRequest):
    """主页面使用的隐私优先流式排盘入口。"""
    return _chart_stream_response(payload)


def _strip_technical(data: dict):
    """去除经典引用，不暴露技术推导。保留其他所有内容。"""

    def _clean_text(text):
        # 去除古典引用标注，如"《渊海子平》：「...」"、《滴天髓》等
        text = re.sub(r'《[^》]+》[：:「][^」」]*[」」]', '', text)
        text = re.sub(r'《[^》]+》[^，。]*，', '', text)
        return text

    # 流年事件中去掉经典引用备注（保留空亡等重要提示）
    for scan in data.get("annual_scans", []):
        for ev in scan.get("events", []):
            notes = ev.get("notes", [])
            # 只去掉纯古籍引用（以[开头或全为古典句式），保留含有关键信息的备注
            ev["notes"] = [n for n in notes if not (
                n.startswith('[') or  # 纯标签 [正官年]
                (n.startswith('《') and n.count('：') >= 1)  # 纯古籍引用句
            )]
            # 清洗备注中的古籍出处标注，保留正文
            ev["notes"] = [re.sub(r'（《[^》]+》[^）]*）', '', n).strip() for n in ev["notes"]]
            ev.pop("calibration_refs", None)
            if ev.get("prediction"):
                ev["prediction"] = _clean_text(ev["prediction"])

    # 性格中去掉古典原文引用
    p = data.get("personality")
    if p:
        for k in list(p.keys()):
            if isinstance(p[k], str):
                p[k] = _clean_text(p[k])
        traits = p.get("traits", {})
        for k in list(traits.keys()):
            if isinstance(traits[k], str):
                traits[k] = _clean_text(traits[k])

    # 家境中去掉古典引用
    f = data.get("family")
    if f:
        for k in ("father", "mother", "parents_health"):
            if f.get(k):
                f[k] = _clean_text(f[k])


@app.post("/api/batch")
def batch_api(records: list[dict]):
    if _IS_PUBLIC:
        return JSONResponse({"error": "公网不提供批量排盘"}, status_code=403)
    if len(records) > 20:
        return JSONResponse({"error": "单次最多处理20条"}, status_code=422)
    results = []
    for r in records:
        try:
            ln_range = None
            if r.get("liunian_from") and r.get("liunian_to"):
                ln_range = (r["liunian_from"], r["liunian_to"])
            fav_set = set(r["favorable"]) if r.get("favorable") else None
            use_calibrate = r.get("calibrate", False) and not _IS_PUBLIC

            chart = build_chart(
                name=r.get("name", ""), gender=r.get("gender", "男"),
                year=r["year"], month=r["month"], day=r["day"], hour=r.get("hour", 12),
                liunian_range=ln_range,
                favorable=fav_set,
                calibrate=use_calibrate,
                life_stage_override=r.get("life_stage", ""),
            )
            results.append({"name": r.get("name"), "status": "ok", "data": chart.to_dict()})
        except Exception as e:
            results.append({"name": r.get("name"), "status": "error", "error": str(e)})
    return {"count": len(results), "results": results}


# ═══════════════════════════════════════════════════════════════
# 择日 API
# ═══════════════════════════════════════════════════════════════

@app.post("/api/date-pick")
def date_pick_api(body: dict):
    """择日：根据命盘筛选吉日/凶日（v2 完整评分）

    POST body:
        chart: { four_pillars: {...}, yongshen: { favorable_wuxing: [...], harmful_wuxing: [...] },
                 minggong: { branch: "申" }, ... }
        year: int  目标年份
        month: int 目标月份 (1-12)
    Returns:
        { year, month, results: [{date, score, good_tags, bad_tags, day_ganzhi}] }
    """
    import calendar
    from datetime import date

    from .date_picker import pick_good_dates
    from .enums import Dizhi, Tiangan

    chart_data = body.get("chart", {})
    yr = body.get("year")
    mo = body.get("month")

    if not yr or not mo:
        return JSONResponse({"error": "缺少 year 或 month 参数"}, status_code=400)

    pillars = chart_data.get("four_pillars", {})

    def _parse_dz(s: str):
        try:
            return Dizhi(s)
        except ValueError:
            return None

    def _parse_tg(s: str):
        try:
            return Tiangan(s)
        except ValueError:
            return None

    # 构建 MiniChart（复用原函数期望的属性）
    class _MiniPillar:
        def __init__(self, stem, branch):
            self.stem = stem
            self.branch = branch

    class _MiniChart:
        pass

    mini = _MiniChart()
    mini.year = _MiniPillar(
        _parse_tg(pillars.get("year", {}).get("stem", "")),
        _parse_dz(pillars.get("year", {}).get("branch", "")),
    )
    mini.month = _MiniPillar(
        _parse_tg(pillars.get("month", {}).get("stem", "")),
        _parse_dz(pillars.get("month", {}).get("branch", "")),
    )
    mini.day = _MiniPillar(
        _parse_tg(pillars.get("day", {}).get("stem", "")),
        _parse_dz(pillars.get("day", {}).get("branch", "")),
    )
    mini.hour = _MiniPillar(
        _parse_tg(pillars.get("hour", {}).get("stem", "")),
        _parse_dz(pillars.get("hour", {}).get("branch", "")),
    )

    # 命宫/身宫/胎元
    for attr, key in [("minggong_branch", "minggong"), ("shengong_branch", "shengong"), ("taiyuan_branch", "taiyuan")]:
        branch_str = chart_data.get(key, {}).get("branch", "")
        dz = _parse_dz(branch_str) if branch_str else None
        setattr(mini, attr, dz)

    if not mini.day.branch:
        return JSONResponse({"error": "缺少日柱地支"}, status_code=400)

    # 用神数据
    yongshen = chart_data.get("yongshen")

    _, last_day = calendar.monthrange(yr, mo)
    start = date(yr, mo, 1)
    end = date(yr, mo, last_day)

    results = pick_good_dates(mini, start, end, yongshen_data=yongshen)

    return {
        "year": yr,
        "month": mo,
        "results": results,
    }


# ═══════════════════════════════════════════════════════════════
# AI 追问 Chat 端点
# ═══════════════════════════════════════════════════════════════

@app.post("/api/chat")
async def chat_api(request: Request):
    """AI 八字追问 — SSE 流式返回"""
    if not _AI_ENABLED:
        return JSONResponse({"error": "AI 功能未启用"}, status_code=503)
    from .chat import (
        FREE_DAILY_LIMIT,
        build_messages,
        call_deepseek_stream,
        check_free_quota,
        consume_code,
        consume_free_quota,
        filter_sensitive,
        validate_code,
    )

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "请求格式错误"}, status_code=400)
    user_question = (body.get("question") or "").strip()
    chart_data = body.get("chart_data") or {}
    activation_code = (body.get("activation_code") or "").strip().upper()
    history = body.get("history") or []
    client_ip = request.client.host if request.client else "unknown"

    # 1. 敏感词检测
    passed, reject_msg = filter_sensitive(user_question)
    if not passed:
        async def reject_gen():
            yield f"data: {json.dumps({'token': reject_msg})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(reject_gen(), media_type="text/event-stream")

    # 2. 权限检查
    if activation_code:
        valid, _remaining, msg = validate_code(activation_code)
        if not valid:
            async def invalid_gen():
                yield f"data: {json.dumps({'token': msg})}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(invalid_gen(), media_type="text/event-stream")
    else:
        can_use, _remaining = check_free_quota(client_ip)
        if not can_use:
            async def quota_gen():
                yield f"data: {json.dumps({'token': f'今日免费追问次数（{FREE_DAILY_LIMIT}次）已用完。点击"解锁追问"获取激活码。'})}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(quota_gen(), media_type="text/event-stream")

    # 3. 构建 messages
    messages = build_messages(chart_data, user_question, history)

    # 4. 流式响应（扣费在首个token到达后执行，避免错误响应也扣费）
    async def stream_chat():
        consumed = False
        async for chunk in call_deepseek_stream(messages):
            if not consumed and chunk.startswith('data: {"token"'):
                consumed = True
                if activation_code:
                    consume_code(activation_code)
                else:
                    consume_free_quota(client_ip)
            yield chunk

    return _limited_stream_response(stream_chat())


@app.post("/api/personality/fusion/stream")
async def fusion_stream(request: Request):
    """LLM 融合引擎 — SSE 流式端点。

    POST body:  PersonalityResult + FamilyResult 的 JSON（来自 /api/chart）
    返回:     SSE text/event-stream，每行 data: {token} 或 data: [DONE]
    失败:     返回 {"error": "..."} 并结束流

    前端用法:
        const es = new EventSource('/api/personality/fusion/stream');
        // POST 不支持 EventSource，需用 fetch + ReadableStream 手动解析
        const resp = await fetch('/api/personality/fusion/stream', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({personality: chartData.personality, family: chartData.family})
        });
        const reader = resp.body.getReader();
        // ... 逐行解析 SSE
    """
    from .personality_fusion import build_fusion_data_package, generate_fusion_report

    if os.getenv("BAZI_FUSION_ENGINE", "0") != "1" or not os.getenv("DEEPSEEK_API_KEY", ""):
        async def err_gen():
            yield f"data: {json.dumps({'error': 'LLM 融合引擎未启用（设置 BAZI_FUSION_ENGINE=1 并配置 DEEPSEEK_API_KEY）'})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(err_gen(), media_type="text/event-stream")

    try:
        body = await request.json()
    except Exception:
        async def err_gen():
            yield f"data: {json.dumps({'error': '请求体必须是有效的 JSON'})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(err_gen(), media_type="text/event-stream")

    personality_data = body.get("personality", {})
    family_data = body.get("family")
    life_stage = body.get("life_stage", "")
    age_info = body.get("age_info", {})

    if not personality_data:
        async def err_gen():
            yield f"data: {json.dumps({'error': '缺少 personality 数据'})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(err_gen(), media_type="text/event-stream")

    data_package = build_fusion_data_package(personality_data, family_data, life_stage, age_info)

    # SSE 生成器 — 用 asyncio.Queue 桥接同步 LLM 流，实现真正的逐 token 推送
    import asyncio
    import concurrent.futures

    async def stream_fusion():
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_event_loop()
        fusion_meta: dict = {}

        def on_token(token: str):
            """LLM 每吐一个 token，立刻推入 queue"""
            loop.call_soon_threadsafe(queue.put_nowait, ("token", token))

        def run_llm():
            """在线程中跑同步流式 LLM 调用"""
            try:
                full = generate_fusion_report(
                    data_package,
                    on_chunk=on_token,
                    result_metadata=fusion_meta,
                )
                loop.call_soon_threadsafe(queue.put_nowait, ("done", full))
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, ("error", str(e)))

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        loop.run_in_executor(executor, run_llm)

        while True:
            msg_type, msg_data = await queue.get()
            if msg_type == "token":
                yield f"data: {json.dumps({'token': msg_data})}\n\n"
            elif msg_type == "done":
                if msg_data:
                    yield f"data: {json.dumps({'done': True, 'length': len(msg_data), 'full': msg_data, 'meta': fusion_meta})}\n\n"
                else:
                    yield f"data: {json.dumps({'error': 'LLM 调用失败，请稍后重试'})}\n\n"
                yield "data: [DONE]\n\n"
                executor.shutdown(wait=False)
                return
            elif msg_type == "error":
                yield f"data: {json.dumps({'error': msg_data})}\n\n"
                yield "data: [DONE]\n\n"
                executor.shutdown(wait=False)
                return

    return _limited_stream_response(stream_fusion())


@app.get("/api/chat/quota")
async def chat_quota(request: Request):
    """查询免费追问次数。激活码额度改由 POST 请求体查询。"""
    from .chat import check_free_quota
    client_ip = request.client.host if request.client else "unknown"
    _can_use, remaining = check_free_quota(client_ip)
    return {"has_code": False, "remaining": remaining}


@app.post("/api/chat/quota")
async def chat_code_quota(payload: ActivationCodeRequest):
    """查询激活码额度，避免把凭证放进 URL 和访问日志。"""
    from .chat import validate_code
    valid, remaining, _ = validate_code(payload.code.strip().upper())
    return {"has_code": True, "remaining": remaining if valid else 0}


# ═══════════════════════════════════════════════════════════════
# 管理端点
# ═══════════════════════════════════════════════════════════════

@app.get("/api/admin/codes")
def admin_codes(request: Request):
    """查看所有激活码状态"""
    if not _admin_authorized(request):
        return JSONResponse({"error": "无权访问"}, status_code=403)
    from .chat import _load_codes
    codes = _load_codes()
    items = []
    total_remaining = 0
    for code, info in sorted(codes.items(), key=lambda x: x[1].get("剩余", 0)):
        r = info.get("剩余", 0)
        total_remaining += r
        items.append({
            "code": code,
            "remaining": r,
            "note": info.get("备注", ""),
        })
    return {
        "total_codes": len(codes),
        "total_remaining": total_remaining,
        "codes": items,
    }


@app.get("/api/admin/feedback")
def admin_feedback(request: Request, days: int = Query(7, description="查看最近N天的反馈")):
    """查看用户反馈差异记录"""
    if not _admin_authorized(request):
        return JSONResponse({"error": "无权访问"}, status_code=403)

    # 日期筛选
    from datetime import datetime as dt
    from datetime import timedelta
    cutoff = dt.now() - timedelta(days=days) if days > 0 else dt(2000, 1, 1)

    records = []
    for f in sorted(_FEEDBACK_DIR.glob("feedback_*.jsonl"), reverse=True):
        # 从文件名提取日期：feedback_2026-05-26.jsonl → 2026-05-26
        try:
            file_date_str = f.stem.replace("feedback_", "")
            file_date = dt.strptime(file_date_str, "%Y-%m-%d")
            if file_date < cutoff:
                continue  # 超出天数范围，跳过
        except ValueError:
            pass  # 文件名格式不对，仍然读取

        if len(records) >= 1000:
            break
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                with suppress(Exception):
                    records.append(json.loads(line.strip()))

    # 统计
    total = len(records)
    discrepancies = sum(1 for r in records if r.get("discrepancy"))
    engine_levels = {}
    for r in records:
        lv = r.get("engine_level", "未知")
        engine_levels[lv] = engine_levels.get(lv, 0) + 1
    user_levels = {}
    for r in records:
        lv = r.get("user_level", "未知")
        user_levels[lv] = user_levels.get(lv, 0) + 1

    return {
        "total_records": total,
        "discrepancy_count": discrepancies,
        "discrepancy_rate": f"{discrepancies/total*100:.1f}%" if total > 0 else "0%",
        "engine_distribution": engine_levels,
        "user_distribution": user_levels,
        "recent": records[:50],
    }


@app.get("/api/admin")
def admin_page():
    """兼容旧入口，管理数据仅由静态页面通过请求头获取。"""
    return HTMLResponse(
        '<!doctype html><meta http-equiv="refresh" content="0; url=/admin.html">',
        headers={"Cache-Control": "no-store"},
    )


# ═══════════════════════════════════════════════════════════════
# 用户反馈 → 差异记录持久化
# ═══════════════════════════════════════════════════════════════

_FEEDBACK_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "feedback"
_FEEDBACK_LOCK = threading.Lock()


@app.post("/api/personality/fusion/feedback")
async def fusion_feedback_api(request: Request):
    """保存融合报告命中度反馈，不持久化出生资料或报告正文。"""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "请求格式错误"}, status_code=400)

    rating = body.get("rating", "")
    section = body.get("inaccurate_section", "")
    report_text = body.get("report_text", "")
    generation = body.get("generation", {})
    valid_ratings = {"very", "partial", "low"}
    valid_sections = {"", "core", "moments", "analysis", "misunderstood"}
    if rating not in valid_ratings:
        return JSONResponse({"saved": False, "error": "无效 rating"}, status_code=400)
    if section not in valid_sections:
        return JSONResponse({"saved": False, "error": "无效 inaccurate_section"}, status_code=400)
    if not isinstance(report_text, str) or not report_text.strip():
        return JSONResponse({"saved": False, "error": "缺少 report_text"}, status_code=400)

    from ._deepseek_config import DEEPSEEK_MODEL
    from .personality_fusion import FUSION_PROMPT_VERSION

    report_text = report_text[:20000]
    default_temperature = float(os.getenv("BAZI_FUSION_TEMPERATURE", "0.3"))
    try:
        temperature = float(generation.get("temperature", default_temperature))
    except (TypeError, ValueError):
        temperature = default_temperature
    if not 0 <= temperature <= 2:
        temperature = default_temperature

    record = {
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "rating": rating,
        "inaccurate_section": section,
        "report_hash": hashlib.sha256(report_text.encode("utf-8")).hexdigest(),
        "report_length": len(report_text),
        "prompt_version": str(generation.get("prompt_version") or FUSION_PROMPT_VERSION)[:80],
        "model": str(generation.get("model") or DEEPSEEK_MODEL)[:80],
        "temperature": temperature,
        "repaired": bool(generation.get("repaired", False)),
    }
    date_str = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
    feedback_file = _FEEDBACK_DIR / f"fusion_feedback_{date_str}.jsonl"

    with _FEEDBACK_LOCK:
        _FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
        with open(feedback_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return JSONResponse({"saved": True, "message": "反馈已记录"})


@app.get("/api/admin/fusion-feedback")
def admin_fusion_feedback(
    request: Request,
    days: int = Query(7, ge=0, le=365, description="查看最近N天的融合报告反馈"),
):
    """汇总融合报告命中度反馈，不返回报告正文或报告哈希。"""
    if not _admin_authorized(request):
        return JSONResponse({"error": "无权访问"}, status_code=403)

    from datetime import datetime as dt
    from datetime import timedelta

    cutoff = dt.now() - timedelta(days=days) if days > 0 else dt(2000, 1, 1)
    records: list[dict] = []
    for feedback_file in sorted(_FEEDBACK_DIR.glob("fusion_feedback_*.jsonl"), reverse=True):
        try:
            file_date = dt.strptime(feedback_file.stem.replace("fusion_feedback_", ""), "%Y-%m-%d")
            if file_date < cutoff:
                continue
        except ValueError:
            pass
        with open(feedback_file, encoding="utf-8") as fh:
            for line in fh:
                with suppress(Exception):
                    records.append(json.loads(line.strip()))
        if len(records) >= 1000:
            break

    rating_distribution: dict[str, int] = {}
    section_distribution: dict[str, int] = {}
    prompt_versions: dict[str, int] = {}
    model_distribution: dict[str, int] = {}
    temperature_distribution: dict[str, int] = {}
    repaired_count = 0
    for record in records:
        rating = record.get("rating", "unknown")
        section = record.get("inaccurate_section", "") or "未选择"
        version = record.get("prompt_version", "unknown")
        model = str(record.get("model") or "unknown")
        try:
            temperature = f"{float(record.get('temperature')):g}"
        except (TypeError, ValueError):
            temperature = "unknown"
        rating_distribution[rating] = rating_distribution.get(rating, 0) + 1
        section_distribution[section] = section_distribution.get(section, 0) + 1
        prompt_versions[version] = prompt_versions.get(version, 0) + 1
        model_distribution[model] = model_distribution.get(model, 0) + 1
        temperature_distribution[temperature] = temperature_distribution.get(temperature, 0) + 1
        repaired_count += int(bool(record.get("repaired")))

    total = len(records)
    recent = [
        {key: value for key, value in record.items() if key != "report_hash"}
        for record in records[:50]
    ]
    return {
        "total_records": total,
        "rating_distribution": rating_distribution,
        "section_distribution": section_distribution,
        "prompt_versions": prompt_versions,
        "model_distribution": model_distribution,
        "temperature_distribution": temperature_distribution,
        "repaired_count": repaired_count,
        "repaired_rate": f"{repaired_count / total * 100:.1f}%" if total else "0%",
        "recent": recent,
    }


@app.post("/api/feedback")
async def feedback_api(request: Request):
    """用户提交家境真实情况，引擎自动比对并保存差异记录。

    请求体: { "chart_data": {...}, "family_level": "普通", "father_job": "工人" }
    返回: { "saved": true, "discrepancy": "引擎推断宽裕, 用户反馈普通" | null }
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "请求格式错误"}, status_code=400)

    family_level = body.get("family_level", "")
    engine_level = body.get("engine_level", "")

    if not family_level:
        return JSONResponse({"saved": False, "error": "缺少 family_level"}, status_code=400)

    # 兼容旧客户端，但不持久化旧请求中可能携带的命盘或身份字段。
    if not engine_level:
        chart_data = body.get("chart_data", {})
        family_section = chart_data.get("family") or chart_data.get("family_result", {})
        if family_section:
            engine_level = family_section.get("level", "")

    # 比对
    discrepancy = None
    if engine_level and engine_level != family_level:
        discrepancy = f"引擎推断: {engine_level}, 用户反馈: {family_level}"

    # 保存到持久化文件
    record = {
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "engine_level": engine_level,
        "user_level": family_level,
        "discrepancy": discrepancy is not None,
    }
    if discrepancy:
        record["discrepancy_detail"] = discrepancy

    # 按日期分文件，避免单文件过大
    date_str = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
    feedback_file = _FEEDBACK_DIR / f"feedback_{date_str}.jsonl"

    _FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    with open(feedback_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return JSONResponse({
        "saved": True,
        "discrepancy": discrepancy,
        "message": "反馈已记录" if not discrepancy else "差异已记录，将用于改进引擎",
    })

@app.get("/privacy")
def privacy_page():
    fp = _FRONTEND / "privacy.html"
    if fp.exists():
        return HTMLResponse(fp.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>页面未找到</h1>", status_code=404)


@app.get("/terms")
def terms_page():
    fp = _FRONTEND / "terms.html"
    if fp.exists():
        return HTMLResponse(fp.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>页面未找到</h1>", status_code=404)


# 静态文件挂载（末尾，不影响 API 路由优先级）
if _FRONTEND.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND), html=True), name="static")
