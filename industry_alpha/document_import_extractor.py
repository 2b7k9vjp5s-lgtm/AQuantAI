"""Bounded embedded-text-only PDF extraction in a synchronous child process."""

from __future__ import annotations

import multiprocessing as mp
import os
from hashlib import sha256
from io import BytesIO
from typing import Any

from industry_alpha.document_import_contracts import (
    DocumentImportError,
    ExtractedPage,
    ExtractionResult,
)
from industry_alpha.document_import_rules import (
    MAX_DECODED_DOCUMENT_BYTES,
    MAX_DECODED_PAGE_BYTES,
    MAX_DOCUMENT_CHARACTERS,
    MAX_INPUT_BYTES,
    MAX_PAGE_CHARACTERS,
    MAX_PAGES,
    MAX_WORKER_MEMORY_BYTES,
    sha256_hex,
)


def _install_posix_limit() -> bool:
    try:
        import resource

        resource.setrlimit(
            resource.RLIMIT_AS,
            (MAX_WORKER_MEMORY_BYTES, MAX_WORKER_MEMORY_BYTES),
        )
        return True
    except (ImportError, OSError, ValueError):
        return False


def _install_windows_limit() -> bool:
    if os.name != "nt":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x100
        JobObjectExtendedLimitInformation = 9

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in (
                "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
            )]

        class BASIC_LIMIT(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class EXTENDED_LIMIT(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", BASIC_LIMIT),
                ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return False
        info = EXTENDED_LIMIT()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_PROCESS_MEMORY
        info.ProcessMemoryLimit = MAX_WORKER_MEMORY_BYTES
        if not kernel32.SetInformationJobObject(
            job,
            JobObjectExtendedLimitInformation,
            ctypes.byref(info),
            ctypes.sizeof(info),
        ):
            kernel32.CloseHandle(job)
            return False
        if not kernel32.AssignProcessToJobObject(job, kernel32.GetCurrentProcess()):
            kernel32.CloseHandle(job)
            return False
        globals()["_WINDOWS_JOB_HANDLE"] = job
        return True
    except (AttributeError, OSError, ValueError):
        return False


def _extract_worker(connection: Any, raw_pdf_bytes: bytes) -> None:
    try:
        if not (_install_posix_limit() or _install_windows_limit()):
            connection.send((False, "extractor_resource_limit", None))
            return
        import pypdf
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(raw_pdf_bytes), strict=True, password=None)
        if reader.is_encrypted:
            connection.send((False, "encrypted_pdf_unsupported", None))
            return
        page_count = len(reader.pages)
        if not 1 <= page_count <= MAX_PAGES:
            connection.send((False, "page_count_out_of_range", None))
            return
        decoded_total = 0
        text_total = 0
        embedded_pages = 0
        output: list[tuple[int, str, str, int]] = []
        for number, page in enumerate(reader.pages, start=1):
            contents = page.get_contents()
            decoded = contents.get_data() if contents is not None else b""
            decoded_total += len(decoded)
            if len(decoded) > MAX_DECODED_PAGE_BYTES or decoded_total > MAX_DECODED_DOCUMENT_BYTES:
                connection.send((False, "decoded_content_stream_too_large", None))
                return
            text = page.extract_text(extraction_mode="plain") or ""
            if len(text) > MAX_PAGE_CHARACTERS:
                connection.send((False, "page_text_too_large", None))
                return
            text_total += len(text)
            if text_total > MAX_DOCUMENT_CHARACTERS:
                connection.send((False, "document_text_too_large", None))
                return
            if text.strip():
                embedded_pages += 1
            output.append((number, text, sha256(text.encode("utf-8")).hexdigest(), len(text)))
        if embedded_pages == 0:
            connection.send((False, "embedded_text_unavailable", None))
            return
        connection.send(
            (
                True,
                None,
                {
                    "pages": output,
                    "embedded_pages": embedded_pages,
                    "text_total": text_total,
                    "version": pypdf.__version__,
                },
            )
        )
    except MemoryError:
        connection.send((False, "extractor_resource_limit", None))
    except BaseException:
        connection.send((False, "malformed_pdf", None))
    finally:
        connection.close()


def extract_pdf(raw_pdf_bytes: bytes, *, timeout_seconds: float = 30.0) -> ExtractionResult:
    if not raw_pdf_bytes:
        raise DocumentImportError("invalid_pdf_signature")
    if len(raw_pdf_bytes) > MAX_INPUT_BYTES:
        raise DocumentImportError("file_too_large")
    if not raw_pdf_bytes.startswith(b"%PDF-"):
        raise DocumentImportError("invalid_pdf_signature")
    context = mp.get_context("spawn")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=_extract_worker, args=(child, raw_pdf_bytes), daemon=True)
    process.start()
    child.close()
    if not parent.poll(timeout_seconds):
        process.terminate()
        process.join(5)
        parent.close()
        raise DocumentImportError("extractor_timeout")
    try:
        success, code, payload = parent.recv()
    except EOFError as exc:
        raise DocumentImportError("extractor_resource_limit") from exc
    finally:
        parent.close()
        process.join(5)
        if process.is_alive():
            process.kill()
            process.join(5)
    if not success:
        raise DocumentImportError(str(code or "extractor_failure"))
    assert isinstance(payload, dict)
    pages = tuple(
        ExtractedPage(
            page_number=item[0],
            text=item[1],
            text_sha256=item[2],
            text_char_count=item[3],
        )
        for item in payload["pages"]
    )
    return ExtractionResult(
        content_sha256=sha256_hex(raw_pdf_bytes),
        byte_size=len(raw_pdf_bytes),
        pages=pages,
        embedded_text_page_count=int(payload["embedded_pages"]),
        total_text_char_count=int(payload["text_total"]),
        extractor_package="pypdf",
        extractor_version=str(payload["version"]),
    )
