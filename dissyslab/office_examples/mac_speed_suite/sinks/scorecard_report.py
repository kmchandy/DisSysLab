"""
---
emits: report.html, the full scorecard of the run
---
Arguments: path (default "report.html"), title.
"""

from _report_html import ReportHtmlSink


class ScorecardReport(ReportHtmlSink):
    def __call__(self, msg):
        self.run(msg["scorecard"])
        print(f"Scorecard written to {self.path}")
