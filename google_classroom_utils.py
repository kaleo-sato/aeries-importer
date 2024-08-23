import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Optional

import click
from arrow import Arrow

COURSEWORK_PAGE_SIZE = 1000
COURSEWORK_SUBMISSION_PAGE_SIZE = 100

EMAIL_ADDRESS_PATTERN = r'^[A-Za-z]{2}([0-9]+)@student\.musd\.org$'
EMAIL_ADDRESS_PATTERN_COMPILE = re.compile(EMAIL_ADDRESS_PATTERN)


@dataclass(frozen=True)
class GoogleClassroomAssignment:
    submissions: dict[int, Optional[float]]
    assignment_name: str
    point_total: int
    category: str


class GoogleClassroomData:

    def __init__(self, periods: Iterable[int], classroom_service) -> None:
        self.classroom_service = classroom_service
        self.periods = periods
        self.periods_to_assignments: dict[int, list[GoogleClassroomAssignment]] = defaultdict(list)

    def get_submissions(self) -> None:
        """
        Gets all student submissions of assignments for the periods and populates result as a mapping of period
        to list of assignment data, which contains assignment metadata and submissions.

        :return: Nothing, populates the periods_to_assignments attribute.
        """
        click.echo('Retrieving assignment submissions from Google Classroom...')
        periods_to_course_ids = self._get_periods_to_course_ids()

        for period, course_id in periods_to_course_ids.items():
            click.echo(f'\tProcessing Period {period}...')
            user_ids_to_student_ids = self._get_user_ids_to_student_ids(course_id=course_id)

            coursework_ids_to_assignment_data = self._get_all_published_coursework(course_id=course_id)

            for coursework_id, assignment_data in coursework_ids_to_assignment_data.items():
                user_ids_to_grades = self._get_grades_for_coursework(course_id=course_id,
                                                                     coursework_id=coursework_id)
                for user_id, grade in user_ids_to_grades.items():
                    student_id = user_ids_to_student_ids[user_id]
                    assignment_data.submissions[student_id] = grade

                self.periods_to_assignments[period].append(assignment_data)

    def _get_periods_to_course_ids(self) -> dict[int, int]:
        """
        Returns period number mapped to the course id.

        :return: The period number mapped to its corresponding Course Id.
        """
        courses = self.classroom_service.courses().list().execute().get('courses', [])
        valid_courses = {course['section'][:len('Period 1')]: course['id']
                         for course in courses if 'Period ' in course.get('section', '')
                         and course.get('courseState') == 'ACTIVE'}

        periods_to_course_ids: dict[int, int] = {}
        for period in self.periods:
            section_name = f'Period {period}'
            if section_name not in valid_courses:
                raise ValueError(f'{section_name} is not a valid period number.')
            periods_to_course_ids[period] = valid_courses[section_name]

        return periods_to_course_ids

    def _get_user_ids_to_student_ids(self, course_id: int) -> dict[int, int]:
        """
        Returns Google service user id mapped to the student id.

        :param course_id: The Course Id to fetch student emails from.
        :return: The student user id mapped to their student id.
        """
        user_ids_to_student_ids: dict[int, int] = {}
        query = self.classroom_service.courses().students().list(courseId=course_id).execute()
        students = query.get('students', [])

        while True:
            for student in students:
                email = student['profile']['emailAddress']
                google_id = student['userId']

                match = EMAIL_ADDRESS_PATTERN_COMPILE.match(email)

                if not match:
                    raise ValueError(f'Student email address is in an unexpected format: {email}')
                user_ids_to_student_ids[google_id] = int(match.group(1))

            next_page_token = query.get('nextPageToken')
            if next_page_token:
                query = (self.classroom_service
                         .courses()
                         .students()
                         .list(courseId=course_id, pageToken=next_page_token)
                         .execute())
                students = query.get('students', [])
            else:
                break

        return user_ids_to_student_ids

    def _get_all_published_coursework(self, course_id: int) -> dict[int, GoogleClassroomAssignment]:
        """
        Returns a mapping of assignment id to assignment metadata for published coursework in the given course_id.

        :param course_id: The Course Id to get all published coursework for.
        :return: The assignment id mapped to assignment metadata
        """
        coursework = (self.classroom_service
                      .courses()
                      .courseWork()
                      .list(courseId=course_id,
                            pageSize=COURSEWORK_PAGE_SIZE,
                            orderBy='dueDate desc')
                      .execute()
                      .get('courseWork', []))

        coursework_assignments = {}
        for coursework_obj in coursework:
            if not GoogleClassroomData._is_current_semester(coursework_obj['dueDate']['month']):
                break

            # This is possible if an assignment has a point value and students submit, but then the assignment later is
            # changed to Ungraded.
            if 'maxPoints' not in coursework_obj:
                continue

            coursework_assignments[coursework_obj['id']] = GoogleClassroomAssignment(
                submissions={},
                assignment_name=coursework_obj['title'].strip(),
                point_total=coursework_obj['maxPoints'],
                category=coursework_obj['gradeCategory']['name']
            )

        return coursework_assignments

    @staticmethod
    def _is_current_semester(month: int) -> bool:
        """
        Determine if the coursework's month due date is within the same semester as the current time.
        """
        current_time = Arrow.now()
        if 1 <= current_time.month <= 6:
            return 1 <= month <= 6
        else:
            return 7 <= month <= 12

    def _get_grades_for_coursework(self,
                                   course_id: int,
                                   coursework_id: int) -> dict[int, Optional[float]]:
        """
        Returns the grades for the assignment as a map of user id to the point total.
        If the grade is None, that means that the assignment is not graded. This could mean that grading is unfinished,
        or that the student is excused from this work.

        :param course_id: The Course Id that is relevant to the coursework id.
        :param coursework_id: The Coursework Id to get all student submissions for.
        :return: The student user id mapped to their grade for the assignment.
        """
        student_submissions = (self.classroom_service
                               .courses()
                               .courseWork()
                               .studentSubmissions()
                               .list(courseId=course_id,
                                     courseWorkId=coursework_id,
                                     pageSize=COURSEWORK_SUBMISSION_PAGE_SIZE)
                               .execute()
                               .get('studentSubmissions', []))
        return {submission['userId']: submission.get('assignedGrade') for submission in student_submissions}

    def get_student_name(self, student_id: int) -> str:
        """
        Returns the name of the student with the given student id.

        :param student_id: The student id to get the name for.
        :return: The student name.
        """
        user_profile = (self.classroom_service
                        .userProfiles()
                        .get(userId=student_id)
                        .execute())
        return user_profile['name']['fullName']

