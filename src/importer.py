import re
from collections import defaultdict
from typing import Optional

import click

from aeries_utils import AeriesData, AssignmentPatchData, AeriesAssignmentData
from google_classroom_utils import GoogleClassroomData, GoogleClassroomAssignment
from validator import Validator

GRADEBOOK_NUMBER_PATTERN = re.compile(r'^([0-9]+)/([F|S])$')


def run_import(classroom_service,
               periods: list[int],
               s_cookie: str) -> None:
    """
    Runs the logic for importing assignment grades from Google Classroom to Aeries.

    :param classroom_service: The Google Classroom service object.
    :param periods: The list of period numbers to import grades.
    :param s_cookie: The cookie for logging into Aeries.
    """
    google_classroom_data = GoogleClassroomData(periods=periods, classroom_service=classroom_service)
    google_classroom_data.get_submissions()

    aeries_data = AeriesData(periods=periods, s_cookie=s_cookie)

    aeries_data.extract_gradebook_ids_from_html()
    aeries_data.extract_student_ids_to_student_nums_from_html()
    aeries_data.extract_assignment_information_from_html()
    aeries_data.extract_assignment_submissions_from_html()
    aeries_data.extract_gradebook_information_from_html()

    assignment_patch_data = _join_google_classroom_and_aeries_data(
        google_classroom_data=google_classroom_data,
        aeries_data=aeries_data
    )

    aeries_data.update_grades_in_aeries(assignment_patch_data=assignment_patch_data)

    click.echo('Grades have been successfully imported to Aeries.')
    click.echo('Checking grades for any discrepancies...')
    validator = Validator(
        periods=periods,
        google_classroom_data=google_classroom_data,
        aeries_data=aeries_data
    )
    validator.generate_discrepancy_report()
    validator.log_discrepancies()
    click.echo('\nGrades have been validated.')


def _join_google_classroom_and_aeries_data(
        google_classroom_data: GoogleClassroomData,
        aeries_data: AeriesData) -> dict[str, list[AssignmentPatchData]]:
    click.echo('Matching Google Classroom grades to Aeries Assignments...')
    assignment_patch_data = defaultdict(list)
    for period, google_classroom_assignments in google_classroom_data.periods_to_assignments.items():
        click.echo(f'\tProcessing Period {period}...')
        gradebook_id = aeries_data.periods_to_gradebook_ids[period]

        next_assignment_id = max(map(lambda x: x.id,
                                     aeries_data.periods_to_assignment_information[period].values())) + 1

        for google_classroom_assignment in google_classroom_assignments:
            aeries_assignment, next_assignment_id = _get_or_create_aeries_assignment(
                google_classroom_assignment=google_classroom_assignment,
                aeries_data=aeries_data,
                period=period,
                next_assignment_id=next_assignment_id
            )

            assignment_patch_data[gradebook_id].extend(
                _generate_patch_data_for_assignment(
                    google_classroom_data=google_classroom_data,
                    google_classroom_submissions=google_classroom_assignment.submissions,
                    aeries_data=aeries_data,
                    aeries_assignment_id=aeries_assignment.id,
                    period=period
                )
            )

    return assignment_patch_data


def _get_or_create_aeries_assignment(
        google_classroom_assignment: GoogleClassroomAssignment,
        aeries_data: AeriesData,
        period: int,
        next_assignment_id: int) -> tuple[AeriesAssignmentData, int]:
    """
    Gets or creates an Aeries assignment based on the Google Classroom assignment data. Also returns the next id
    to use for creating an assignment.
    """
    assignment_name = google_classroom_assignment.assignment_name
    end_term_dates = aeries_data.periods_to_gradebook_information[period].end_term_dates
    categories = aeries_data.periods_to_gradebook_information[period].categories
    aeries_assignments = aeries_data.periods_to_assignment_information[period]
    gradebook_id = aeries_data.periods_to_gradebook_ids[period]

    if assignment_name not in aeries_assignments:
        gradebook_number_match = GRADEBOOK_NUMBER_PATTERN.match(gradebook_id)

        if not gradebook_number_match:
            raise ValueError('Expected gradebook number to be of pattern <number>/<S or F>, '
                             f'but was {gradebook_id}')

        gradebook_number = gradebook_number_match.group(1)
        term_letter = gradebook_number_match.group(2)
        aeries_assignment = aeries_data.create_aeries_assignment(
            gradebook_number=gradebook_number,
            assignment_id=next_assignment_id,
            assignment_name=assignment_name,
            point_total=google_classroom_assignment.point_total,
            category=categories[google_classroom_assignment.category],
            end_term_date=end_term_dates[term_letter])
        next_assignment_id += 1
    else:
        aeries_assignment = aeries_assignments[assignment_name]

        if (aeries_assignment.point_total != google_classroom_assignment.point_total
                or aeries_assignment.category != google_classroom_assignment.category):
            gradebook_number_match = GRADEBOOK_NUMBER_PATTERN.match(gradebook_id)

            if not gradebook_number_match:
                raise ValueError('Expected gradebook number to be of pattern <number>/<S or F>, '
                                 f'but was {gradebook_id}')

            gradebook_number = gradebook_number_match.group(1)
            term_letter = gradebook_number_match.group(2)

            aeries_assignment = aeries_data.patch_aeries_assignment(
                gradebook_number=gradebook_number,
                assignment_id=aeries_assignment.id,
                assignment_name=assignment_name,
                point_total=google_classroom_assignment.point_total,
                category=categories[google_classroom_assignment.category],
                end_term_date=end_term_dates[term_letter])

    return aeries_assignment, next_assignment_id


def _generate_patch_data_for_assignment(
        google_classroom_data: GoogleClassroomData,
        google_classroom_submissions: dict[int, Optional[float]],
        aeries_data: AeriesData,
        aeries_assignment_id: int,
        period: int) -> list[AssignmentPatchData]:
    patch_data = []
    aeries_submissions = (aeries_data.periods_to_assignment_submissions[period]
                          .get(aeries_assignment_id, {}))
    student_ids_to_student_nums = aeries_data.periods_to_student_ids_to_student_nums[period]

    for student_id, grade in google_classroom_submissions.items():
        if student_id not in student_ids_to_student_nums:
            student_name = google_classroom_data.user_ids_to_names[student_id]
            raise ValueError(f'Student {student_name} found in Google Classroom who is not enrolled in the Aeries '
                             'roster. Please check Aeries if they need to added to the class, or if they should be '
                             'dropped from the Google Classroom roster.')

        student_num = student_ids_to_student_nums[student_id]
        if len(aeries_submissions) == 0:
            patch_data.append(AssignmentPatchData(student_num=student_num,
                                                  assignment_number=aeries_assignment_id,
                                                  grade=grade))
            continue

        aeries_score = aeries_submissions[student_num]
        if grade is None:
            if aeries_score != '':
                patch_data.append(AssignmentPatchData(student_num=student_num,
                                                      assignment_number=aeries_assignment_id,
                                                      grade=grade))
        elif grade == 0:
            if aeries_score != 'MI':
                patch_data.append(AssignmentPatchData(student_num=student_num,
                                                      assignment_number=aeries_assignment_id,
                                                      grade=grade))
        elif aeries_score == '' or aeries_score == 'N/A' or aeries_score == 'MI' or grade != float(aeries_score):
            patch_data.append(AssignmentPatchData(student_num=student_num,
                                                  assignment_number=aeries_assignment_id,
                                                  grade=grade))

    return patch_data
