from typing import Dict, Any

class PerformanceReporter:
    @staticmethod
    def print_performance_report(results: Dict[str, Any]) -> str:
        """Formats the run statistics into a clean text console summary."""
        report = []
        report.append("==================================================")
        report.append("          D DAP LOAD RESILIENCE REPORT            ")
        report.append("==================================================")
        report.append(f"Total Requests Processed: {results['totalRequests']}")
        report.append(f"Throughput (TPS)        : {results['tps']} req/sec")
        report.append("--------------------------------------------------")
        report.append(f"P50 Latency (median)    : {results['p50']} ms")
        report.append(f"P90 Latency             : {results['p90']} ms")
        report.append(f"P95 Latency             : {results['p95']} ms")
        report.append(f"P99 Latency             : {results['p99']} ms")
        report.append(f"Cache Hit Ratio         : {results['cacheHitRatioPct']}%")
        report.append("==================================================")
        return "\n".join(report)

performance_reporter = PerformanceReporter()
