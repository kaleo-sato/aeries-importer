from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Optional

from aeries_utils import extract_gradebook_ids_from_html
from google_classroom_utils import (get_all_published_coursework, get_periods_to_course_ids,
                                    get_user_ids_to_student_emails, get_grades_for_coursework)


@dataclass(frozen=True)
class OverallGrades:
    assignment_name_to_grades: dict[str, Optional[float]]


def run_import(classroom_service,
               periods: list[int],
               aeries_cookie: str) -> None:
    """
    Runs the logic for importing assignment grades from Google Classroom to Aeries.

    :param classroom_service: The Google Classroom service object.
    :param aeries_cookie: The cookie for logging into Aeries.
    :param periods: The list of period numbers to import grades.
    """
    # emails_to_grades = _get_emails_to_grades(classroom_service=classroom_service,
    #                                          periods=periods)
    #
    # print(emails_to_grades)

    gradebook_ids = extract_gradebook_ids_from_html(periods=periods,
                                                    aeries_cookie=aeries_cookie)
    return None


def _get_emails_to_grades(classroom_service, periods: Iterable[int]) -> dict[str, OverallGrades]:
    periods_to_course_ids = get_periods_to_course_ids(classroom_service=classroom_service,
                                                      periods=periods)

    emails_to_grades: dict[str, OverallGrades] = defaultdict(lambda: OverallGrades(assignment_name_to_grades={}))
    for period, course_id in periods_to_course_ids.items():
        user_ids_to_emails = get_user_ids_to_student_emails(classroom_service=classroom_service,
                                                            course_id=course_id)

        coursework_ids_and_names = get_all_published_coursework(classroom_service=classroom_service,
                                                                course_id=course_id)

        for coursework_id, assignment_name in coursework_ids_and_names:
            user_ids_to_grades = get_grades_for_coursework(classroom_service=classroom_service,
                                                           course_id=course_id,
                                                           coursework_id=coursework_id)
            for user_id, grade in user_ids_to_grades.items():
                email = user_ids_to_emails[user_id]
                emails_to_grades[email].assignment_name_to_grades[assignment_name] = grade

    return emails_to_grades
