from collections.abc import Iterable

from course_and_student_data import (get_all_published_coursework, get_periods_to_course_ids,
                                     get_user_ids_to_student_emails, get_grades_for_coursework)


def run_import(classroom_service,
               periods: Iterable[int]) -> None:
    """
    Runs the logic for importing assignment grades from Google Classroom to Aeries.

    :param classroom_service: The Google Classroom service object.
    :param periods: The list of period numbers to import grades.
    """
    periods_to_course_ids = get_periods_to_course_ids(classroom_service=classroom_service,
                                                      periods=periods)

    for period, course_id in periods_to_course_ids.items():
        user_ids_to_emails = get_user_ids_to_student_emails(classroom_service=classroom_service,
                                                            course_id=course_id)

        coursework_ids = get_all_published_coursework(classroom_service=classroom_service,
                                                      course_id=course_id)

        for coursework_id in coursework_ids:
            user_ids_to_grades = get_grades_for_coursework(classroom_service=classroom_service,
                                                           course_id=course_id,
                                                           coursework_id=coursework_id)
            print(user_ids_to_grades)

    return user_ids_to_grades
