import re
from dataclasses import dataclass
from itertools import zip_longest
from typing import Optional, List

import click
from arrow import Arrow
from bs4 import BeautifulSoup
import requests

from constants import MILPITAS_SCHOOL_CODE

GRADEBOOK_URL = 'https://aeries.musd.org/gradebook'
GRADEBOOK_HTML_ID = 'ValidGradebookList'
GRADEBOOK_LIST_ATTRIBUTE = 'data-validgradebookandterm'
GRADEBOOK_NAME_PATTERN = r'^([1-6]) - '
GRADEBOOK_AND_TERM_TAG_NAME = 'data-validgradebookandterm'
LIST_VIEW_ID = 'GbkDash-list-view'

SCORES_BY_CLASS_URL = 'https://aeries.musd.org/gradebook/{gradebook_id}/scoresByClass'
SCORES_BY_CLASS_ASSIGNMENT_INFO_TABLE_CLASS_NAME = 'assignment-header'
SCORES_BY_CLASS_ASSIGNMENT_NAME_CLASS_NAME = 'scores-by-class-override'
SCORES_BY_CLASS_STUDENT_INFO_TABLE_CLASS_NAME = 'students'
STUDENT_ID_TAG_NAME = 'data-stuid'
STUDENT_NUMBER_TAG_NAME = 'data-sn'
SCORE_TAG_NAME = 'data-original-value'
ASSIGNMENT_DESC_CLASS_NAME = 'description row cursor-hand'
ASSIGNMENT_CATEGORY_SEARCH_STRING = 'Category:'
ASSIGNMENT_DESC_TAG_NAME = 'data-assignment-desc'
ASSIGNMENT_NAME_PATTERN = r'^[0-9]+ - (.+)'
ASSIGNMENT_POINT_TOTAL_PATTERN = r' : ([0-9]+)'
ASSIGNMENT_NUMBER_TAG_NAME = 'data-an'
ASSIGNMENT_SCORES_ROW = 'scores row'
ASSIGNMENT_TOTAL_SCORE_TITLE = '# Correct Possible'
ASSIGNMENT_SUBMISSION_CLASS_ROW_TAG_NAME = 'cell text-center hidden-text cell-by-class'

GRADEBOOK_INFORMATION_URL = 'https://aeries.musd.org/gradebook/{gradebook_id}/manage'
WEIGHT_CATEGORY_TABLE_ID = 'manageManageCategoriesTable'
END_TERMS_TABLE_ID = 'manageTerms'
GRADEBOOK_TERM_ID = 'gradebook-term-desc'
END_TERMS_END_DATE_ID = 'term-end-date'

CREATE_ASSIGNMENT_URL = 'https://aeries.musd.org/gradebook/manage/assignment'

UPDATE_ASSIGNMENT_GRADE_URL = 'https://aeries.musd.org/api/schools/{school_code}/gradebooks/{gradebook_id}/students/'\
                              '{student_number}/{school_code}/scores/{assignment_number}'


@dataclass(frozen=True)
class AeriesAssignmentData:
    id: int
    point_total: int
    category: str


@dataclass(frozen=True)
class AssignmentPatchData:
    student_num: int
    assignment_number: int
    grade: Optional[float]


@dataclass(frozen=True)
class AeriesCategory:
    name: str
    weight: float
    id: int


@dataclass(frozen=True)
class AeriesClassroomData:
    categories: dict[str, AeriesCategory]
    end_term_dates: dict[str, Arrow]


class AeriesData:

    def __init__(self, periods: List[int], s_cookie: str):
        self.periods = periods
        self.s_cookie = s_cookie
        self.request_verification_token = ''
        self.periods_to_gradebook_ids = {}
        self.periods_to_student_ids_to_student_nums = {}
        self.periods_to_assignment_information = {}
        self.periods_to_assignment_submissions = {}
        self.periods_to_gradebook_information = {}

    def extract_gradebook_ids_from_html(self) -> None:
        """
        Parse the HTML of the Aeries gradebook page to get the gradebook ids for the periods.
        """
        click.echo('Retrieving Aeries Gradebook ids...')
        headers = {'Accept': 'application/json, text/html, application/xhtml+xml, */*',
                   'Cookie': f's={self.s_cookie}'}
        response = requests.get(GRADEBOOK_URL, headers=headers)
        beautiful_soup = BeautifulSoup(response.text, 'html.parser')

        self.periods_to_gradebook_ids = self._get_periods_to_gradebook_and_term(beautiful_soup=beautiful_soup)

    def _get_periods_to_gradebook_and_term(self, beautiful_soup: BeautifulSoup) -> dict[int, str]:
        # Parse HTML for gradebook numbers and terms, e.g. '4532451/S'
        gradebook_list_tags = beautiful_soup.find(id=GRADEBOOK_HTML_ID).find_all('li')
        gradebook_and_terms = [tag.get(GRADEBOOK_AND_TERM_TAG_NAME) for tag in gradebook_list_tags]

        # Use gradebook numbers and terms to map to the period num and filter by periods supplied.
        # Parse the list view of the gradebooks to reduce false positive searches for the gradebook link.
        periods_to_gradebook_and_term = dict()
        for gradebook_and_term in gradebook_and_terms:
            class_name = (beautiful_soup
                          .find(id=LIST_VIEW_ID)
                          .find(href=re.compile(f'gradebook/{gradebook_and_term}/ScoresByClass')).string)
            period_num_match = re.match(GRADEBOOK_NAME_PATTERN, class_name)

            if not period_num_match:
                raise ValueError(f'Unexpected naming convention for Aeries class: {class_name}. '
                                 'Expected it to start with "[1-6] - "')

            period_num = int(period_num_match.group(1))
            if period_num in self.periods:
                periods_to_gradebook_and_term[period_num] = gradebook_and_term

        if len(periods_to_gradebook_and_term) != len(self.periods):
            raise ValueError(
                'Periods specified were not matched to the Aeries class gradebook.\n'
                f'Periods wanted: {", ".join(str(period) for period in sorted(self.periods))}\n'
                f'Periods found in Aeries: {", ".join(str(period) for period in sorted(periods_to_gradebook_and_term))}'
            )

        return periods_to_gradebook_and_term

    def extract_student_ids_to_student_nums_from_html(self) -> None:
        """
        Parse the HTML of the Aeries gradebook page to get the student ids mapped to student numbers for the periods.
        Student numbers are used to send HTTP requests to Aeries for updating grades, while student ids are the ids
        that are used in Google Classroom.
        """
        click.echo('Fetching Student Numbers (not IDs!) from Aeries...')
        headers = {'Accept': 'application/json, text/html, application/xhtml+xml, */*',
                   'Cookie': f's={self.s_cookie}'}

        for period, gradebook_id in self.periods_to_gradebook_ids.items():
            click.echo(f'\tProcessing Period {period}...')
            response = requests.get(SCORES_BY_CLASS_URL.format(gradebook_id=gradebook_id), headers=headers)
            beautiful_soup = BeautifulSoup(response.text, 'html.parser')

            self.periods_to_student_ids_to_student_nums[period] = AeriesData._get_student_ids_to_student_nums(
                beautiful_soup=beautiful_soup
            )

    @staticmethod
    def _get_student_ids_to_student_nums(beautiful_soup: BeautifulSoup) -> dict[int, int]:
        student_ids_to_student_nums = dict()
        for tag in (beautiful_soup
                    .find('table', class_=SCORES_BY_CLASS_STUDENT_INFO_TABLE_CLASS_NAME)
                    .find_all('tr', class_='row')):
            student_number = int(tag.get(STUDENT_NUMBER_TAG_NAME))
            student_id = int(tag.get(STUDENT_ID_TAG_NAME))

            student_ids_to_student_nums[student_id] = student_number

        return student_ids_to_student_nums

    def extract_assignment_information_from_html(self) -> None:
        """
        Get assignment information from Aeries for the periods. The assignment data includes assignment id, point total,
        and category.
        """
        click.echo('Fetching Assignment information from Aeries...')
        headers = {'Accept': 'application/json, text/html, application/xhtml+xml, */*',
                   'Cookie': f's={self.s_cookie}'}

        for period, gradebook_id in self.periods_to_gradebook_ids.items():
            click.echo(f'\tProcessing Period {period}...')
            response = requests.get(SCORES_BY_CLASS_URL.format(gradebook_id=gradebook_id), headers=headers)
            beautiful_soup = BeautifulSoup(response.text, 'html.parser')

            self.periods_to_assignment_information[period] = AeriesData._get_assignment_information(
                beautiful_soup=beautiful_soup
            )

    @staticmethod
    def _get_assignment_information(beautiful_soup: BeautifulSoup) -> dict[str, AeriesAssignmentData]:
        assignments = {}
        for tag in (beautiful_soup
                    .find('table', class_=SCORES_BY_CLASS_ASSIGNMENT_INFO_TABLE_CLASS_NAME)
                    .find_all('th', class_=SCORES_BY_CLASS_ASSIGNMENT_NAME_CLASS_NAME)):
            assignment_description = (tag
                                      .find('tr', class_=ASSIGNMENT_DESC_CLASS_NAME)
                                      .get(ASSIGNMENT_DESC_TAG_NAME))
            description_match = re.match(ASSIGNMENT_NAME_PATTERN, assignment_description)

            if not description_match:
                raise ValueError(f'Unexpected format for Aeries assignment description: {assignment_description}. '
                                 'Expected it to start with "<Assignment number> - "')

            assignment_name = description_match.group(1)

            assignment_point_total_desc = (tag
                                           .find('tr', class_=ASSIGNMENT_SCORES_ROW)
                                           .find('div', class_='ellipsis')
                                           .find('span', title=ASSIGNMENT_TOTAL_SCORE_TITLE)
                                           .string)

            point_total_match = re.match(ASSIGNMENT_POINT_TOTAL_PATTERN, assignment_point_total_desc)

            if not point_total_match:
                raise ValueError(f'Unexpected format for Aeries assignment point total: {assignment_point_total_desc}. '
                                 'Expected it to look like " : <Point total>"')

            assignment_point_total = int(point_total_match.group(1))
            assignment_number = int(tag.get(ASSIGNMENT_NUMBER_TAG_NAME))

            assignment_category = (tag
                                   .find('tr', class_=ASSIGNMENT_DESC_CLASS_NAME)
                                   .find('td', string=ASSIGNMENT_CATEGORY_SEARCH_STRING)
                                   .find_next_sibling()
                                   .string)

            assignments[assignment_name] = AeriesAssignmentData(id=assignment_number,
                                                                point_total=assignment_point_total,
                                                                category=assignment_category)

        return assignments

    def extract_assignment_submissions_from_html(self) -> None:
        """
        Returns a mapping of period -> assignment_id -> student_num -> score
        """
        click.echo('Fetching Assignment submissions from Aeries...')
        headers = {'Accept': 'application/json, text/html, application/xhtml+xml, */*',
                   'Cookie': f's={self.s_cookie}'}

        for period, gradebook_id in self.periods_to_gradebook_ids.items():
            click.echo(f'\tProcessing Period {period}...')
            response = requests.get(SCORES_BY_CLASS_URL.format(gradebook_id=gradebook_id), headers=headers)
            beautiful_soup = BeautifulSoup(response.text, 'html.parser')

            self.periods_to_assignment_submissions[period] = AeriesData._get_assignment_submissions_information(
                beautiful_soup=beautiful_soup
            )

    @staticmethod
    def _get_assignment_submissions_information(beautiful_soup: BeautifulSoup) -> dict[int, dict[int, str]]:
        """
        Returns a mapping of assignment_id -> student_num -> score
        """
        assignment_submissions = {}
        for tag in (beautiful_soup
                    .find('table', class_='assignments')
                    .find_all('td', attrs={'data-stusc': MILPITAS_SCHOOL_CODE})):
            assignment_number = int(tag.get(ASSIGNMENT_NUMBER_TAG_NAME))

            student_number = int(tag.get(STUDENT_NUMBER_TAG_NAME))
            score = tag.get(SCORE_TAG_NAME)

            if assignment_number not in assignment_submissions:
                assignment_submissions[assignment_number] = {}

            assignment_submissions[assignment_number][student_number] = score

        return assignment_submissions

    def extract_gradebook_information_from_html(self) -> None:
        """
        Fetch the gradebook information from Aeries, which includes the weights for each category
        and the term end dates.

        As a byproduct, this function also gets the request verification token which is necessary for POST and PUT
        requests to Aeries.
        """
        click.echo('Fetching Gradebook information (weights and term end dates) for gradebooks...')
        headers = {'Accept': 'application/json, text/html, application/xhtml+xml, */*',
                   'Cookie': f's={self.s_cookie}'}

        for period, gradebook_id in self.periods_to_gradebook_ids.items():
            click.echo(f'\tProcessing Period {period}...')
            response = requests.get(GRADEBOOK_INFORMATION_URL.format(gradebook_id=gradebook_id),
                                    headers=headers)
            beautiful_soup = BeautifulSoup(response.text, 'html.parser')
            categories = AeriesData._get_aeries_category_information(beautiful_soup=beautiful_soup)
            end_term_dates = AeriesData._get_aeries_end_term_information(beautiful_soup=beautiful_soup)

            self.periods_to_gradebook_information[period] = AeriesClassroomData(
                categories=categories,
                end_term_dates=end_term_dates
            )

            self.request_verification_token = response.cookies.get('__RequestVerificationToken')

    @staticmethod
    def _get_aeries_category_information(beautiful_soup: BeautifulSoup) -> dict[str, AeriesCategory]:
        categories = {}
        tags = (beautiful_soup
                .find('table', id=WEIGHT_CATEGORY_TABLE_ID)
                .find_all('input', type=['text', 'number']))
        index = 0
        while index < len(tags):
            tag = tags[index]
            category_id = int(tag.get('data-cat-value'))
            category_name = tag.get('value')

            index += 1
            tag = tags[index]

            weight = int(tag.get('value')) / 100
            categories[category_name] = AeriesCategory(name=category_name,
                                                       weight=weight,
                                                       id=category_id)
            index += 1

        return categories

    @staticmethod
    def _get_aeries_end_term_information(beautiful_soup: BeautifulSoup) -> dict[str, Arrow]:
        end_term_information = {}
        term_table = beautiful_soup.find('table', class_=END_TERMS_TABLE_ID)
        term_names = term_table.find_all('input', class_=GRADEBOOK_TERM_ID)
        term_end_dates = term_table.find_all('td', class_=END_TERMS_END_DATE_ID)

        for term_name, term_end_date in zip_longest(term_names, term_end_dates):
            end_term_information[term_name.get('value')[0]] = Arrow.strptime(
                term_end_date.find('input').get('value').split(' ')[0],
                '%m/%d/%Y',
                'US/Pacific'
            )
        return end_term_information

    def create_aeries_assignment(self,
                                 gradebook_number: str,
                                 assignment_id: int,
                                 assignment_name: str,
                                 point_total: int,
                                 category: AeriesCategory,
                                 end_term_date: Arrow) -> AeriesAssignmentData:
        """
        Create an assignment in Aeries with the given parameters.

        :param gradebook_number: Gradebook number for the class.
        :param assignment_id: Assignment number.
        :param assignment_name: Name of the assignment.
        :param point_total: Total points for the assignment.
        :param category: Category of the assignment.
        :param end_term_date: End term date for the class.
        :return: AeriesAssignmentData object with the assignment id, point total, and category.
        """
        form_request_verification_token = self._get_form_request_verification_token(gradebook_number=gradebook_number)

        time = Arrow.now()
        if time >= end_term_date:
            time = end_term_date.shift(days=-1)

        headers = {'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                   'Cookie': f'__RequestVerificationToken={self.request_verification_token}; s={self.s_cookie}'}
        data = {
            '__RequestVerificationToken': form_request_verification_token,
            'Assignment.GradebookNumber': gradebook_number,
            'SourceGradebook.SchoolCode': MILPITAS_SCHOOL_CODE,
            'SourceGradebook.Name': 'blah',
            'Assignment.AssignmentNumber': assignment_id,
            'Assignment.Description': assignment_name,
            'Assignment.AssignmentType': 'S' if category.name == 'Performance' else 'F',
            'Assignment.Category': category.id,
            'Assignment.DateAssigned': f'{time.month:02d}/{time.day:02d}/{time.year}',
            'Assignment.DateDue': f'{time.month:02d}/{time.day:02d}/{time.year}',
            'Assignment.MaxNumberCorrect': point_total,
            'Assignment.MaxScore': point_total,
            'Assignment.VisibleToParents': True,
            'Assignment.ScoresVisibleToParents': True
        }

        response = requests.post(CREATE_ASSIGNMENT_URL,
                                 params={'gn': gradebook_number, 'an': assignment_id},
                                 data=data,
                                 headers=headers)

        if response.status_code != 200:
            raise ValueError(f'Assignment creation has unexpected status code: {response.status_code}')

        return AeriesAssignmentData(id=assignment_id,
                                    point_total=point_total,
                                    category=category.name)

    def patch_aeries_assignment(self,
                                gradebook_number: str,
                                assignment_id: int,
                                assignment_name: str,
                                point_total: int,
                                category: AeriesCategory,
                                end_term_date: Arrow) -> AeriesAssignmentData:
        """
        Update an assignment in Aeries with the given parameters.

        :param assignment_id: Number of the assignment.
        :param assignment_name: Name of the assignment.
        :param point_total: Total points for the assignment.
        :param category: Category of the assignment.
        :param end_term_date: End term date for the class.
        :return: AeriesAssignmentData object with the assignment id, point total, and category.
        """
        form_request_verification_token = self._get_form_request_verification_token(gradebook_number=gradebook_number)

        time = Arrow.now()
        if time >= end_term_date:
            time = end_term_date.shift(days=-1)

        headers = {'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                   'Cookie': f'__RequestVerificationToken={self.request_verification_token}; s={self.s_cookie}'}
        data = {
            '__RequestVerificationToken': form_request_verification_token,
            'Assignment.GradebookNumber': gradebook_number,
            'SourceGradebook.SchoolCode': MILPITAS_SCHOOL_CODE,
            'SourceGradebook.Name': 'blah',
            'Assignment.AssignmentNumber': assignment_id,
            'Assignment.Description': assignment_name,
            'Assignment.AssignmentType': 'S' if category.name == 'Performance' else 'F',
            'Assignment.Category': category.id,
            'Assignment.DateAssigned': f'{time.month:02d}/{time.day:02d}/{time.year}',
            'Assignment.DateDue': f'{time.month:02d}/{time.day:02d}/{time.year}',
            'Assignment.MaxNumberCorrect': point_total,
            'Assignment.MaxScore': point_total,
            'Assignment.VisibleToParents': True,
            'Assignment.ScoresVisibleToParents': True
        }

        response = requests.put(CREATE_ASSIGNMENT_URL,
                                params={'gn': gradebook_number, 'an': assignment_id},
                                data=data,
                                headers=headers)

        if response.status_code != 200:
            raise ValueError(f'Assignment update has unexpected status code: {response.status_code}')

        return AeriesAssignmentData(id=assignment_id,
                                    point_total=point_total,
                                    category=category.name)

    def _get_form_request_verification_token(self, gradebook_number: str) -> str:
        params = {'gn': gradebook_number,
                  'an': 0}
        headers = {'Cookie': f'__RequestVerificationToken={self.request_verification_token}; s={self.s_cookie}'}

        response = requests.get(CREATE_ASSIGNMENT_URL, params=params, headers=headers)
        beautiful_soup = BeautifulSoup(response.text, 'html.parser')

        return beautiful_soup.find('form').find('input', attrs={'name': '__RequestVerificationToken'}).get('value')

    def update_grades_in_aeries(self, assignment_patch_data: dict[str, list[AssignmentPatchData]]) -> None:
        """
        Update the grades in Aeries with the given patch data.

        :param assignment_patch_data: Mapping of gradebook id to list of AssignmentPatchData objects.
        """
        click.echo('Updating Aeries grades...')
        for gradebook_id, patch_datas in assignment_patch_data.items():
            click.echo(f'\tProcessing Gradebook Number {gradebook_id}...')
            for patch_data in patch_datas:
                self._send_patch_request(gradebook_id=gradebook_id,
                                         assignment_number=patch_data.assignment_number,
                                         student_number=patch_data.student_num,
                                         grade=patch_data.grade)

    def _send_patch_request(self,
                            gradebook_id: str,
                            assignment_number: int,
                            student_number: int,
                            grade: Optional[float]) -> None:
        headers = {
            'content-type': 'application/json; charset=UTF-8',
            'cookie': f's={self.s_cookie}'
        }

        if grade is None:
            grade = ''
        elif grade == 0:
            grade = 'MI'

        data = {
            "SchoolCode": MILPITAS_SCHOOL_CODE,
            "GradebookNumber": gradebook_id[:-2],
            "AssignmentNumber": assignment_number,
            "StudentNumber": student_number,
            "Mark": grade
        }

        requests.post(UPDATE_ASSIGNMENT_GRADE_URL.format(school_code=MILPITAS_SCHOOL_CODE,
                                                         gradebook_id=gradebook_id,
                                                         student_number=student_number,
                                                         assignment_number=assignment_number),
                      params={'fieldName': 'Mark'},
                      headers=headers,
                      json=data)
