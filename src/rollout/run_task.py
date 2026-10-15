#!/usr/bin/env python3
"""Run one arm of one task with mini-swe-agent (text-based actions) driving a local vLLM model inside the
repo's docker image, and write the run artifacts that src/checker/checker.py reads.

usage: run_task.py data/tasks/<repo_key>/<task_id> A|B [--seq N] [--timeout 1800] [--port 8000]
       [--model Qwen3.5-4B] [--step-limit 50] [--runs-root work/runs]
"""
from __future__ import annotations
import argparse, hashlib, json, os, pathlib, re, shlex, subprocess, sys, time, logging
from datetime import datetime, timezone
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from container import sh, dexec, SNAPSHOT_PY, PATH_TOKEN
ROOT = pathlib.Path(__file__).resolve().parents[2]
os.environ.setdefault('MSWEA_COST_TRACKING', 'ignore_errors')
os.environ.setdefault('MSWEA_GLOBAL_CONFIG_FILE', '/dev/null')
from minisweagent.agents.default import DefaultAgent
from minisweagent.models.litellm_textbased_model import LitellmTextbasedModel
from minisweagent.exceptions import Submitted, FormatError, InterruptAgentFlow

SYSTEM_TEMPLATE = """You are a software engineering agent working in a terminal inside a git repository.

Your response must contain exactly ONE bash code block with ONE command (or commands connected with && or ||).
Write your reasoning before the command. Format:

<format_example>
Your reasoning here.

```mswea_bash_command
your_command_here
```
</format_example>

Rules:
- Every response must contain exactly one action, enclosed in a ```mswea_bash_command block.
- Each command runs in a fresh subshell in the repository directory; `cd` and environment variables do not persist between commands.
- Edit files with shell tools (e.g. `cat <<'EOF' > file`, `sed -i`, `python3 - <<'EOF'`), and view files with `nl -ba file | sed -n '10,40p'`.
- When you have finished the task, run exactly `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` as your only command. You cannot continue after it.
"""
INSTANCE_TEMPLATE = """{{task}}"""
OBS_TEMPLATE = """<returncode>{{output.returncode}}</returncode>
{% if output.output | length < 12000 -%}
<output>
{{ output.output -}}
</output>
{%- else -%}
<warning>Output too long ({{ output.output | length }} chars); showing the first and last 5000 characters.</warning>
<output_head>
{{ output.output[:5000] }}
</output_head>
<output_tail>
{{ output.output[-5000:] }}
</output_tail>
{%- endif %}"""
FORMAT_ERROR = "Your response must contain exactly ONE ```mswea_bash_command block (found {{actions|length}}). Reply again with reasoning and exactly one command block."

class ContainerEnv:
    """mini-swe-agent Environment over an already-running docker container (created by this runner)."""
    def __init__(self, container, workdir, cmd_timeout, log):
        self.container, self.workdir, self.cmd_timeout, self.log = container, workdir, cmd_timeout, log
        self.t0 = time.monotonic()
    def get_template_vars(self, **kw): return dict(cwd=self.workdir, **kw)
    def serialize(self): return {'info': {'config': {'environment': {'container': self.container, 'workdir': self.workdir}, 'environment_type': 'ContainerEnv'}}}
    def execute(self, action, cwd='', *, timeout=None):
        command = action.get('command', '')
        t_start = round(time.monotonic() - self.t0, 3)
        try:
            r = subprocess.run(['docker', 'exec', '-w', cwd or self.workdir, '-e', 'PAGER=cat', '-e', 'GIT_PAGER=cat', '-e', 'PIP_PROGRESS_BAR=off', '-e', 'TQDM_DISABLE=1', '-e', 'NO_COLOR=1',
                                self.container, 'bash', '-lc', command], text=True, encoding='utf-8', errors='replace',
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout or self.cmd_timeout)
            out = {'output': r.stdout, 'returncode': r.returncode, 'exception_info': ''}
        except subprocess.TimeoutExpired as e:
            raw = e.output.decode('utf-8', errors='replace') if isinstance(e.output, bytes) else (e.output or '')
            out = {'output': raw + f'\n[command killed after {self.cmd_timeout}s timeout]', 'returncode': -1, 'exception_info': f'timeout after {self.cmd_timeout}s'}
            subprocess.run(['docker', 'exec', self.container, 'sh', '-c', "for p in /proc/[0-9]*; do pid=${p#/proc/}; [ \"$pid\" = 1 ] && continue; kill -9 $pid 2>/dev/null; done; true"], capture_output=True, timeout=60)
        except Exception as e:
            out = {'output': '', 'returncode': -1, 'exception_info': f'{type(e).__name__}: {e}'}
        t_end = round(time.monotonic() - self.t0, 3)
        self.log.append(dict(t_start=t_start, t_end=t_end, command=command, exit_code=out['returncode'], output=out['output']))
        lines = out['output'].lstrip().splitlines(keepends=True)
        if lines and lines[0].strip() == 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT' and out['returncode'] == 0:
            raise Submitted({'role': 'exit', 'content': ''.join(lines[1:]), 'extra': {'exit_status': 'Submitted', 'submission': ''.join(lines[1:])}})
        return out

class UsageModel(LitellmTextbasedModel):
    """Text-based litellm model that also records token usage per call."""
    def __init__(self, **kw):
        super().__init__(**kw); self.usage_log = []
    def _query(self, messages, **kwargs):
        t0 = time.time(); resp = super()._query(messages, **kwargs)
        u = getattr(resp, 'usage', None)
        self.usage_log.append(dict(t=round(time.time() - t0, 2), prompt_tokens=getattr(u, 'prompt_tokens', None), completion_tokens=getattr(u, 'completion_tokens', None),
                                   finish_reason=resp.choices[0].finish_reason, reasoning_chars=len(getattr(resp.choices[0].message, 'reasoning_content', '') or '')))
        return resp

def run_until_exit(agent):
    """Same loop as DefaultAgent.run(), but starting from the current message list (used for later turns)."""
    while True:
        try:
            agent.step(); agent.n_consecutive_format_errors = 0
        except FormatError as e:
            agent.n_consecutive_format_errors += 1
            if 0 < agent.config.max_consecutive_format_errors <= agent.n_consecutive_format_errors:
                agent.add_messages(*e.messages, {'role': 'exit', 'content': 'RepeatedFormatError', 'extra': {'exit_status': 'RepeatedFormatError', 'submission': ''}})
            else: agent.add_messages(*e.messages)
        except InterruptAgentFlow as e:
            agent.add_messages(*e.messages)
        except Exception as e:
            agent.handle_uncaught_exception(e); break
        if agent.messages[-1].get('role') == 'exit': break
    return agent.messages[-1].get('extra', {})

def last_assistant_text(messages):
    for m in reversed(messages):
        if m.get('role') == 'assistant' and m.get('content'):
            return re.sub(r'```mswea_bash_command.*?```', '', m['content'], flags=re.S).strip()
    return ''

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('task_dir'); ap.add_argument('arm', choices=['A', 'B'])
    ap.add_argument('--seq', type=int, default=None); ap.add_argument('--timeout', type=int, default=None, help='wall-clock limit for the agent (default 1800, 3000 for Go images)')
    ap.add_argument('--port', type=int, default=8000); ap.add_argument('--model', default='Qwen3.5-4B')
    ap.add_argument('--step-limit', type=int, default=50); ap.add_argument('--cmd-timeout', type=int, default=900)
    ap.add_argument('--max-tokens', type=int, default=6000); ap.add_argument('--temperature', type=float, default=1.0)
    ap.add_argument('--thinking', type=int, default=1); ap.add_argument('--runs-root', default='work/runs')
    a = ap.parse_args()
    task_dir = pathlib.Path(a.task_dir).resolve(); task = json.loads((task_dir / 'task.json').read_text())
    arm_dir = task_dir / f'arm{a.arm}'
    repo_key = task['repo'].replace('/', '__'); image = task.get('image') or f'forkdpo-run:{repo_key}'; workdir = task['workdir']
    is_go = 'go_' in (ROOT / 'data' / 'environments' / repo_key / 'Dockerfile').read_text().splitlines()[0]
    timeout = a.timeout or (3000 if is_go else 1800)
    runs_root = ROOT / a.runs_root / repo_key / task['task_id'] / a.arm; runs_root.mkdir(parents=True, exist_ok=True)
    seq = a.seq or (1 + sum(1 for p in runs_root.iterdir() if p.is_dir()))
    run_id = f"{task['task_id']}-{a.arm}-q{seq:02d}"; run_dir = runs_root / run_id
    if run_dir.exists(): raise SystemExit(f'run dir exists: {run_dir}')
    run_dir.mkdir()
    c = f'forkdpo-q-{run_id}'.replace('/', '_')[:60]
    started = datetime.now(timezone.utc).isoformat()
    r = sh(['docker', 'run', '-d', '--platform', 'linux/amd64', '--name', c, '-e', 'NO_COLOR=1', '--memory', '3g', '--cpus', '3', image, 'sleep', str(timeout * 3 + 3600)])
    if r.returncode != 0: raise SystemExit('docker run failed: ' + r.stderr)
    try:
        dexec(c, 'git config core.fileMode false && git update-index -q --refresh || true', workdir=workdir)
        setup_log = {}
        if (arm_dir / 'overlay').is_dir():
            r = sh(['docker', 'cp', str(arm_dir / 'overlay') + '/.', f'{c}:{workdir}/']); setup_log['overlay_rc'] = r.returncode
        if (arm_dir / 'setup.sh').exists():
            r = dexec(c, 'bash -s', workdir=workdir, stdin=(arm_dir / 'setup.sh').read_text(), timeout=600)
            setup_log.update(setup_rc=r.returncode, setup_out=r.stdout[-4000:], setup_err=r.stderr[-4000:])
            if r.returncode != 0: raise SystemExit(f'setup.sh failed: {r.stderr[-2000:]}')
        base_head = dexec(c, 'git rev-parse HEAD', workdir=workdir).stdout.strip()
        base_status = dexec(c, 'git status --porcelain=v1 --untracked-files=all', workdir=workdir).stdout
        snap = dexec(c, f'python3 - {shlex.quote(workdir)}', workdir=workdir, stdin=SNAPSHOT_PY, timeout=900)
        before = json.loads(snap.stdout or '{}')
        (run_dir / 'before.json').write_text(json.dumps(dict(head=base_head, status=base_status, files=before), ensure_ascii=False))
        # --- agent ---
        cmd_log = []
        env = ContainerEnv(c, workdir, a.cmd_timeout, cmd_log)
        model = UsageModel(model_name=f'openai/{a.model}', observation_template=OBS_TEMPLATE, format_error_template=FORMAT_ERROR,
                           model_kwargs=dict(api_base=f'http://localhost:{a.port}/v1', api_key='EMPTY', temperature=a.temperature, top_p=0.95, max_tokens=a.max_tokens,
                                             extra_body={'chat_template_kwargs': {'enable_thinking': bool(a.thinking)}, 'top_k': 20}, timeout=600, num_retries=2))
        agent = DefaultAgent(model, env, system_template=SYSTEM_TEMPLATE, instance_template=INSTANCE_TEMPLATE, step_limit=a.step_limit, cost_limit=0,
                             wall_time_limit_seconds=timeout, max_consecutive_format_errors=4, output_path=run_dir / 'trajectory.json')
        t0 = time.monotonic(); turn_summ = []; finals = []
        turns_file = arm_dir / 'turns.json'
        turns = json.loads(turns_file.read_text()) if turns_file.exists() else [(arm_dir / 'prompt.md').read_text()]
        prompt_sha = hashlib.sha256((turns_file if turns_file.exists() else arm_dir / 'prompt.md').read_bytes()).hexdigest()
        for i, user_msg in enumerate(turns, 1):
            (run_dir / (f'turn{i}.prompt.md' if len(turns) > 1 else 'prompt.md')).write_text(user_msg)
            tt = time.monotonic(); n0 = len(cmd_log)
            if i == 1:
                res = agent.run(task=user_msg)
            else:
                if agent.messages and agent.messages[-1].get('role') == 'exit': agent.messages.pop()
                agent.add_messages(agent.model.format_message(role='user', content=user_msg))
                res = run_until_exit(agent)
            final = last_assistant_text(agent.messages); finals.append(final)
            if len(turns) > 1: (run_dir / f'turn{i}.message.md').write_text(final or '(none)')
            turn_summ.append(dict(turn=i, duration=round(time.monotonic() - tt, 1), exit_status=res.get('exit_status'), n_commands=len(cmd_log) - n0))
        agent.save(run_dir / 'trajectory.json')
        exit_status = agent.messages[-1].get('extra', {}).get('exit_status') if agent.messages else None
        (run_dir / 'final_message.md').write_text('\n\n---\n\n'.join(finals) or '(no agent message captured)')
        # --- after state ---
        snap = dexec(c, f'python3 - {shlex.quote(workdir)}', workdir=workdir, stdin=SNAPSHOT_PY, timeout=900)
        after = json.loads(snap.stdout or '{}')
        head_after = dexec(c, 'git rev-parse HEAD', workdir=workdir).stdout.strip()
        git_after = dict(head=head_after, status=dexec(c, 'git status --porcelain=v1 --untracked-files=all', workdir=workdir).stdout,
                         log=dexec(c, f'git log --format="%H %an %ad %s" {base_head}..HEAD', workdir=workdir).stdout, stash=dexec(c, 'git stash list', workdir=workdir).stdout)
        (run_dir / 'git_after.json').write_text(json.dumps(git_after, ensure_ascii=False, indent=1))
        (run_dir / 'patch.diff').write_text(dexec(c, f'git diff {base_head}', workdir=workdir).stdout)
        (run_dir / 'patch_untracked.txt').write_text(dexec(c, 'git ls-files --others --exclude-standard; echo ---ignored---; git ls-files --others --ignored --exclude-standard', workdir=workdir).stdout)
        new = [p for p in after if p not in before]; deleted = [p for p in before if p not in after]
        modified = [p for p in after if p in before and after[p] != before[p]]
        (run_dir / 'changed_files.json').write_text(json.dumps(dict(new=new, modified=modified, deleted=deleted, before={p: before.get(p) for p in modified + deleted}, after={p: after.get(p) for p in new + modified}), ensure_ascii=False, indent=1))
        if new or modified:
            r = subprocess.run(['docker', 'exec', '-i', '-w', workdir, c, 'tar', '-cf', '-', '--ignore-failed-read', '-T', '-'], input='\n'.join(new + modified).encode(), capture_output=True)
            (run_dir / 'changed_files.tar').write_bytes(r.stdout)
        (run_dir / 'after.json').write_text(json.dumps(dict(head=head_after, files=after), ensure_ascii=False))
        tests_after = {}
        if (task_dir / 'oracle.sh').exists():
            to = time.monotonic()
            r = dexec(c, 'bash -s', workdir=workdir, stdin=(task_dir / 'oracle.sh').read_text(), timeout=1500)
            tests_after = dict(rc=r.returncode, duration=round(time.monotonic() - to, 1), stdout=r.stdout[-20000:], stderr=r.stderr[-20000:])
        (run_dir / 'tests_after.json').write_text(json.dumps(tests_after, ensure_ascii=False, indent=1))
        # --- derived: commands.jsonl, reads.json, metrics.json, config.json ---
        with open(run_dir / 'commands.jsonl', 'w') as fo:
            for i, row in enumerate(cmd_log): fo.write(json.dumps(dict(id=i, **row), ensure_ascii=False) + '\n')
        reads = {}; fileset = set(before)
        for row in cmd_log:
            cmdtxt = row['command']
            for tok in PATH_TOKEN.findall(cmdtxt):
                tk = tok[2:] if tok.startswith('./') else tok
                if tk in fileset: reads.setdefault(tk, []).append(dict(t=row['t_end'], cmd=cmdtxt[:200]))
                elif tk and re.search(r'\b(ls|rg|grep|find|tree|cat|sed|head|tail|nl)\b', cmdtxt):
                    for f in fileset:
                        if f.startswith(tk.rstrip('/') + '/'): reads.setdefault(f, []).append(dict(t=row['t_end'], cmd=cmdtxt[:200], via_dir=tk))
        (run_dir / 'reads.json').write_text(json.dumps(reads, ensure_ascii=False))
        usage = dict(input_tokens=sum(u['prompt_tokens'] or 0 for u in model.usage_log), output_tokens=sum(u['completion_tokens'] or 0 for u in model.usage_log),
                     reasoning_chars=sum(u['reasoning_chars'] for u in model.usage_log), n_calls=len(model.usage_log), length_truncations=sum(1 for u in model.usage_log if u['finish_reason'] == 'length'))
        patch = (run_dir / 'patch.diff').read_text()
        metrics = dict(ok=exit_status == 'Submitted', exit_status=exit_status, turns=turn_summ, duration_seconds=round(time.monotonic() - t0, 1), n_commands=len(cmd_log),
                       n_model_calls=agent.n_calls, format_errors=sum(1 for m in agent.messages if m.get('extra', {}).get('interrupt_type') == 'FormatError'), usage=usage,
                       diff_added=sum(1 for l in patch.splitlines() if l.startswith('+') and not l.startswith('+++')), diff_removed=sum(1 for l in patch.splitlines() if l.startswith('-') and not l.startswith('---')),
                       n_files_changed=len(new) + len(modified) + len(deleted), oracle_rc=tests_after.get('rc'), command_times=[[r['t_start'], r['t_end']] for r in cmd_log])
        (run_dir / 'metrics.json').write_text(json.dumps(metrics, ensure_ascii=False, indent=1))
        image_id = sh(['docker', 'inspect', '--format', '{{.Id}}', image]).stdout.strip()
        cfg = dict(run_id=run_id, task_id=task['task_id'], arm=a.arm, cls=task.get('class'), sub=task.get('sub'), repo=task['repo'], image=image, image_id=image_id, workdir=workdir, base_head=base_head,
                   agent='mini-swe-agent', agent_version=__import__('minisweagent').__version__, action_format='text (```mswea_bash_command)', model=a.model, served_by=f'vllm http://localhost:{a.port}',
                   sampling=dict(temperature=a.temperature, top_p=0.95, top_k=20, max_tokens=a.max_tokens, enable_thinking=bool(a.thinking)), step_limit=a.step_limit, cmd_timeout=a.cmd_timeout,
                   system_template=SYSTEM_TEMPLATE, instance_template=INSTANCE_TEMPLATE, sandbox='docker container; agent commands run via docker exec as root; container network: default bridge',
                   container_limits='3g / 3 cpus', prompt_file='turns.json' if len(turns) > 1 else 'prompt.md', prompt_sha256=prompt_sha, started_at=started, finished_at=datetime.now(timezone.utc).isoformat(), timeout=timeout, setup=setup_log)
        (run_dir / 'config.json').write_text(json.dumps(cfg, ensure_ascii=False, indent=1))
        with open(ROOT / a.runs_root / 'runs.jsonl', 'a') as fo:
            fo.write(json.dumps(dict(run_id=run_id, task_id=task['task_id'], arm=a.arm, repo=task['repo'], cls=task.get('class'), sub=task.get('sub'), dir=str(run_dir.relative_to(ROOT)),
                                     ok=metrics['ok'], exit_status=exit_status, oracle_rc=metrics['oracle_rc'], n_commands=metrics['n_commands'], duration=metrics['duration_seconds'], started=started)) + '\n')
        print(f"{run_id} exit={exit_status} cmds={len(cmd_log)} calls={agent.n_calls} oracle_rc={metrics['oracle_rc']} {metrics['duration_seconds']}s files={metrics['n_files_changed']}")
    finally:
        subprocess.run(['docker', 'rm', '-f', c], capture_output=True)

if __name__ == '__main__':
    main()
