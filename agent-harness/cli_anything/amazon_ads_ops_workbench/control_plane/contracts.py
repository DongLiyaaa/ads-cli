"""Typed, allowlisted adapters; no shell execution or process-global credentials."""

import json
import math
import re
from datetime import date
import click
from ..amazon_ads_ops_workbench_cli import cli
from ..core.runtime import OperationRuntime, operation_runtime
from ..core.amc import check_window as check_amc_window, resolve_query as resolve_amc_query
from .security import Problem

HIDDEN = {"marketplace", "dry_run", "confirm_submit"}
AMC_QUERY = "reports.create-amc-query"
EXCLUDED_GROUPS = {"auth", "profiles", "approvals"}
FILE_OPTIONS = {"input_file", "output_dir", "output_file"}


def registry():
    result = {}
    root = click.Context(cli)
    for name in cli.list_commands(root):
        if name in EXCLUDED_GROUPS or name == "capabilities":
            continue
        group = cli.get_command(root, name)
        children = (
            [(sub, group.get_command(root, sub)) for sub in group.list_commands(root)]
            if isinstance(group, click.Group)
            else [(None, group)]
        )
        for sub, command in children:
            if any(p.name in FILE_OPTIONS for p in command.params):
                continue
            if name == "reports" and not str(sub).startswith("create-"):
                continue
            operation = f"{name}.{sub}" if sub else name
            kind = (
                "report"
                if name == "reports"
                else "write"
                if any(p.name == "dry_run" for p in command.params)
                else "read"
            )
            properties, required = {}, []
            for p in command.params:
                if p.name in HIDDEN:
                    continue
                t = (
                    "boolean"
                    if p.is_flag
                    else "integer"
                    if isinstance(p.type, click.types.IntParamType)
                    else "number"
                    if isinstance(p.type, click.types.FloatParamType)
                    else "string"
                )
                item = {"type": t, "description": p.help or p.name}
                if isinstance(p.type, click.Choice):
                    item["enum"] = list(p.type.choices)
                if p.multiple:
                    item = {"type": "array", "items": item}
                default = p.get_default(click.Context(command))
                if default is not None:
                    try:
                        json.dumps(default, allow_nan=False)
                    except (TypeError, ValueError):
                        pass  # Click UNSET sentinels are not JSON schema defaults.
                    else:
                        item["default"] = default
                properties[p.name] = item
                if p.required:
                    required.append(p.name)
            result[operation] = {
                "operation": operation,
                "kind": kind,
                "description": command.help or operation,
                "inputSchema": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False,
                },
                "_command": command,
            }
    return result


def public_catalog():
    return [
        {k: v for k, v in entry.items() if not k.startswith("_")}
        for entry in registry().values()
    ]


def validate_arguments(operation, arguments):
    entry = registry().get(operation)
    if not entry:
        raise Problem(400, "不支持的操作；文件路径和本地审批命令不会暴露为 MCP 工具")
    if len(json.dumps(arguments)) > 256000:
        raise Problem(413, "操作参数过大")
    unknown = set(arguments) - set(entry["inputSchema"]["properties"])
    if unknown:
        raise Problem(400, "未知参数: " + ", ".join(sorted(unknown)))
    for key in ("budget", "bid", "default_bid"):
        if arguments.get(key) is not None:
            value = arguments[key]
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value <= 0
            ):
                raise Problem(400, f"{key} 必须是大于零的有限数值")
    if operation.endswith("-raw.request"):
        path = arguments.get("path", "")
        product = operation.split("-")[0]
        if not re.fullmatch(r"/" + product + r"/[A-Za-z0-9/_-]+", path) or "//" in path:
            raise Problem(
                400, "原始接口路径必须在指定广告类型内，不允许查询串或路径跳转"
            )
    if operation == AMC_QUERY:
        try:
            resolve_amc_query(arguments.get("template"), arguments.get("sql"))
            check_amc_window(arguments.get("start_date"), arguments.get("end_date"))
        except ValueError as exc:
            raise Problem(400, str(exc)) from None
    elif entry["kind"] == "report":
        try:
            start, end = (
                date.fromisoformat(arguments["start_date"]),
                date.fromisoformat(arguments["end_date"]),
            )
        except (KeyError, TypeError, ValueError):
            raise Problem(400, "请提供有效的报表起止日期")
        if not 0 <= (end - start).days < 31:
            raise Problem(400, "单个报表任务最多 31 天；更长范围请拆分任务")
    return entry


def invoke_contract(operation, arguments, env, mode, token="", profiles=None):
    entry = validate_arguments(operation, arguments)
    expected = {"read": "read", "write": "plan", "report": "report_plan"}[entry["kind"]]
    if mode != expected:
        raise Problem(400, "操作类型与调用入口不匹配")
    command = entry["_command"]
    root = click.Context(cli, obj={"json": True})
    ctx = click.Context(command, parent=root, obj={"json": True})
    parsed = {}
    try:
        for p in command.params:
            value = (
                env.marketplace
                if p.name == "marketplace"
                else False
                if p.name in HIDDEN
                else arguments.get(p.name, p.get_default(ctx))
            )
            parsed[p.name] = p.process_value(ctx, value)
        runtime = OperationRuntime(
            env=env, mode=mode, token=token, profiles=profiles or []
        )
        with operation_runtime(runtime), root, ctx:
            ctx.invoke(command.callback, **parsed)
    except click.ClickException as exc:
        raise Problem(400, str(exc)) from None
    if mode == "plan":
        if not runtime.plan:
            raise Problem(500, "操作没有产生待确认计划")
        return runtime.plan
    if mode == "report_plan":
        if not runtime.report:
            raise Problem(500, "操作没有产生报表配置")
        return runtime.report
    if (
        isinstance(runtime.output, dict)
        and runtime.output.get("meta", {}).get("mode") == "mock"
    ):
        raise Problem(502, "真实 API 请求未成功；服务端不会以演示数据代替")
    return runtime.output
