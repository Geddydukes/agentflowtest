from pathlib import Path
from typing import List, Dict, Any
from jinja2 import Environment, FileSystemLoader

from agentft.core.result import EvaluationResult
from agentft.core.metadata import RunMetadata
from agentft.reporting.summary import build_summary


def generate_html_report(
    metadata: RunMetadata,
    results: List[EvaluationResult],
    output_path: str,
) -> None:
    """Generate an HTML report from metadata and results."""
    template_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("report.html.j2")

    summary = build_summary(results)

    html_content = template.render(
        metadata=metadata,
        summary=summary,
        results=results,
    )

    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path_obj, "w") as f:
        f.write(html_content)

