"""Tests for bug_investigator.py — TDD-first, mirrors test_whats_new.py shape.

Block 1 — TestClassifyInput      (input-kind routing heuristics)
Block 2 — TestParsePanic         (macOS panic golden fixture decode)
Block 3 — TestThirdPartyKext     (driver-exclusion logic, both directions)
Block 4 — TestParseTraceback     (Python traceback frame extraction)
Block 5 — TestKarpathyGate       (claim must have a resolvable proof anchor)
Block 6 — TestStdlibOnly         (no third-party imports)
"""

from __future__ import annotations

import ast
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add parent dir (memory-mcp/) to sys.path — matches existing test convention
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bug_investigator import (  # noqa: E402
    Anchor,
    Claim,
    InputKind,
    classify_input,
    karpathy_gate,
    main,
    parse_panic,
    parse_traceback,
    redact_secrets,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Trimmed but faithful slice of the real panic the user hit (2026-05-19).
MACOS_PANIC = """\
panic(cpu 1 caller 0xfffffe0037230464): busy timeout[0], (60s): multiple \
entries holding the registry busy, IOKit termination queue depth 5249: \
'RootDomainUserClient' (1,2001), 'RootDomainUserClient' (1,2001), \
'RootDomainUserClient' (1,2001) @IOService.cpp:5963
Debugger message: panic
OS version: 25D2128
Kernel version: Darwin Kernel Version 25.3.0: Wed Jan 28 20:55:08 PST 2026; \
root:xnu-12377.91.3~2/RELEASE_ARM64_T6020
CORE 1 is the one that panicked. Check the full backtrace for details.
Panicked task 0xfffffe27a6f5eb30: 296 pages, 4 threads: pid 347: watchdogd
Panicked thread: 0xfffffe21d9e98e40, backtrace: 0xfffffe3cc4967330, tid: 289759
          lr: 0xfffffe0036a71e10  fp: 0xfffffe3cc49673d0
          lr: 0xfffffe0037230464  fp: 0xfffffe3cc4967b30
loaded kexts:
com.apple.filesystems.autofs    3.0
com.apple.driver.AppleTopCaseHIDEventDriver    9430.1
com.apple.filesystems.apfs    2632.80.1
com.apple.iokit.IOPCIFamily    2.9
com.apple.kec.corecrypto    26.0
"""

# Same shape, but with a third-party kernel extension injected.
PANIC_WITH_THIRD_PARTY = MACOS_PANIC.replace(
    "com.apple.kec.corecrypto    26.0",
    "com.apple.kec.corecrypto    26.0\norg.virtualbox.kext.VBoxDrv    7.0.14",
)

PY_TRACEBACK = """\
Traceback (most recent call last):
  File "/srv/app/worker.py", line 12, in <module>
    main()
  File "/srv/app/worker.py", line 8, in main
    process(payload)
  File "/srv/app/handlers.py", line 41, in process
    return data["user"]["id"]
KeyError: 'user'
"""

UNITTEST_FAILURE = """\
======================================================================
FAIL: test_widget (tests.test_widget.WidgetCase)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/p/tests/test_widget.py", line 9, in test_widget
    self.assertEqual(add(2, 2), 5)
AssertionError: 4 != 5
----------------------------------------------------------------------
Ran 1 test in 0.001s

FAILED (failures=1)
"""

NPM_BUILD_ERROR = """\
npm ERR! code ELIFECYCLE
npm ERR! Failed at the app@1.0.0 build script.
make: *** [build] Error 1
"""


# ---------------------------------------------------------------------------
# Block 1 — classify_input
# ---------------------------------------------------------------------------


class TestClassifyInput(unittest.TestCase):
    def test_kernel_panic(self):
        self.assertEqual(classify_input(MACOS_PANIC), InputKind.KERNEL_PANIC)

    def test_test_failure_beats_plain_traceback(self):
        # Has a Traceback block but is really a unittest failure.
        self.assertEqual(classify_input(UNITTEST_FAILURE), InputKind.TEST_FAILURE)

    def test_plain_traceback(self):
        self.assertEqual(classify_input(PY_TRACEBACK), InputKind.TRACEBACK)

    def test_build_error(self):
        self.assertEqual(classify_input(NPM_BUILD_ERROR), InputKind.BUILD_ERROR)

    def test_unknown(self):
        self.assertEqual(classify_input("hello world"), InputKind.UNKNOWN)


# ---------------------------------------------------------------------------
# Block 2 — parse_panic (the golden fixture)
# ---------------------------------------------------------------------------


class TestParsePanic(unittest.TestCase):
    def setUp(self):
        self.r = parse_panic(MACOS_PANIC)

    def test_fault_site(self):
        self.assertEqual(self.r.fault_site, "IOService.cpp:5963")

    def test_faulting_cpu(self):
        self.assertEqual(self.r.faulting_cpu, 1)

    def test_repeated_class_and_queue_depth(self):
        self.assertEqual(self.r.repeated_class, "RootDomainUserClient")
        self.assertEqual(self.r.termination_queue_depth, 5249)

    def test_panicked_task(self):
        self.assertEqual(self.r.panicked_task, "watchdogd")
        self.assertEqual(self.r.panicked_pid, 347)

    def test_darwin_and_macos_name(self):
        self.assertEqual(self.r.darwin_version, "25.3.0")
        self.assertIn("Tahoe", self.r.macos_name)
        self.assertIn("26", self.r.macos_name)

    def test_hardware_model(self):
        self.assertEqual(self.r.hardware_model, "Apple M2 Pro")

    def test_loaded_kexts_captured(self):
        self.assertIn("com.apple.filesystems.apfs", self.r.loaded_kexts)
        self.assertEqual(len(self.r.loaded_kexts), 5)

    def test_backtrace_lrs(self):
        self.assertIn("0xfffffe0037230464", self.r.backtrace_lrs)


# ---------------------------------------------------------------------------
# Block 3 — third-party kext detection (the "not a driver" proof)
# ---------------------------------------------------------------------------


class TestThirdPartyKext(unittest.TestCase):
    def test_all_apple_means_zero_third_party(self):
        r = parse_panic(MACOS_PANIC)
        self.assertEqual(r.third_party_kexts, [])

    def test_injected_third_party_is_detected(self):
        r = parse_panic(PANIC_WITH_THIRD_PARTY)
        self.assertEqual(r.third_party_kexts, ["org.virtualbox.kext.VBoxDrv"])


# ---------------------------------------------------------------------------
# Block 4 — parse_traceback
# ---------------------------------------------------------------------------


class TestParseTraceback(unittest.TestCase):
    def setUp(self):
        self.t = parse_traceback(PY_TRACEBACK)

    def test_exception_type_and_message(self):
        self.assertEqual(self.t.exception_type, "KeyError")
        self.assertEqual(self.t.exception_message, "'user'")

    def test_frame_count(self):
        self.assertEqual(len(self.t.frames), 3)

    def test_crash_frame_is_deepest(self):
        self.assertEqual(self.t.crash_frame.file, "/srv/app/handlers.py")
        self.assertEqual(self.t.crash_frame.line, 41)

    def test_root_frame_is_entrypoint(self):
        self.assertEqual(self.t.root_frame.file, "/srv/app/worker.py")
        self.assertEqual(self.t.root_frame.line, 12)


# ---------------------------------------------------------------------------
# Block 5 — karpathy_gate (a claim ships only with a resolvable anchor)
# ---------------------------------------------------------------------------


class TestKarpathyGate(unittest.TestCase):
    def test_no_anchor_fails(self):
        v = karpathy_gate([Claim("the bug is a leak", None)])
        self.assertEqual(v.status, "FAIL")
        self.assertIn("the bug is a leak", v.unproven)

    def test_resolvable_file_anchor_passes(self):
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
            fh.write("line1\nline2\nline3\n")
            path = fh.name
        try:
            v = karpathy_gate([Claim("see impl", Anchor("file", f"{path}:2"))])
            self.assertEqual(v.status, "PASS")
            self.assertEqual(v.unproven, [])
        finally:
            os.unlink(path)

    def test_file_line_beyond_eof_fails(self):
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
            fh.write("only one line\n")
            path = fh.name
        try:
            v = karpathy_gate([Claim("see line 99", Anchor("file", f"{path}:99"))])
            self.assertEqual(v.status, "FAIL")
        finally:
            os.unlink(path)

    def test_missing_file_anchor_fails(self):
        v = karpathy_gate(
            [Claim("x", Anchor("file", "/no/such/path/zzz.py"))]
        )
        self.assertEqual(v.status, "FAIL")

    def test_command_anchor_syntax_checked(self):
        ok = karpathy_gate([Claim("run it", Anchor("command", "echo hi"))])
        self.assertEqual(ok.status, "PASS")
        # unparseable shell quoting → FAIL
        bad = karpathy_gate([Claim("run it", Anchor("command", 'a "unterminated'))])
        self.assertEqual(bad.status, "FAIL")

    def test_command_anchor_rejects_substitution_no_exec(self):
        # Must NOT execute. A canary file proves the substitution never ran.
        canary = tempfile.mktemp()
        try:
            v = karpathy_gate(
                [Claim("x", Anchor("command", f"echo $(touch {canary})"))]
            )
            self.assertEqual(v.status, "FAIL")
            self.assertFalse(os.path.exists(canary), "command substitution executed!")
        finally:
            if os.path.exists(canary):
                os.unlink(canary)

    def test_unknown_anchor_kind_fails(self):
        v = karpathy_gate([Claim("x", Anchor("mystery", "whatever"))])
        self.assertEqual(v.status, "FAIL")


# ---------------------------------------------------------------------------
# Block 6 — stdlib only (mirrors test_whats_new TestStdlibOnly)
# ---------------------------------------------------------------------------


class TestStdlibOnly(unittest.TestCase):
    def test_no_third_party_imports(self):
        src = (Path(__file__).resolve().parent.parent / "bug_investigator.py").read_text()
        tree = ast.parse(src)
        allowed = {
            "__future__", "argparse", "dataclasses", "enum", "re", "sys",
            "json", "pathlib", "typing", "shlex", "shutil", "os",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    self.assertIn(n.name.split(".")[0], allowed, n.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.assertIn(node.module.split(".")[0], allowed, node.module)


# ---------------------------------------------------------------------------
# Block 7 — review-fix coverage (Layer-2 findings)
# ---------------------------------------------------------------------------

PYTEST_FAILURE = """\
=================================== FAILURES ===================================
_________________________________ test_add ____________________________________
    def test_add():
>       assert add(2, 2) == 5
E       assert 4 == 5
tests/test_math.py:4: AssertionError
=========================== short test summary info ============================
FAILED tests/test_math.py::test_add - assert 4 == 5
"""


class TestReviewFixes(unittest.TestCase):
    def test_classify_empty_is_unknown(self):
        self.assertEqual(classify_input(""), InputKind.UNKNOWN)
        self.assertEqual(classify_input("   \n  "), InputKind.UNKNOWN)

    def test_classify_pytest_failure(self):
        self.assertEqual(classify_input(PYTEST_FAILURE), InputKind.TEST_FAILURE)

    def test_soc_code_non_4_digit_falls_back(self):
        raw = MACOS_PANIC.replace("RELEASE_ARM64_T6020", "RELEASE_ARM64_T60441")
        r = parse_panic(raw)
        self.assertEqual(r.hardware_model, "Apple Silicon (T60441)")

    def test_unknown_darwin_major_yields_none_name(self):
        raw = MACOS_PANIC.replace("Darwin Kernel Version 25.3.0", "Darwin Kernel Version 9.8.0")
        r = parse_panic(raw)
        self.assertEqual(r.darwin_version, "9.8.0")
        self.assertIsNone(r.macos_name)

    def test_kext_list_survives_blank_line_gap(self):
        raw = MACOS_PANIC.replace(
            "com.apple.iokit.IOPCIFamily    2.9\n",
            "com.apple.iokit.IOPCIFamily    2.9\n\ncom.apple.kec.pthread    1\n",
        )
        r = parse_panic(raw)
        self.assertIn("com.apple.kec.pthread", r.loaded_kexts)
        self.assertIn("com.apple.kec.corecrypto", r.loaded_kexts)

    def test_kext_list_stops_at_non_kext_line(self):
        raw = MACOS_PANIC + "\nSystem Profile:\nthis is not a kext line at all\n"
        r = parse_panic(raw)
        self.assertNotIn("System", r.loaded_kexts)
        self.assertNotIn("this", r.loaded_kexts)

    def test_bare_custom_exception_name(self):
        tb = (
            'Traceback (most recent call last):\n'
            '  File "/a.py", line 2, in <module>\n'
            '    lookup()\n'
            'UserNotFound: no such user\n'
        )
        t = parse_traceback(tb)
        self.assertEqual(t.exception_type, "UserNotFound")
        self.assertEqual(t.exception_message, "no such user")

    def test_redact_secrets(self):
        s = (
            "db=postgres://admin:s3cr3tpw@db.host/app "
            "auth=Bearer sk-ABCDEF123456 key=AKIAIOSFODNN7EXAMPLE "
            "password=hunter2"
        )
        out = redact_secrets(s)
        self.assertNotIn("s3cr3tpw", out)
        self.assertNotIn("sk-ABCDEF123456", out)
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", out)
        self.assertNotIn("hunter2", out)
        self.assertIn("postgres://admin:", out)  # structure kept, secret gone

    def test_cli_bad_path_returns_1(self):
        rc = main(["/no/such/file/zzz.log"])
        self.assertEqual(rc, 1)

    def test_cli_directory_arg_returns_1(self):
        rc = main([str(Path(__file__).resolve().parent)])
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
