"""
Module to usefully present results in the form of an interactive
html-report downloadable by participants.
"""

    
from datetime import datetime
from html import escape
from collections import Counter, defaultdict
from typing import Any


class AlgorithmSubmissionReport:
    """
    AI Disclaimer: The report generation has been created by AI to a substantial extend.
    """

    def __init__(self, results: dict[str, dict[str, float]], universal_metrics: dict[str, float], issues: list[dict]):
        self.results = results
        self.universal_metrics = universal_metrics
        self.issues = issues

        self.html: str = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <title>Evaluation Report</title>

                <style>
                    body {
                        font-family: Arial, sans-serif;
                        margin: 40px;
                        color: #222;
                    }

                    h1 {
                        border-bottom: 2px solid #444;
                        padding-bottom: 10px;
                    }

                    h2 {
                        margin-top: 40px;
                        border-bottom: 1px solid #ccc;
                        padding-bottom: 6px;
                    }

                    table {
                        border-collapse: collapse;
                        width: 100%;
                        margin-top: 10px;
                    }

                    th, td {
                        border: 1px solid #ddd;
                        padding: 8px;
                        text-align: left;
                    }

                    th {
                        background: #f4f4f4;
                    }

                    .ok {
                        color: green;
                        font-weight: bold;
                    }

                    /* Accordion styling */
                    .accordion-item {
                        border: 1px solid #ddd;
                        border-radius: 6px;
                        margin-bottom: 10px;
                        overflow: hidden;
                    }

                    .accordion-header {
                        width: 100%;
                        background: #f7f7f7;
                        border: none;
                        padding: 12px;
                        text-align: left;
                        font-size: 14px;
                        cursor: pointer;

                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    }

                    .accordion-header:hover {
                        background: #eee;
                    }

                    .accordion-content {
                        display: none;
                        padding: 10px;
                        background: white;
                    }

                    .arrow {
                        transition: transform 0.2s ease;
                    }

                    .accordion-item.active .accordion-content {
                        display: block;
                    }

                    .accordion-item.active .arrow {
                        transform: rotate(90deg);
                    }

                    .controls {
                        margin: 10px 0 20px 0;
                    }

                    .controls button {
                        margin-right: 10px;
                        padding: 6px 10px;
                        cursor: pointer;
                    }
                    .issue-section-good {
                        background: #f1fbf1;
                        border: 1px solid #cce5cc;
                        border-radius: 8px;
                        padding: 20px;
                    }

                    .issue-section-bad {
                        background: #fff2f2;
                        border: 1px solid #f0c4c4;
                        border-radius: 8px;
                        padding: 20px;
                    }

                    .issue-card {
                        border: 1px solid #ddd;
                        border-radius: 6px;
                        margin-bottom: 10px;
                        overflow: hidden;
                    }

                    .issue-header {
                        width: 100%;
                        background: #fafafa;
                        border: none;
                        padding: 12px;
                        text-align: left;
                        cursor: pointer;

                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    }

                    .issue-header:hover {
                        background: #eee;
                    }

                    .issue-content {
                        display: none;
                        padding: 15px;
                        background: white;
                    }

                    .issue-card.active .issue-content {
                        display: block;
                    }

                    .issue-card.active .arrow {
                        transform: rotate(90deg);
                    }

                    .issue-property {
                        margin-bottom: 8px;
                    }

                    .issue-property b {
                        display: inline-block;
                        width: 100px;
                    }
                    .summary-cards {
                        display: flex;
                        flex-wrap: wrap;
                        gap: 15px;
                        margin-bottom: 25px;
                    }

                    .summary-card {
                        flex: 1;
                        min-width: 180px;
                        background: #fafafa;
                        border: 1px solid #ddd;
                        border-radius: 8px;
                        padding: 15px;
                    }

                    .summary-card-title {
                        font-size: 0.9em;
                        color: #666;
                        margin-bottom: 8px;
                    }

                    .summary-card-value {
                        font-size: 1.8em;
                        font-weight: bold;
                        color: #333;
                    }
                </style>
            </head>
        """
    
    @staticmethod
    def _fmt(v: Any) -> Any | float:
        if isinstance(v, float):
            return f"{v:.4f}"
        return str(v)
    
    @staticmethod
    def _aggregate_by_key(items: list[dict], key: str) -> tuple[Counter, defaultdict]:
        """
        Aggregate level details on validation results

        Args:
            items (list[dict]): warning or errors
            key (str): by which key to aggregate

        Returns:
            tuple[Counter, defaultdict]: category counts and grouped items by category
        """
        counter: Counter = Counter()
        grouped: defaultdict = defaultdict(list)

        for item in items:
            res: str = item[key]
            counter[res] += 1
            grouped[res].append(item)

        return counter, grouped
    
    def build_issues_section(self) -> str:

        if len(self.issues) == 0:
            return """
            <section class="issue-section-good">
                <h2>Warnings & Errors</h2>
                <p class="ok">No issues detected.</p>
            </section>
            """

        severity_counter, severity_grouped = self._aggregate_by_key(
            self.issues,
            key="severity"
        )

        has_errors: bool = severity_counter.get("error", 0) > 0

        section_class = (
            "issue-section-bad"
            if has_errors
            else "issue-section-good"
        )

        # ---------- severity summary ----------
        severity_rows = "\n".join(
            f"""
            <tr>
                <td>{escape(severity)}</td>
                <td>{count}</td>
            </tr>
            """
            for severity, count in severity_counter.items()
        )

        # ---------- code summary ----------
        code_rows = []

        for severity, issues in severity_grouped.items():

            code_counter, _ = self._aggregate_by_key(
                issues,
                key="code"
            )

            for code, count in code_counter.items():
                code_rows.append(
                    f"""
                    <tr>
                        <td>{escape(severity)}</td>
                        <td>{escape(code)}</td>
                        <td>{count}</td>
                    </tr>
                    """
                )

        code_rows = "\n".join(code_rows)

        # ---------- individual issue cards ----------
        issue_cards = []

        for i in self.issues:

            severity = escape(i.get("severity", "unknown"))
            code = escape(i.get("code", ""))
            location = escape(i.get("location", ""))
            message = escape(i.get("issueMessage", ""))

            issue_cards.append(
                f"""
                <div class="issue-card">
                    <button class="issue-header"
                            onclick="toggleIssue(this)">
                        <span>
                            [{severity.upper()}] {location}
                        </span>
                        <span class="arrow">▶</span>
                    </button>

                    <div class="issue-content">

                        <div class="issue-property">
                            <b>Severity:</b> {severity}
                        </div>

                        <div class="issue-property">
                            <b>Code:</b> {code}
                        </div>

                        <div class="issue-property">
                            <b>Location:</b>
                            <br>
                            {location}
                        </div>

                        <div class="issue-property">
                            <b>Description:</b>
                            <br>
                            {message}
                        </div>

                    </div>
                </div>
                """
            )

        issue_cards = "\n".join(issue_cards)

        return f"""
        <section class="{section_class}">

            <h2>Warnings & Errors</h2>

            <h3>Summary by Severity</h3>

            <table>
                <thead>
                    <tr>
                        <th>Severity</th>
                        <th>Count</th>
                    </tr>
                </thead>
                <tbody>
                    {severity_rows}
                </tbody>
            </table>

            <h3>Summary by Code</h3>

            <table>
                <thead>
                    <tr>
                        <th>Severity</th>
                        <th>Code</th>
                        <th>Count</th>
                    </tr>
                </thead>
                <tbody>
                    {code_rows}
                </tbody>
            </table>

            <h3>Detailed Issues</h3>

            {issue_cards}

        </section>
        """
    
    def build_universal_section(self):
        metadata: dict[str, Any] = {
            "predictions_scored": len(self.results),
            "accepted_units_total": sum(
                x["accepted_units"]
                for x in self.results.values()
            ),
            "rejected_units_total": sum(
                x["rejected_units"]
                for x in self.results.values()
            )
        }
        
        rows: str = "\n".join(
            f"<tr><td>{escape(k)}</td><td>{self._fmt(v)}</td></tr>"
            for k, v in self.universal_metrics.items()
        )

        cards: str = f"""
            <div class="summary-cards">

                <div class="summary-card">
                    <div class="summary-card-title">
                        Predictions scored
                    </div>
                    <div class="summary-card-value">
                        {metadata["predictions_scored"]}
                    </div>
                </div>

                <div class="summary-card">
                    <div class="summary-card-title">
                        Accepted units
                    </div>
                    <div class="summary-card-value">
                        {metadata["accepted_units_total"]}
                    </div>
                </div>

                <div class="summary-card">
                    <div class="summary-card-title">
                        Rejected units
                    </div>
                    <div class="summary-card-value">
                        {metadata["rejected_units_total"]}
                    </div>
                </div>

            </div>
            """

        return f"""
            <section>
                <h2>Universal Results</h2>

                {cards}

                <h3>Performance Metrics</h3>

                <table>
                    <thead>
                        <tr>
                            <th>Metric</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
            </section>
            """
    
    def build_file_accordion(self):
        blocks: list[str] = []

        for idx, fname in enumerate(sorted(self.results.keys())):
            metrics: dict[str, float] = self.results[fname]

            metric_rows = "\n".join(
                f"<tr><td>{escape(k)}</td><td>{self._fmt(v)}</td></tr>"
                for k, v in metrics.items()
            )

            blocks.append(f"""
                <div class="accordion-item">
                    <button class="accordion-header" onclick="toggleAccordion(this)">
                        <span>{escape(fname)}</span>
                        <span class="arrow">▶</span>
                    </button>

                    <div class="accordion-content">
                        <table>
                            <thead>
                                <tr><th>Metric</th><th>Value</th></tr>
                            </thead>
                            <tbody>
                                {metric_rows}
                            </tbody>
                        </table>
                    </div>
                </div>
            """)

        return "\n".join(blocks)
    
    def generate_report(self) -> None:
        self.html += f"""
            <body>

                <h1>Evaluation Report</h1>
                <p>Generated: {datetime.now().isoformat()}</p>

                {self.build_universal_section()}

                {self.build_issues_section()}

                <section>
                    <h2>File-level Results</h2>
                    {self.build_file_accordion()}
                </section>

                <script>
                    function toggleAccordion(btn) {{
                        const item = btn.parentElement;
                        item.classList.toggle("active");
                    }}
                    function toggleIssue(btn) {{
                        const item = btn.parentElement;
                        item.classList.toggle("active");
                    }}
                </script>

            </body>
        </html>
        """

    def save_html_report(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.html)
