from collections.abc import Iterable
from typing import Optional

COURSEWORK_PAGE_SIZE = 1000
COURSEWORK_SUBMISSION_PAGE_SIZE = 100


def get_periods_to_course_ids(classroom_service,
                              periods: Iterable[int]) -> dict[int, int]:
    """
    Returns period number mapped to the id.

    :param classroom_service: The Google Classroom service object.
    :param periods: The list of periods to filter for.
    :return: The period number mapped to its corresponding Course Id.
    """
    courses = classroom_service.courses().list().execute().get('courses', [])
    valid_courses = {course['section']: course['id']
                     for course in courses if 'Period ' in course['section']}

    periods_to_course_ids: dict[int, int] = {}
    for period in periods:
        section_name = f'Period {period}'
        if section_name not in valid_courses:
            raise ValueError(f'{section_name} is not a valid period number.')
        periods_to_course_ids[period] = valid_courses[section_name]

    return periods_to_course_ids


def get_user_ids_to_student_emails(classroom_service, course_id: int) -> dict[int, str]:
    """
    Returns user id mapped to the email.

    :param classroom_service: The Google Classroom service object.
    :param course_id: The Course Id to fetch student emails from.
    :return: The student user id mapped to their emails.
    """
    students = classroom_service.courses().students().list(courseId=course_id).execute().get('students', [])
    return {student['userId']: student['profile']['emailAddress'] for student in students}


def get_all_published_coursework(classroom_service, course_id: int) -> list[tuple[int, str]]:
    """
    Returns a list of all assignment names and coursework ids for published coursework in the given course_id.

    :param classroom_service: The Google Classroom service object.
    :param course_id: The Course Id to get all published coursework for.
    :return: The student user id mapped to their emails.
    """
    coursework = (classroom_service
                  .courses()
                  .courseWork()
                  .list(courseId=course_id,
                        pageSize=COURSEWORK_PAGE_SIZE)
                  .execute()
                  .get('courseWork', []))
    return [(coursework_obj['id'], coursework_obj['title']) for coursework_obj in coursework]


def get_grades_for_coursework(classroom_service,
                              course_id: int,
                              coursework_id: int) -> dict[int, Optional[float]]:
    """
    Returns the grades for the assignment as a map of user id to the point total.
    If the grade is None, that means that the assignment is not graded. This could mean that grading is unfinished, or
    that the student is excused from this work.

    :param classroom_service: The Google Classroom service object.
    :param course_id: The Course Id that is relevant to the coursework id.
    :param coursework_id: The Coursework Id to get all student submissions for.
    :return: The student user id mapped to their grade for the assignment.
    """
    student_submissions = (classroom_service
                           .courses()
                           .courseWork()
                           .studentSubmissions()
                           .list(courseId=course_id,
                                 courseWorkId=coursework_id,
                                 pageSize=COURSEWORK_SUBMISSION_PAGE_SIZE)
                           .execute()
                           .get('studentSubmissions', []))
    return {submission['userId']: submission.get('assignedGrade') for submission in student_submissions}
