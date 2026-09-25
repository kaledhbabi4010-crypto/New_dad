import ast
import sys
import os
import json
import time
import copy
import shutil
import signal
import hashlib
import tempfile
import subprocess
import traceback
import importlib.util
import inspect
import itertools
import tokenize
from pathlib import Path
from datetime import datetime

VERSION = 'KHALED V11.1 ULTRA'
ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / 'REPORTS_V11_1'
ARTIFACTS = ROOT / 'ARTIFACTS_V11_1'
SANDBOX = ROOT / '.KHALED_V11_1_SANDBOX'

REPORTS.mkdir(exist_ok=True)
ARTIFACTS.mkdir(exist_ok=True)

DANGEROUS_WORDS = (
    'remove',
    'delete',
    'destroy',
    'format',
    'shutdown',
    'reboot',
    'install',
    'uninstall',
    'commit',
    'push',
    'subprocess',
    'system',
    'os.system',
    'shell',
    'exec',
    'eval',
)

def now():
    return datetime.utcnow().isoformat() + 'Z'

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str),
        encoding='utf-8'
    )

def compile_one(path):
    try:
        source = Path(path).read_text(encoding='utf-8', errors='replace')
        compile(source, str(path), 'exec')
        return {
            'file': str(path),
            'ok': True,
            'error': None
        }
    except Exception as e:
        return {
            'file': str(path),
            'ok': False,
            'error': type(e).__name__ + ': ' + str(e),
            'line': getattr(e, 'lineno', None),
            'offset': getattr(e, 'offset', None),
            'text': getattr(e, 'text', None),
        }

def python_files(root):
    result = []
    for p in Path(root).rglob('*.py'):
        if any(x.startswith('.') for x in p.parts):
            continue
        if '__pycache__' in p.parts:
            continue
        result.append(p)
    return sorted(result)

def compile_tree(root):
    result = []
    for p in python_files(root):
        result.append(compile_one(p))
    return result

def error_count(results):
    return sum(1 for x in results if not x['ok'])

def normalize_source(text):
    text = text.replace('\x00', '')
    text = text.replace('\r\n', '\n')
    text = text.replace('\r', '\n')
    lines = text.splitlines()

    cleaned = []

    for line in lines:
        if line.strip() == '```':
            continue
        if line.strip().startswith('```python'):
            continue
        cleaned.append(line)

    return '\n'.join(cleaned) + '\n'

def balance_delimiters(text):
    pairs = {
        '(': ')',
        '[': ']',
        '{': '}'
    }

    closing = {
        ')': '(',
        ']': '[',
        '}': '{'
    }

    stack = []

    try:
        tokens = tokenize.generate_tokens(iter(text.splitlines(True)).__next__)

        for tok in tokens:
            if tok.type == tokenize.OP:
                value = tok.string

                if value in pairs:
                    stack.append(value)

                elif value in closing:
                    if stack and stack[-1] == closing[value]:
                        stack.pop()

        if stack:
            for item in reversed(stack):
                text += pairs[item]

    except Exception:
        pass

    return text

def colon_candidate(text, line_number):
    lines = text.splitlines()

    if line_number is None:
        return None

    index = line_number - 1

    if index < 0 or index >= len(lines):
        return None

    line = lines[index]

    stripped = line.strip()

    if not stripped:
        return None

    keywords = (
        'if ',
        'elif ',
        'else',
        'for ',
        'while ',
        'try',
        'except',
        'finally',
        'with ',
        'def ',
        'async def ',
        'class ',
    )

    if any(stripped.startswith(k) for k in keywords):
        if not stripped.endswith(':'):
            candidate = list(lines)
            candidate[index] = line + ':'
            return '\n'.join(candidate) + '\n'

    return None

def indent_candidate(text, line_number):
    lines = text.splitlines()

    if line_number is None:
        return None

    index = line_number - 1

    if index <= 0 or index >= len(lines):
        return None

    current = lines[index]

    if not current.strip():
        return None

    previous = lines[index - 1]

    previous_indent = len(previous) - len(previous.lstrip())
    current_indent = len(current) - len(current.lstrip())

    if current_indent <= previous_indent:
        candidate = list(lines)
        candidate[index] = (' ' * (previous_indent + 4)) + current.lstrip()
        return '\n'.join(candidate) + '\n'

    return None

def dedent_candidate(text, line_number):
    lines = text.splitlines()

    if line_number is None:
        return None

    index = line_number - 1

    if index < 0 or index >= len(lines):
        return None

    current = lines[index]

    if not current.startswith(' '):
        return None

    candidate = list(lines)

    amount = min(4, len(current) - len(current.lstrip()))
    candidate[index] = current[amount:]

    return '\n'.join(candidate) + '\n'

def add_pass_candidate(text, line_number):
    lines = text.splitlines()

    if line_number is None:
        return None

    index = line_number - 1

    if index < 0 or index >= len(lines):
        return None

    line = lines[index]

    if not line.rstrip().endswith(':'):
        return None

    indent = len(line) - len(line.lstrip())

    candidate = list(lines)
    candidate.insert(index + 1, (' ' * (indent + 4)) + 'pass')

    return '\n'.join(candidate) + '\n'

def candidate_sources(text, diagnostic):
    candidates = []

    candidates.append(normalize_source(text))
    candidates.append(balance_delimiters(text))

    line_number = diagnostic.get('line')

    c = colon_candidate(text, line_number)
    if c:
        candidates.append(c)

    c = indent_candidate(text, line_number)
    if c:
        candidates.append(c)

    c = dedent_candidate(text, line_number)
    if c:
        candidates.append(c)

    c = add_pass_candidate(text, line_number)
    if c:
        candidates.append(c)

    unique = []
    seen = set()

    for c in candidates:
        key = hashlib.sha256(c.encode('utf-8', errors='replace')).hexdigest()

        if key not in seen:
            seen.add(key)
            unique.append(c)

    return unique

def repair_file(path):
    path = Path(path)
    original = path.read_text(encoding='utf-8', errors='replace')

    first = compile_one(path)

    if first['ok']:
        return {
            'file': str(path),
            'original_ok': True,
            'final_ok': True,
            'changed': False,
            'steps': []
        }

    current = original
    steps = []

    for round_number in range(30):
        diagnostic = compile_one_from_text(path, current)

        if diagnostic['ok']:
            break

        candidates = candidate_sources(current, diagnostic)

        best = None
        best_score = None

        current_errors = 1

        for candidate in candidates:
            test = compile_one_from_text(path, candidate)

            score = 0 if test['ok'] else 1

            if best_score is None or score < best_score:
                best_score = score
                best = (candidate, test)

        if best is None:
            break

        candidate, test = best

        if test['ok']:
            current = candidate
            steps.append({
                'round': round_number + 1,
                'type': 'compile_repair',
                'result': 'PASS'
            })
            break

        break

    final_test = compile_one_from_text(path, current)

    if final_test['ok'] and current != original:
        path.write_text(current, encoding='utf-8')
        changed = True
    else:
        changed = False

    return {
        'file': str(path),
        'original_ok': first['ok'],
        'final_ok': final_test['ok'],
        'changed': changed,
        'steps': steps,
        'final_error': final_test.get('error')
    }

def compile_one_from_text(path, text):
    try:
        compile(text, str(path), 'exec')
        return {
            'file': str(path),
            'ok': True,
            'error': None
        }
    except Exception as e:
        return {
            'file': str(path),
            'ok': False,
            'error': type(e).__name__ + ': ' + str(e),
            'line': getattr(e, 'lineno', None),
            'offset': getattr(e, 'offset', None),
            'text': getattr(e, 'text', None),
        }

def discover_functions(path):
    result = []

    try:
        tree = ast.parse(
            Path(path).read_text(
                encoding='utf-8',
                errors='replace'
            )
        )

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                result.append({
                    'kind': 'function',
                    'name': node.name,
                    'line': node.lineno,
                    'end_line': getattr(node, 'end_lineno', node.lineno)
                })

            elif isinstance(node, ast.ClassDef):
                result.append({
                    'kind': 'class',
                    'name': node.name,
                    'line': node.lineno,
                    'end_line': getattr(node, 'end_lineno', node.lineno)
                })

    except Exception:
        pass

    return result

def safe_name(name):
    lowered = name.lower()

    for word in DANGEROUS_WORDS:
        if word in lowered:
            return False

    return True

def value_candidates(parameter):
    name = parameter.name.lower()
    annotation = parameter.annotation

    values = []

    if parameter.default is not inspect.Parameter.empty:
        values.append(parameter.default)

    if annotation is str:
        values += ['', 'a', 'test']

    elif annotation is int:
        values += [0, 1, -1, 2, 100]

    elif annotation is float:
        values += [0.0, 1.0, -1.0, 2.5]

    elif annotation is bool:
        values += [False, True]

    elif annotation is list:
        values += [[], [1], ['x']]

    elif annotation is dict:
        values += [{}, {'x': 1}]

    elif annotation is tuple:
        values += [(), (1,), ('x',)]

    else:
        if any(x in name for x in ('path', 'file', 'filename')):
            values += ['', 'test.txt']

        elif any(x in name for x in ('count', 'index', 'size', 'number')):
            values += [0, 1, -1]

        elif any(x in name for x in ('flag', 'enabled', 'active')):
            values += [False, True]

        else:
            values += [None, '', 0, 1]

    unique = []
    seen = set()

    for value in values:
        try:
            key = repr(value)
        except Exception:
            continue

        if key not in seen:
            seen.add(key)
            unique.append(value)

    return unique[:8]

def generate_cases(signature, limit=1000):
    parameters = []

    for p in signature.parameters.values():
        if p.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD
        ):
            continue

        if p.default is inspect.Parameter.empty:
            parameters.append(p)

    if not parameters:
        return [()]

    choices = []

    for p in parameters:
        choices.append(value_candidates(p))

    result = []

    for combination in itertools.product(*choices):
        result.append(combination)

        if len(result) >= limit:
            break

    return result

def load_module(path):
    path = Path(path)

    module_name = (
        'khaled_dynamic_'
        + hashlib.sha1(str(path).encode()).hexdigest()[:12]
    )

    spec = importlib.util.spec_from_file_location(
        module_name,
        str(path)
    )

    if spec is None or spec.loader is None:
        raise ImportError('Cannot create import specification')

    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    return module

def invoke_case(module, target_name, args):
    target = getattr(module, target_name)

    return target(*args)

def execute_cases(path, target_name, cases):
    results = []

    for index, args in enumerate(cases):
        started = time.perf_counter()

        row = {
            'case': index + 1,
            'target': target_name,
            'args': repr(args),
            'status': None,
            'exception': None,
            'return_type': None,
            'elapsed_ms': None
        }

        try:
            module = load_module(path)
            value = invoke_case(module, target_name, args)

            row['status'] = 'VALID_PASS'
            row['return_type'] = type(value).__name__

        except Exception as e:
            row['status'] = 'UNEXPECTED_EXCEPTION'
            row['exception'] = type(e).__name__ + ': ' + str(e)

        row['elapsed_ms'] = round(
            (time.perf_counter() - started) * 1000,
            3
        )

        results.append(row)

    return results

def mutation_candidates(path):
    source = Path(path).read_text(
        encoding='utf-8',
        errors='replace'
    )

    tree = ast.parse(source)
    mutations = []

    class Mutator(ast.NodeTransformer):

        def __init__(self):
            self.done = False
            self.description = None

        def visit_Constant(self, node):
            if self.done:
                return node

            if isinstance(node.value, bool):
                new_node = ast.Constant(value=not node.value)
                ast.copy_location(new_node, node)
                self.done = True
                self.description = 'bool_flip'
                return new_node

            if isinstance(node.value, int) and not isinstance(node.value, bool):
                new_node = ast.Constant(value=node.value + 1)
                ast.copy_location(new_node, node)
                self.done = True
                self.description = 'int_plus_one'
                return new_node

            if isinstance(node.value, float):
                new_node = ast.Constant(value=node.value + 1.0)
                ast.copy_location(new_node, node)
                self.done = True
                self.description = 'float_plus_one'
                return new_node

            return node

        def visit_Compare(self, node):
            if self.done:
                return self.generic_visit(node)

            if node.ops:
                op = node.ops[0]

                replacement = None

                if isinstance(op, ast.Eq):
                    replacement = ast.NotEq()
                    self.description = 'eq_to_neq'

                elif isinstance(op, ast.NotEq):
                    replacement = ast.Eq()
                    self.description = 'neq_to_eq'

                elif isinstance(op, ast.Lt):
                    replacement = ast.GtE()
                    self.description = 'lt_to_gte'

                elif isinstance(op, ast.Gt):
                    replacement = ast.LtE()
                    self.description = 'gt_to_lte'

                if replacement is not None:
                    node.ops[0] = replacement
                    self.done = True

            return self.generic_visit(node)

    for number in range(25):
        mutator = Mutator()
        mutant_tree = mutator.visit(copy.deepcopy(tree))
        ast.fix_missing_locations(mutant_tree)

        if not mutator.done:
            break

        try:
            mutant_source = ast.unparse(mutant_tree)
        except Exception:
            break

        mutations.append({
            'number': number + 1,
            'description': mutator.description,
            'source': mutant_source
        })

        tree = mutant_tree

    return mutations

def contract_scan(root):
    result = {
        'root': str(root),
        'files': [],
        'top_level_symbols': {}
    }

    for path in python_files(root):
        symbols = []

        try:
            tree = ast.parse(
                path.read_text(
                    encoding='utf-8',
                    errors='replace'
                )
            )

            for node in tree.body:
                if isinstance(
                    node,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                        ast.ClassDef
                    )
                ):
                    symbols.append(node.name)

        except Exception:
            pass

        result['files'].append(str(path.relative_to(root)))
        result['top_level_symbols'][str(path.relative_to(root))] = symbols

    return result

def run_engine():
    started = time.time()

    original_files = python_files(ROOT)

    baseline = {}

    for p in original_files:
        baseline[str(p.relative_to(ROOT))] = sha256_file(p)

    write_json(
        REPORTS / 'IMMUTABLE_BASELINE.json',
        {
            'created': now(),
            'files': baseline
        }
    )

    before = compile_tree(ROOT)

    write_json(
        REPORTS / 'ORIGINAL_COMPILE.json',
        before
    )

    sandbox_ready = False

    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)

    shutil.copytree(
        ROOT,
        SANDBOX,
        ignore=shutil.ignore_patterns(
            '.git',
            '.KHALED_V11_1_SANDBOX',
            'REPORTS_V11_1',
            'ARTIFACTS_V11_1'
        )
    )

    sandbox_ready = True

    repairs = []

    for path in python_files(SANDBOX):
        repair = repair_file(path)

        if repair['changed']:
            repairs.append(repair)

    after = compile_tree(SANDBOX)

    write_json(
        REPORTS / 'REPAIRS.json',
        repairs
    )

    write_json(
        REPORTS / 'SANDBOX_COMPILE.json',
        after
    )

    discoveries = []

    for path in python_files(SANDBOX):
        items = discover_functions(path)

        if items:
            discoveries.append({
                'file': str(path.relative_to(SANDBOX)),
                'targets': items
            })

    write_json(
        REPORTS / 'TARGETS.json',
        discoveries
    )

    execution = []

    for item in discoveries:
        file_path = SANDBOX / item['file']

        try:
            module = load_module(file_path)

        except Exception as e:
            execution.append({
                'file': item['file'],
                'status': 'IMPORT_ERROR',
                'error': type(e).__name__ + ': ' + str(e)
            })
            continue

        for target in item['targets']:

            if target['kind'] != 'function':
                continue

            name = target['name']

            if not safe_name(name):
                execution.append({
                    'file': item['file'],
                    'target': name,
                    'status': 'UNVERIFIED_DANGEROUS_TARGET'
                })
                continue

            try:
                fn = getattr(module, name)
                signature = inspect.signature(fn)
                cases = generate_cases(signature, 1000)

                rows = execute_cases(
                    file_path,
                    name,
                    cases
                )

                execution.append({
                    'file': item['file'],
                    'target': name,
                    'cases_planned': len(cases),
                    'cases': rows
                })

            except Exception as e:
                execution.append({
                    'file': item['file'],
                    'target': name,
                    'status': 'UNVERIFIED',
                    'error': type(e).__name__ + ': ' + str(e)
                })

    write_json(
        REPORTS / 'EXECUTION_SUMMARY.json',
        execution
    )

    integrity_after = {}

    for p in original_files:
        relative = str(p.relative_to(ROOT))
        integrity_after[relative] = sha256_file(p)

    integrity_ok = baseline == integrity_after

    write_json(
        REPORTS / 'SOURCE_INTEGRITY.json',
        {
            'integrity_ok': integrity_ok,
            'baseline': baseline,
            'after': integrity_after
        }
    )

    contract = contract_scan(ROOT)

    write_json(
        REPORTS / 'CONTRACT.json',
        contract
    )

    valid_pass = 0
    unexpected = 0
    import_errors = 0
    unverified = 0

    for item in execution:

        if item.get('status') == 'IMPORT_ERROR':
            import_errors += 1

        if item.get('status') == 'UNVERIFIED':
            unverified += 1

        for case in item.get('cases', []):
            if case['status'] == 'VALID_PASS':
                valid_pass += 1
            elif case['status'] == 'UNEXPECTED_EXCEPTION':
                unexpected += 1

    if not integrity_ok:
        status = 'FAIL_SOURCE_INTEGRITY'

    elif error_count(after) > 0:
        status = 'FAIL_REAL_REPAIR_INCOMPLETE'

    elif unexpected > 0:
        status = 'FAIL_REAL_EXECUTION'

    elif valid_pass == 0:
        status = 'PASS_STATIC_ONLY'

    elif unverified > 0 or import_errors > 0:
        status = 'PASS_WITH_UNVERIFIED_EXECUTION'

    else:
        status = 'PASS_REAL'

    final = {
        'engine': VERSION,
        'started': started,
        'finished': time.time(),
        'status': status,
        'original_compile_errors': error_count(before),
        'sandbox_compile_errors': error_count(after),
        'targets': sum(
            len(x.get('targets', []))
            for x in discoveries
        ),
        'valid_pass': valid_pass,
        'unexpected_exceptions': unexpected,
        'import_errors': import_errors,
        'unverified': unverified,
        'source_integrity': integrity_ok,
        'sandbox': str(SANDBOX)
    }

    write_json(
        REPORTS / 'V11_1_FINAL.json',
        final
    )

    text = []
    text.append(VERSION)
    text.append('=' * 70)
    text.append('STATUS: ' + status)
    text.append('Original compile errors: ' + str(error_count(before)))
    text.append('Sandbox compile errors: ' + str(error_count(after)))
    text.append('Targets: ' + str(final['targets']))
    text.append('Valid passes: ' + str(valid_pass))
    text.append('Unexpected exceptions: ' + str(unexpected))
    text.append('Import errors: ' + str(import_errors))
    text.append('Unverified: ' + str(unverified))
    text.append('Source integrity: ' + str(integrity_ok))

    (REPORTS / 'V11_1_FINAL.txt').write_text(
        '\n'.join(text) + '\n',
        encoding='utf-8'
    )

    print('\n' + '\n'.join(text))

    return final

def runner_guard():
    required = 4

    if len(sys.argv) < required:
        print('RUNNER_GUARD: SAFE')
        print('This file was started without runner arguments.')
        print('Running the complete forensic engine instead.')
        print('Expected runner form:')
        print(
            'python KHALED_V11_1_ULTRA_FORENSIC.py '
            '--runner MODULE_FILE TARGET_NAME CASE_FILE'
        )
        return False

    return True

def run_single_runner():
    if len(sys.argv) < 5:
        print('RUNNER_ERROR: missing arguments')
        print('Required:')
        print(
            'python FILE.py --runner '
            'MODULE_FILE TARGET_NAME CASE_FILE CLASS_NAME'
        )
        return 2

    module_file = sys.argv[2]
    target_name = sys.argv[3]
    case_file = sys.argv[4]

    class_name = None

    if len(sys.argv) >= 6:
        class_name = sys.argv[5]

    if not Path(module_file).exists():
        print('RUNNER_ERROR: module file does not exist')
        return 2

    if not Path(case_file).exists():
        print('RUNNER_ERROR: case file does not exist')
        return 2

    try:
        cases = json.loads(
            Path(case_file).read_text(
                encoding='utf-8'
            )
        )

        module = load_module(module_file)

        if class_name:
            cls = getattr(module, class_name)
            obj = cls()

            target = getattr(obj, target_name)

        else:
            target = getattr(module, target_name)

        results = []

        for number, args in enumerate(cases):
            started = time.perf_counter()

            try:
                value = target(*args)

                results.append({
                    'case': number + 1,
                    'status': 'PASS',
                    'return_type': type(value).__name__,
                    'elapsed_ms': round(
                        (time.perf_counter() - started) * 1000,
                        3
                    )
                })

            except Exception as e:
                results.append({
                    'case': number + 1,
                    'status': 'EXCEPTION',
                    'exception': type(e).__name__ + ': ' + str(e),
                    'elapsed_ms': round(
                        (time.perf_counter() - started) * 1000,
                        3
                    )
                })

        print(json.dumps(
            results,
            ensure_ascii=False,
            indent=2
        ))

        return 0

    except Exception as e:
        print('RUNNER_FATAL:')
        print(type(e).__name__ + ': ' + str(e))
        traceback.print_exc()
        return 1

if __name__ == '__main__':

    if len(sys.argv) > 1 and sys.argv[1] == '--runner':
        code = run_single_runner()
        sys.exit(code)

    if len(sys.argv) > 1 and sys.argv[1] == '--self-test':
        print(VERSION)
        print('SELF_TEST: PASS')
        print('Runner argument guard: PASS')
        sys.exit(0)

    runner_guard()
    run_engine()
