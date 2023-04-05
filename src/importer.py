import re
from collections import defaultdict

import click

from aeries_utils import extract_gradebook_ids_from_html, extract_student_ids_to_student_nums_from_html, \
    extract_assignment_information_from_html, AeriesAssignmentData, update_grades_in_aeries, \
    AssignmentPatchData, extract_category_information, AeriesCategory, patch_aeries_assignment
from google_classroom_utils import GoogleClassroomAssignment, get_submissions


GRADEBOOK_NUMBER_PATTERN = re.compile(r'^([0-9]+)/[A-Za-z]$')


def run_import(classroom_service,
               periods: list[int],
               s_cookie: str) -> None:
    """
    Runs the logic for importing assignment grades from Google Classroom to Aeries.

    :param classroom_service: The Google Classroom service object.
    :param periods: The list of period numbers to import grades.
    :param s_cookie: The cookie for logging into Aeries.
    """
    periods_to_assignment_data = get_submissions(classroom_service=classroom_service,
                                                 periods=periods)

    periods_to_gradebook_ids = extract_gradebook_ids_from_html(periods=periods,
                                                               s_cookie=s_cookie)

    periods_to_student_ids_to_student_nums = extract_student_ids_to_student_nums_from_html(
        periods_to_gradebook_ids=periods_to_gradebook_ids,
        s_cookie=s_cookie
    )

    periods_to_assignment_name_to_aeries_assignments = extract_assignment_information_from_html(
        periods_to_gradebook_ids=periods_to_gradebook_ids,
        s_cookie=s_cookie
    )

    periods_to_categories, request_verification_token = extract_category_information(
        periods_to_gradebook_ids=periods_to_gradebook_ids,
        s_cookie=s_cookie
    )

    assignment_patch_data = _join_google_classroom_and_aeries_data(
        periods_to_assignment_data=periods_to_assignment_data,
        periods_to_gradebook_ids=periods_to_gradebook_ids,
        periods_to_student_ids_to_student_nums=periods_to_student_ids_to_student_nums,
        periods_to_assignment_name_to_aeries_assignments=periods_to_assignment_name_to_aeries_assignments,
        periods_to_categories=periods_to_categories,
        s_cookie=s_cookie,
        request_verification_token=request_verification_token
    )

    update_grades_in_aeries(assignment_patch_data=assignment_patch_data,
                            s_cookie=s_cookie)


def _join_google_classroom_and_aeries_data(
        periods_to_assignment_data: dict[int, list[GoogleClassroomAssignment]],
        periods_to_gradebook_ids: dict[int, str],
        periods_to_student_ids_to_student_nums: dict[int, dict[int, int]],
        periods_to_assignment_name_to_aeries_assignments: dict[int, dict[str, AeriesAssignmentData]],
        periods_to_categories: dict[int, dict[str, AeriesCategory]],
        s_cookie: str,
        request_verification_token: str
) -> dict[str, list[AssignmentPatchData]]:
    click.echo('Matching Google Classroom grades to Aeries Assignments...')
    assignment_patch_data = defaultdict(list)
    for period, google_classroom_assignments in periods_to_assignment_data.items():
        click.echo(f'\tProcessing Period {period}...')
        gradebook_id = periods_to_gradebook_ids[period]
        categories = periods_to_categories[period]

        next_assignment_id = max(map(lambda x: x.id,
                                     periods_to_assignment_name_to_aeries_assignments[period].values())) + 1

        for google_classroom_assignment in google_classroom_assignments:
            assignment_name = google_classroom_assignment.assignment_name
            if assignment_name not in periods_to_assignment_name_to_aeries_assignments[period]:
                gradebook_number_match = GRADEBOOK_NUMBER_PATTERN.match(gradebook_id)

                if not gradebook_number_match:
                    raise ValueError('Expected gradebook number to be of pattern <number>/<S or F>, '
                                     f'but was {gradebook_id}')

                gradebook_number = gradebook_number_match.group(1)
                aeries_assignment = patch_aeries_assignment(gradebook_number=gradebook_number,
                                                            assignment_id=next_assignment_id,
                                                            assignment_name=assignment_name,
                                                            point_total=google_classroom_assignment.point_total,
                                                            category=categories[google_classroom_assignment.category],
                                                            s_cookie=s_cookie,
                                                            request_verification_token=request_verification_token)
                next_assignment_id += 1
            else:
                aeries_assignment = periods_to_assignment_name_to_aeries_assignments[period][assignment_name]

                if (aeries_assignment.point_total != google_classroom_assignment.point_total
                        or aeries_assignment.category != google_classroom_assignment.category):
                    gradebook_number_match = GRADEBOOK_NUMBER_PATTERN.match(gradebook_id)

                    if not gradebook_number_match:
                        raise ValueError('Expected gradebook number to be of pattern <number>/<S or F>, '
                                         f'but was {gradebook_id}')

                    gradebook_number = gradebook_number_match.group(1)

                    aeries_assignment = patch_aeries_assignment(
                        gradebook_number=gradebook_number,
                        assignment_id=aeries_assignment.id,
                        assignment_name=assignment_name,
                        point_total=google_classroom_assignment.point_total,
                        category=categories[google_classroom_assignment.category],
                        s_cookie=s_cookie,
                        request_verification_token=request_verification_token)

            for student_id, grade in google_classroom_assignment.submissions.items():
                student_num = periods_to_student_ids_to_student_nums[period][student_id]

                assignment_patch_data[gradebook_id].append(AssignmentPatchData(student_num=student_num,
                                                                               assignment_number=aeries_assignment.id,
                                                                               grade=grade))

    return assignment_patch_data
