import time

from aim.sdk.bench import DistStatCollector

disk_stats_collector = DistStatCollector('./test.csv')
disk_stats_collector.collect()
time.sleep(2)
