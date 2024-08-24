import math
from collections import defaultdict

import click
from collections.abc import Iterable
from dataclasses import dataclass

from aeries_utils import AeriesData
from google_classroom_utils import GoogleClassroomData


@dataclass(frozen=True)
class OverallGradeDiscrepancy:
    google_classroom_overall_grade: float
    aeries_overall_grade: float


class Validator:

    def __init__(self,
                 periods: Iterable[int],
                 google_classroom_data: GoogleClassroomData,
                 aeries_data: AeriesData) -> None:
        self.periods = periods
        self.google_classroom_data = google_classroom_data
        self.aeries_data = aeries_data

        # period -> student_id -> discrepancy
        self.periods_to_student_overall_grade_discrepancies = defaultdict(dict)

    def generate_discrepancy_report(self) -> None:
        """
        Populate periods_to_overall_grade_discrepancies with discrepancies between Google Classroom and Aeries.
        """
        for period in self.periods:
            categories_to_weights = {
                category_name: aeries_category.weight
                for category_name, aeries_category in self.aeries_data.periods_to_gradebook_information[period].categories.items()
            }
            google_classroom_overall_grades = self.google_classroom_data.get_overall_grades(
                period=period,
                categories_to_weights=categories_to_weights
            )
            aeries_overall_grades = self.aeries_data.extract_overall_grades_from_html(period=period)

            for student_id, google_classroom_overall_grade in google_classroom_overall_grades.items():
                aeries_overall_grade = aeries_overall_grades[student_id]

                if not math.isclose(google_classroom_overall_grade, aeries_overall_grade, abs_tol=0.01):
                    discrepancy = OverallGradeDiscrepancy(google_classroom_overall_grade=google_classroom_overall_grade,
                                                          aeries_overall_grade=aeries_overall_grade)
                    self.periods_to_student_overall_grade_discrepancies[period][student_id] = discrepancy

    def log_discrepancies(self) -> None:
        if not self.periods_to_student_overall_grade_discrepancies:
            return

        periods_to_student_ids_to_names = self.google_classroom_data.get_student_ids_to_names()

        click.echo('***Discrepancies between Google Classroom and Aeries overall grades:***')
        for period in self.periods:
            period_discrepancies = self.periods_to_student_overall_grade_discrepancies[period]

            if not period_discrepancies:
                continue

            click.echo(f'Period {period}:')
            click.echo("\t{:<30}{:>20}{:>10}".format('Student', 'Google Classroom', 'Aeries'))
            for student_id, discrepancy in sorted(
                    period_discrepancies.items(),
                    key=lambda pair: periods_to_student_ids_to_names[period][pair[0]].split(' ')[-1]):
                student_name = periods_to_student_ids_to_names[period][student_id]
                google_classroom_grade = discrepancy.google_classroom_overall_grade
                aeries_grade = discrepancy.aeries_overall_grade
                click.echo(f"\t{student_name:<30}{google_classroom_grade:>20.2f}{aeries_grade:>10}")
