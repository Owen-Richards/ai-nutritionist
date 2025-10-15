"""
Prompt Evaluation Harness

Provides systematic evaluation of prompts across multiple metrics with
reporting, comparison, and A/B testing support.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from .metrics import EvaluationMetric, MetricResult


class EvaluationReport(BaseModel):
    """
    Comprehensive report from prompt evaluation.
    
    Aggregates results from multiple metrics and provides
    pass/fail determination and recommendations.
    """
    
    prompt_name: str = Field(..., description="Template name")
    prompt_version: str = Field(..., description="Template version")
    prompt_hash: str = Field(..., description="Template content hash")
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Test inputs
    test_context: Dict[str, Any] = Field(..., description="Context used for rendering")
    rendered_prompt: str = Field(..., description="Actual prompt sent to LLM")
    llm_response: str = Field(..., description="LLM response received")
    llm_metadata: Dict[str, Any] = Field(default_factory=dict, description="API metadata")
    
    # Evaluation results
    metric_results: List[MetricResult] = Field(default_factory=list)
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Weighted average score")
    passed: bool = Field(..., description="All critical metrics passed")
    
    # Summary statistics
    total_metrics: int = Field(..., description="Number of metrics evaluated")
    passed_metrics: int = Field(..., description="Number of metrics that passed")
    failed_metrics: int = Field(..., description="Number of metrics that failed")
    
    # Recommendations
    warnings: List[str] = Field(default_factory=list, description="Non-critical issues")
    errors: List[str] = Field(default_factory=list, description="Critical failures")
    
    @classmethod
    def from_results(
        cls,
        prompt_name: str,
        prompt_version: str,
        prompt_hash: str,
        test_context: Dict[str, Any],
        rendered_prompt: str,
        llm_response: str,
        llm_metadata: Dict[str, Any],
        metric_results: List[MetricResult],
        metric_weights: Optional[Dict[str, float]] = None,
    ) -> "EvaluationReport":
        """
        Create report from metric results.
        
        Args:
            prompt_name: Template name
            prompt_version: Template version
            prompt_hash: Template content hash
            test_context: Context used for rendering
            rendered_prompt: Rendered prompt string
            llm_response: LLM's response
            llm_metadata: Metadata from LLM API
            metric_results: Results from all metrics
            metric_weights: Optional weights for scoring (default: equal weights)
        
        Returns:
            Populated EvaluationReport
        """
        weights = metric_weights or {}
        total_weight = 0.0
        weighted_score = 0.0
        
        passed_count = 0
        failed_count = 0
        warnings = []
        errors = []
        
        for result in metric_results:
            weight = weights.get(result.metric_name, 1.0)
            total_weight += weight
            weighted_score += result.score * weight
            
            if result.passed:
                passed_count += 1
            else:
                failed_count += 1
                if result.score < 0.5:
                    errors.append(
                        f"{result.metric_name}: Critical failure (score={result.score:.2f})"
                    )
                else:
                    warnings.append(
                        f"{result.metric_name}: Below threshold (score={result.score:.2f})"
                    )
        
        overall_score = weighted_score / total_weight if total_weight > 0 else 0.0
        
        # Determine overall pass/fail
        # Pass only if no errors and overall score is acceptable
        passed = len(errors) == 0 and overall_score >= 0.7
        
        return cls(
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            prompt_hash=prompt_hash,
            test_context=test_context,
            rendered_prompt=rendered_prompt,
            llm_response=llm_response,
            llm_metadata=llm_metadata,
            metric_results=metric_results,
            overall_score=overall_score,
            passed=passed,
            total_metrics=len(metric_results),
            passed_metrics=passed_count,
            failed_metrics=failed_count,
            warnings=warnings,
            errors=errors,
        )
    
    def summary(self) -> str:
        """Generate human-readable summary."""
        status = "✅ PASSED" if self.passed else "❌ FAILED"
        
        lines = [
            f"\n{'=' * 60}",
            f"Prompt Evaluation Report: {self.prompt_name}@{self.prompt_version}",
            f"{'=' * 60}",
            f"Status: {status}",
            f"Overall Score: {self.overall_score:.2%}",
            f"Metrics: {self.passed_metrics}/{self.total_metrics} passed",
            "",
        ]
        
        if self.errors:
            lines.append("🚨 ERRORS:")
            for error in self.errors:
                lines.append(f"  • {error}")
            lines.append("")
        
        if self.warnings:
            lines.append("⚠️  WARNINGS:")
            for warning in self.warnings:
                lines.append(f"  • {warning}")
            lines.append("")
        
        lines.append("📊 METRIC DETAILS:")
        for result in self.metric_results:
            status_icon = "✅" if result.passed else "❌"
            lines.append(
                f"  {status_icon} {result.metric_name}: "
                f"{result.score:.2%} (threshold: {result.threshold:.2%})"
            )
        
        lines.append(f"\n{'=' * 60}\n")
        
        return "\n".join(lines)


@dataclass
class PromptEvaluator:
    """
    Harness for evaluating prompts against multiple metrics.
    
    Supports:
    - Single-shot evaluation with custom metrics
    - A/B testing between prompt versions
    - Batch evaluation across test cases
    - Custom metric weighting
    """
    
    metrics: List[EvaluationMetric] = field(default_factory=list)
    metric_weights: Dict[str, float] = field(default_factory=dict)
    
    def add_metric(self, metric: EvaluationMetric, weight: float = 1.0) -> None:
        """
        Add a metric to the evaluation suite.
        
        Args:
            metric: Metric instance
            weight: Relative weight for overall scoring (default: 1.0)
        """
        self.metrics.append(metric)
        self.metric_weights[metric.name] = weight
    
    async def evaluate(
        self,
        prompt_name: str,
        prompt_version: str,
        prompt_hash: str,
        test_context: Dict[str, Any],
        rendered_prompt: str,
        llm_response: str,
        llm_metadata: Optional[Dict[str, Any]] = None,
    ) -> EvaluationReport:
        """
        Evaluate a prompt-response pair against all metrics.
        
        Args:
            prompt_name: Template name
            prompt_version: Template version
            prompt_hash: Template content hash
            test_context: Context used for rendering
            rendered_prompt: Rendered prompt string
            llm_response: LLM's response
            llm_metadata: Optional metadata from LLM API call
        
        Returns:
            EvaluationReport with all metric results
        """
        metadata = llm_metadata or {}
        results = []
        
        # Run all metrics
        for metric in self.metrics:
            result = await metric.evaluate(
                prompt=rendered_prompt,
                response=llm_response,
                context=test_context,
                metadata=metadata,
            )
            results.append(result)
        
        # Generate comprehensive report
        report = EvaluationReport.from_results(
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            prompt_hash=prompt_hash,
            test_context=test_context,
            rendered_prompt=rendered_prompt,
            llm_response=llm_response,
            llm_metadata=metadata,
            metric_results=results,
            metric_weights=self.metric_weights,
        )
        
        return report
    
    async def compare_versions(
        self,
        prompt_name: str,
        version_a: str,
        version_b: str,
        test_context: Dict[str, Any],
        renderer: Any,  # PromptRenderer
        llm_fn: Callable[[str], Dict[str, Any]],
    ) -> Dict[str, EvaluationReport]:
        """
        A/B test two prompt versions with the same context.
        
        Args:
            prompt_name: Template name
            version_a: First version to test
            version_b: Second version to test
            test_context: Shared test context
            renderer: PromptRenderer instance
            llm_fn: Async function that takes prompt and returns
                   {"response": str, "metadata": dict}
        
        Returns:
            Dict mapping version -> EvaluationReport
        """
        results = {}
        
        for version in [version_a, version_b]:
            # Load and render template
            template = renderer.load_template(prompt_name, version)
            rendered = await renderer.render(prompt_name, version, test_context)
            
            # Get LLM response
            llm_result = await llm_fn(rendered)
            
            # Evaluate
            report = await self.evaluate(
                prompt_name=prompt_name,
                prompt_version=version,
                prompt_hash=template.template_hash,
                test_context=test_context,
                rendered_prompt=rendered,
                llm_response=llm_result["response"],
                llm_metadata=llm_result.get("metadata", {}),
            )
            
            results[version] = report
        
        return results
    
    async def batch_evaluate(
        self,
        prompt_name: str,
        prompt_version: str,
        test_cases: List[Dict[str, Any]],
        renderer: Any,  # PromptRenderer
        llm_fn: Callable[[str], Dict[str, Any]],
    ) -> List[EvaluationReport]:
        """
        Evaluate prompt across multiple test cases.
        
        Args:
            prompt_name: Template name
            prompt_version: Template version
            test_cases: List of contexts to test with
            renderer: PromptRenderer instance
            llm_fn: Async function that takes prompt and returns
                   {"response": str, "metadata": dict}
        
        Returns:
            List of EvaluationReports, one per test case
        """
        template = renderer.load_template(prompt_name, prompt_version)
        reports = []
        
        for i, test_context in enumerate(test_cases):
            # Render prompt
            rendered = await renderer.render(prompt_name, prompt_version, test_context)
            
            # Get LLM response
            llm_result = await llm_fn(rendered)
            
            # Evaluate
            report = await self.evaluate(
                prompt_name=prompt_name,
                prompt_version=prompt_version,
                prompt_hash=template.template_hash,
                test_context=test_context,
                rendered_prompt=rendered,
                llm_response=llm_result["response"],
                llm_metadata=llm_result.get("metadata", {}),
            )
            
            reports.append(report)
        
        return reports
    
    def aggregate_reports(self, reports: List[EvaluationReport]) -> Dict[str, Any]:
        """
        Aggregate statistics across multiple evaluation reports.
        
        Args:
            reports: List of evaluation reports to aggregate
        
        Returns:
            Dictionary with aggregate statistics
        """
        if not reports:
            return {}
        
        total_reports = len(reports)
        passed_reports = sum(1 for r in reports if r.passed)
        
        # Average scores per metric
        metric_scores: Dict[str, List[float]] = {}
        for report in reports:
            for result in report.metric_results:
                if result.metric_name not in metric_scores:
                    metric_scores[result.metric_name] = []
                metric_scores[result.metric_name].append(result.score)
        
        avg_metric_scores = {
            name: sum(scores) / len(scores)
            for name, scores in metric_scores.items()
        }
        
        # Overall statistics
        overall_scores = [r.overall_score for r in reports]
        avg_overall_score = sum(overall_scores) / len(overall_scores)
        
        return {
            "total_evaluations": total_reports,
            "passed_evaluations": passed_reports,
            "pass_rate": passed_reports / total_reports,
            "average_overall_score": avg_overall_score,
            "average_metric_scores": avg_metric_scores,
            "min_score": min(overall_scores),
            "max_score": max(overall_scores),
        }
