import click

import math

from aeries_utils import AeriesData, AeriesCategory

from dataclasses import dataclass
from typing import Optional


@dataclass
class BoundaryResult:
    student_name: str
    current_overall: float

    target: int
    required_score: float
    percent_of_points: float


def run_final_grade_calculations(performance_points: float,
                                 periods: list[int],
                                 s_cookie: str) -> None:
    """
    Runs the logic for determining how many of the input performance_points are needed to go up/down a grade.

    :param performance_points: How many performance points remain.
    :param periods: The list of period numbers to import grades.
    :param s_cookie: The cookie to use for Aeries authentication.
    """
    aeries_data = AeriesData(periods=periods, s_cookie=s_cookie)
    aeries_data.extract_gradebook_ids_from_html()
    aeries_data.extract_student_ids_to_student_nums_from_html()
    aeries_data.extract_gradebook_information_from_html()
    aeries_data.fetch_aeries_detailed_overall_grades()

    log_boundaries(periods, aeries_data, performance_points)


def log_boundaries(periods, aeries_data: AeriesData, performance_points: int) -> None:
    for period in periods:
        categories = aeries_data.periods_to_gradebook_information[period].categories

        click.echo(f"\n{'=' * 80}")
        click.echo(f"PERIOD: {period}")
        click.echo(f"{'=' * 80}")

        period_results = []
        student_names_to_overall_grades = aeries_data.periods_to_student_names_to_detailed_overall_grades[period]

        for student_name, overall_grade in student_names_to_overall_grades.items():
            results = _calculate_boundary_for_one_student(
                student_name,
                overall_grade,
                performance_points,
                categories,
            )

            if not results:
                continue

            period_results.append(results)

        def risk_sort(boundary_results: list[BoundaryResult]):
            if (all(result.required_score > performance_points or result.required_score < 0 for result in boundary_results)):
                return float('inf')

            possible_boundary_results = [boundary_result for boundary_result in boundary_results
                                         if boundary_result.required_score <= performance_points
                                         and boundary_result.required_score >= 0]
            return -max(possible_boundary_results, key=lambda r: r.required_score).required_score

        for results in sorted(period_results, key=lambda r: (risk_sort(r), r[0].student_name)):
            click.echo(f"\n{results[0].student_name} ({results[0].current_overall:.2f}%)")

            for r in results:
                if r.target < r.current_overall:
                    label = "Keep"
                else:
                    label = "Reach"

                if r.required_score < 0:
                    click.echo(f"  {label} {r.target}%: Already secured")
                elif r.required_score > performance_points:
                    click.echo(f"  {label} {r.target}%: impossible to reach")
                else:
                    click.echo(
                        f"  {label} {r.target}%: "
                        f"{r.required_score:.2f}/{performance_points} "
                        f"({r.percent_of_points:.2f}%)"
                    )


def _calculate_boundary_for_one_student(
    student_name: str,
    overall_grade: dict[str, dict[str, float]],
    performance_points: int,
    categories: dict[str, AeriesCategory],
) -> list[BoundaryResult]:
    current_overall = overall_grade["Total"]["category_percent"]

    performance_category_name = next(
        (
            name
            for name in overall_grade
            if name != "Total" and "Performance" in name
        ),
        None,
    )

    if performance_category_name is None:
        return []

    performance_category = overall_grade[performance_category_name]

    earned = float(performance_category["category_earned"])
    total = float(performance_category["category_total"])

    if total <= 0:
        return []

    performance_weight = categories[performance_category_name].weight

    current_performance_percent = earned / total * 100

    other_categories_contribution = (
        current_overall
        - performance_weight * current_performance_percent
    )

    def required_score(target_overall: float) -> float:
        required_performance_percent = (
            target_overall - other_categories_contribution
        ) / performance_weight

        required_earned = (
            required_performance_percent / 100
        ) * (total + performance_points)

        return required_earned - earned

    results: list[BoundaryResult] = []

    def add_result(target: int):
        score_needed = required_score(target)
        percent = score_needed / performance_points * 100

        results.append(
            BoundaryResult(
                student_name=student_name,
                current_overall=current_overall,
                target=target,
                required_score=score_needed,
                percent_of_points=percent,
            )
        )

    # Determine boundaries
    if current_overall < 60:
        upper_target = 60
        lower_target = None
    elif current_overall < 90:
        lower_target = math.floor(current_overall / 10) * 10
        upper_target = math.ceil(current_overall / 10) * 10

        if lower_target == upper_target:
            upper_target += 10
    else:
        lower_target = 90
        upper_target = None

    if lower_target is not None:
        add_result(lower_target)

    if upper_target is not None:
        add_result(upper_target)

    return results
    
