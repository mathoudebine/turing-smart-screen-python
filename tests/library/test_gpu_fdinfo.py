# SPDX-License-Identifier: GPL-3.0-or-later

import math

from library.sensors import gpu_fdinfo, sensors_python


def test_engine_counter_sums_amdgpu_engines_and_ignores_capacity():
    parsed = gpu_fdinfo._engine_counter(
        "drm-driver:\tamdgpu\n"
        "drm-client-id:\t7\n"
        "drm-engine-gfx:\t200 ns\n"
        "drm-engine-compute:\t300 ns\n"
        "drm-engine-capacity-gfx:\t2\n"
    )

    assert parsed == ("7", 500)
    assert gpu_fdinfo._engine_counter("drm-driver:\ti915\ndrm-engine-render:\t1 ns") is None


def test_busy_percent_uses_deltas_and_deduplicates_client_fds(tmp_path):
    proc = tmp_path / "proc"
    fd_dir = proc / "123" / "fd"
    fdinfo_dir = proc / "123" / "fdinfo"
    fd_dir.mkdir(parents=True)
    fdinfo_dir.mkdir(parents=True)
    (proc / "uptime").write_text("5000.0 0.0\n", encoding="ascii")
    (proc / "123" / "stat").write_text(
        "123 (game) S " + " ".join(["0"] * 19 + ["100"]),
        encoding="ascii",
    )
    (fd_dir / "3").symlink_to("/dev/dri/renderD128")
    (fd_dir / "4").symlink_to("/dev/dri/renderD128")
    first_fdinfo = fdinfo_dir / "3"
    duplicate_fdinfo = fdinfo_dir / "4"
    initial = "drm-driver:\tamdgpu\ndrm-client-id:\t7\ndrm-engine-gfx:\t0 ns\n"
    first_fdinfo.write_text(initial, encoding="ascii")
    duplicate_fdinfo.write_text(initial, encoding="ascii")

    monotonic_ns = iter((1_000_000_000, 2_000_000_000))
    sampler = gpu_fdinfo.DrmFdinfoSampler(
        proc=proc,
        clock=lambda: 1000.0,
        clock_ns=lambda: next(monotonic_ns),
    )

    assert sampler.busy_percent() is None

    updated = "drm-driver:\tamdgpu\ndrm-client-id:\t7\ndrm-engine-gfx:\t500000000 ns\n"
    first_fdinfo.write_text(updated, encoding="ascii")
    duplicate_fdinfo.write_text(updated, encoding="ascii")

    assert sampler.busy_percent() == 50.0


def test_busy_percent_is_unavailable_without_shared_clients():
    ticks = iter((1_000_000_000, 2_000_000_000))
    samples = iter(({}, {"new-client": 500_000_000}))
    sampler = gpu_fdinfo.DrmFdinfoSampler(clock_ns=lambda: next(ticks))
    sampler.sample = lambda: next(samples)

    assert sampler.busy_percent() is None
    assert sampler.busy_percent() is None


def test_amd_gpu_load_prefers_valid_sysfs_value(monkeypatch):
    monkeypatch.setattr(
        sensors_python.GpuAmd,
        "_sysfs_gpu_busy_percent",
        staticmethod(lambda: 73.0),
    )
    monkeypatch.setattr(
        sensors_python.GpuAmd._fdinfo_sampler,
        "busy_percent",
        lambda: (_ for _ in ()).throw(AssertionError("fdinfo should not be read")),
    )

    assert sensors_python.GpuAmd._gpu_load() == 73.0


def test_amd_stats_returns_fdinfo_load_without_optional_bindings(monkeypatch):
    monkeypatch.setattr(sensors_python, "pyamdgpuinfo", None)
    monkeypatch.setattr(sensors_python, "pyadl", None)
    monkeypatch.setattr(
        sensors_python.GpuAmd,
        "_gpu_load",
        staticmethod(lambda amd_gpu=None: 42.0),
    )

    stats = sensors_python.GpuAmd.stats()
    assert stats[0] == 42.0
    assert all(math.isnan(value) for value in stats[1:])


def test_amd_detection_warms_fdinfo_baseline_when_sysfs_load_is_unavailable(monkeypatch):
    class BrokenAmdgpuinfo:
        @staticmethod
        def detect_gpus():
            raise RuntimeError("unsupported ASIC")

    sampler_calls = []
    monkeypatch.setattr(sensors_python, "pyamdgpuinfo", BrokenAmdgpuinfo)
    monkeypatch.setattr(sensors_python, "pyadl", None)
    monkeypatch.setattr(
        sensors_python.GpuAmd,
        "_amdgpu_sysfs_devices",
        staticmethod(lambda: ["/sys/class/drm/card0/device"]),
    )
    monkeypatch.setattr(
        sensors_python.GpuAmd,
        "_sysfs_gpu_busy_percent",
        staticmethod(lambda: math.nan),
    )
    monkeypatch.setattr(
        sensors_python.GpuAmd._fdinfo_sampler,
        "sample",
        lambda: sampler_calls.append(True),
    )

    assert sensors_python.GpuAmd.is_available()
    assert sampler_calls == [True]