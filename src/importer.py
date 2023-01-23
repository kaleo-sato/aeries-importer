from dataclasses import dataclass
from typing import Optional

from aeries_utils import extract_gradebook_ids_from_html, extract_student_ids_to_student_nums_from_html, \
    extract_assignment_information_from_html
from google_classroom_utils import get_submissions


@dataclass(frozen=True)
class AssignmentSubmissions:
    student_submissions: dict[int, Optional[float]]


def run_import(classroom_service,
               periods: list[int],
               aeries_cookie: str) -> None:
    """
    Runs the logic for importing assignment grades from Google Classroom to Aeries.

    :param classroom_service: The Google Classroom service object.
    :param aeries_cookie: The cookie for logging into Aeries.
    :param periods: The list of period numbers to import grades.
    """
    periods_to_assignment_name_to_submissions = get_submissions(classroom_service=classroom_service,
                                                                periods=periods)

    periods_to_gradebook_ids = extract_gradebook_ids_from_html(periods=periods,
                                                               aeries_cookie=aeries_cookie)

    student_ids_to_student_nums = extract_student_ids_to_student_nums_from_html(
        periods_to_gradebook_ids=periods_to_gradebook_ids,
        aeries_cookie=aeries_cookie
    )

    periods_to_assignments = extract_assignment_information_from_html(
        periods_to_gradebook_ids=periods_to_gradebook_ids,
        aeries_cookie=aeries_cookie
    )
    return None
