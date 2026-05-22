"""
ChatBot adapter that uses a local `claude` CLI (Claude Code) instance as the
LLM backend, instead of the OpenAI API.

This lets the app run with no OpenAI key and no GPU: each `prompt()` call shells
out to `claude -p` (headless / "print" mode), reusing the existing Claude Code
OAuth login in ~/.claude/.credentials.json.

The OpenAI-style message list ([{role, content}, ...]) is rendered into:
  - a single system prompt (all `system` turns concatenated) -> --system-prompt
  - a transcript of the user/assistant turns, sent on stdin, with an
    instruction to produce only the next assistant reply.
"""

import asyncio
import json
import os
import shutil

# Map the OpenAI model names used in the codebase to Claude aliases.
_MODEL_MAP = {
    "gpt-4.1-mini": "claude-haiku-4-5",  # fast path: scene generation, descriptions
    "o4-mini": "claude-sonnet-4-6",      # heavier path: story metadata
}
_DEFAULT_MODEL = "claude-sonnet-4-6"

# Make sure the nvm-installed `claude` binary is discoverable from subprocesses.
_NODE_BIN = "/teamspace/studios/this_studio/.nvm/versions/node/v22.14.0/bin"


def _resolve_claude() -> str:
    path = shutil.which("claude")
    if path:
        return path
    candidate = os.path.join(_NODE_BIN, "claude")
    if os.path.exists(candidate):
        return candidate
    raise RuntimeError("`claude` CLI not found on PATH")


def _render_transcript(non_system_messages) -> str:
    """Flatten user/assistant turns into a labelled transcript for the CLI."""
    lines = [
        "Below is a conversation. Continue it by producing ONLY the assistant's "
        "next reply. Do not add any commentary, labels, or markdown code fences.",
        "",
    ]
    for msg in non_system_messages:
        role = msg["role"].upper()
        lines.append(f"[{role}]:")
        lines.append(str(msg["content"]))
        lines.append("")
    lines.append("[ASSISTANT]:")
    return "\n".join(lines)


def _strip_fences(text: str) -> str:
    """Remove ```json ... ``` fences the model may wrap output in."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t[3:]
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


class ChatBot:
    def __init__(self, model_name="gpt-4.1-mini") -> None:
        self.model_name = _MODEL_MAP.get(model_name, _DEFAULT_MODEL)

    async def prompt(self, messages):
        system_parts = [
            str(m["content"]) for m in messages if m.get("role") == "system"
        ]
        non_system = [m for m in messages if m.get("role") != "system"]

        system_prompt = "\n\n".join(system_parts).strip()
        transcript = _render_transcript(non_system)

        env = dict(os.environ)
        env["PATH"] = _NODE_BIN + os.pathsep + env.get("PATH", "")

        args = [
            _resolve_claude(),
            "-p",
            "--model", self.model_name,
            "--output-format", "json",
            "--no-session-persistence",
            # Pure text generation: forbid any tool use so it never tries to
            # read files, run bash, etc.
            "--disallowed-tools", "Bash Edit Write Read Glob Grep WebFetch WebSearch",
        ]
        if system_prompt:
            args += ["--system-prompt", system_prompt]

        proc = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await proc.communicate(input=transcript.encode())

        if proc.returncode != 0:
            raise RuntimeError(
                f"claude CLI failed (code {proc.returncode}): "
                f"{stderr.decode(errors='replace')[:2000]}"
            )

        raw = stdout.decode(errors="replace").strip()
        # --output-format json wraps the answer: {"result": "...", ...}
        try:
            payload = json.loads(raw)
            result = payload.get("result", raw) if isinstance(payload, dict) else raw
        except json.JSONDecodeError:
            result = raw

        return _strip_fences(result)
