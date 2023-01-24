from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from aeries_utils import extract_gradebook_ids_from_html, extract_student_ids_to_student_nums_from_html, \
    extract_assignment_information_from_html, AeriesAssignmentData
from google_classroom_utils import GoogleClassroomAssignment, get_submissions


@dataclass(frozen=True)
class AssignmentPatchData:
    student_num: int
    assignment_number: int
    grade: Optional[float]


def run_import(classroom_service,
               periods: list[int],
               aeries_cookie: str) -> None:
    """
    Runs the logic for importing assignment grades from Google Classroom to Aeries.

    :param classroom_service: The Google Classroom service object.
    :param aeries_cookie: The cookie for logging into Aeries.
    :param periods: The list of period numbers to import grades.
    """
    periods_to_assignment_data = get_submissions(classroom_service=classroom_service,
                                                 periods=periods)

    periods_to_gradebook_ids = extract_gradebook_ids_from_html(periods=periods,
                                                               aeries_cookie=aeries_cookie)

    student_ids_to_student_nums = extract_student_ids_to_student_nums_from_html(
        periods_to_gradebook_ids=periods_to_gradebook_ids,
        aeries_cookie=aeries_cookie
    )

    periods_to_assignment_name_to_aeries_assignments = extract_assignment_information_from_html(
        periods_to_gradebook_ids=periods_to_gradebook_ids,
        aeries_cookie=aeries_cookie
    )

    _join_google_classroom_and_aeries_data(
        periods_to_assignment_data=periods_to_assignment_data,
        periods_to_gradebook_ids=periods_to_gradebook_ids,
        student_ids_to_student_nums=student_ids_to_student_nums,
        periods_to_assignment_name_to_aeries_assignments=periods_to_assignment_name_to_aeries_assignments,
        aeries_cookie=aeries_cookie
    )
    return None


def _join_google_classroom_and_aeries_data(
        periods_to_assignment_data: dict[int, list[GoogleClassroomAssignment]],
        periods_to_gradebook_ids: dict[int, str],
        student_ids_to_student_nums: dict[int, int],
        periods_to_assignment_name_to_aeries_assignments: dict[int, dict[str, AeriesAssignmentData]],
        aeries_cookie: str
) -> dict[str, set[AssignmentPatchData]]:
    assignment_patch_data = defaultdict(set)
    # for period, google_classroom_assignment in periods_to_assignment_data.items():
    #     gradebook_id = periods_to_gradebook_ids[period]
    #
    #     for assignment_name, google_classroom_assignment in google_classroom_assignment.items():
    #         # if assignment_name not in periods_to_assignment_name_to_aeries_assignments[period]:
    #         #     aeries_assignment = create_aeries_assignment(gradebook_id=gradebook_id,
    #         #                                                  assignment_name=assignment_name,
    #         #                                                  )
    #         # else:
    #         aeries_assignment = periods_to_assignment_name_to_aeries_assignments[period][assignment_name]
    #
    #         for student_id, grade in google_classroom_assignment.submissions.items():
    #             student_num = student_ids_to_student_nums[student_id]
    #
    #             assignment_patch_data[gradebook_id].add(AssignmentPatchData(student_num=student_num,
    #                                                                         assignment_number=aeries_assignment.id,
    #                                                                         grade=grade))
    #
    # return assignment_patch_data
