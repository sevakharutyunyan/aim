import collections
import csv
import functools
import os
import queue
import threading
import datetime
from os import path
import inspect
from aim.engine.aim_repo import AimRepo
from aim.sdk.artifacts.serializable import Serializable
from aim.sdk.artifacts import *

import aim.sdk.init


def get_track_names():
    all_names = dir(aim.sdk.artifacts)
    return [name for name in all_names if
            name[0].isupper() and
            inspect.isclass(globals()[name]) and
            issubclass(globals()[name], aim.sdk.artifacts.Serializable)]


def get_delta_ms(delta):
    return delta / datetime.timedelta(microseconds=1)


class DistStatCollector:
    def __init__(self, results_path):
        aim.sdk.init(overwrite=True)

        self.queue = queue.Queue()
        repo = AimRepo.get_working_repo()
        assert repo is not None, "Cannot find aim repo, please initialize it first"
        self.repo_path = repo.path
        self.results_path = results_path
        self.tracks_calls = collections.Counter()
        self.track_names = get_track_names()

        t = threading.Thread(target=self._collect_stats)
        t.daemon = True
        t.start()

    def wrap_track(self, track):
        @functools.wraps(track)
        def wrapper(*args, **kwds):
            name = args[0]
            if name in self.track_names:
                self.tracks_calls[name] += 1

            return track(*args, **kwds)

        return wrapper

    def collect(self):
        self.queue.put(None)

    def _collect_stats(self):
        disk_stats = DiskStat(self.repo_path)

        print("Initial disk Usage = %10.2fKBi\tFile count = %10d" % (
            disk_stats.initial_usage / 1024., disk_stats.initial_file_count))

        with open(self.results_path, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['Time', 'Usage in bytes', 'Files count', 'Total track calls'] +
                       ['Track:' + n for n in self.track_names])
            start_time = datetime.datetime.now()

            while True:
                self.queue.get()
                file_count, disk_usage = disk_stats.stats()
                total_track_calls = sum(self.tracks_calls.values())

                print(
                    "Disk Usage: %10.2fKBi\tFile count: %10d\tTotal tracks calls: %4d" %
                    (disk_usage / 1024., file_count, total_track_calls)
                )

                w.writerow(
                    [get_delta_ms(datetime.datetime.now() - start_time), disk_usage, file_count, total_track_calls] +
                    [self.tracks_calls[n] for n in self.track_names]
                )
                f.flush()
                self.queue.task_done()


class DiskStat:
    def __init__(self, root_path):
        self.path = root_path
        self.initial_file_count, self.initial_usage = self.stats()

    def stats(self):
        count = 0
        usage = 0
        for root, dirs, files in os.walk(self.path):
            count += len(files) + len(dirs)
            for file in files:
                usage += path.getsize(path.join(root, file))

        return count, usage
