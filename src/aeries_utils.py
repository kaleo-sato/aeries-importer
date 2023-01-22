import re
from collections.abc import Iterable
from dataclasses import dataclass

from bs4 import BeautifulSoup
import requests

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
ASSIGNMENT_DESC_CLASS_NAME = 'description row cursor-hand'
ASSIGNMENT_DESC_TAG_NAME = 'data-assignment-desc'
ASSIGNMENT_NAME_PATTERN = r'^[0-9]+ - (.+)'
ASSIGNMENT_POINT_TOTAL_PATTERN = r' : ([0-9]+)'
ASSIGNMENT_NUMBER_TAG_NAME = 'data-an'
ASSIGNMENT_SCORES_ROW = 'scores row'
ASSIGNMENT_TOTAL_SCORE_TITLE = '# Correct Possible'


@dataclass(frozen=True)
class Assignment:
    id: int
    name: str
    point_total: int


def extract_gradebook_ids_from_html(periods: list[int],
                                    aeries_cookie: str) -> dict[int, str]:
    headers = {'Accept': 'application/json, text/html, application/xhtml+xml, */*',
               'Cookie': f's={aeries_cookie}'}
    response = requests.get(GRADEBOOK_URL, headers=headers)
    beautiful_soup = BeautifulSoup(response.text, 'html.parser')

    return _get_periods_to_gradebook_and_term(periods=periods,
                                              beautiful_soup=beautiful_soup)


def _get_periods_to_gradebook_and_term(periods: list[int],
                                       beautiful_soup: BeautifulSoup) -> dict[int, str]:
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
        if period_num in periods:
            periods_to_gradebook_and_term[period_num] = gradebook_and_term

    if len(periods_to_gradebook_and_term) != len(periods):
        raise ValueError(
            'Periods specified were not matched to the Aeries class gradebook.\n'
            f'Periods wanted: {", ".join(str(period) for period in sorted(periods))}\n'
            f'Periods found in Aeries: {", ".join(str(period) for period in sorted(periods_to_gradebook_and_term))}'
        )

    return periods_to_gradebook_and_term


def extract_student_ids_to_student_nums_from_html(periods_to_gradebook_ids: dict[int, str],
                                                  aeries_cookie: str) -> Iterable[int]:
    headers = {'Accept': 'application/json, text/html, application/xhtml+xml, */*',
               'Cookie': f's={aeries_cookie}'}

    periods_to_student_ids_and_student_nums = dict()
    for period, gradebook_id in periods_to_gradebook_ids.items():
        response = requests.get(SCORES_BY_CLASS_URL.format(gradebook_id=gradebook_id), headers=headers)
        beautiful_soup = BeautifulSoup(response.text, 'html.parser')

        periods_to_student_ids_and_student_nums[period] = _get_student_ids_to_student_nums(
            beautiful_soup=beautiful_soup
        )

    return periods_to_student_ids_and_student_nums


def _get_student_ids_to_student_nums(beautiful_soup: BeautifulSoup) -> dict[int, int]:
    student_ids_to_student_nums = dict()
    for tag in (beautiful_soup
                .find('table', class_=SCORES_BY_CLASS_STUDENT_INFO_TABLE_CLASS_NAME)
                .find_all('tr', class_='row')):
        student_number = int(tag.get(STUDENT_NUMBER_TAG_NAME))
        student_id = int(tag.get(STUDENT_ID_TAG_NAME))

        student_ids_to_student_nums[student_id] = student_number

    return student_ids_to_student_nums


def extract_assignment_information_from_html(periods_to_gradebook_ids: dict[int, str],
                                             aeries_cookie: str) -> dict[int, list[Assignment]]:
    headers = {'Accept': 'application/json, text/html, application/xhtml+xml, */*',
               'Cookie': f's={aeries_cookie}'}

    periods_to_assignment_information = dict()
    for period, gradebook_id in periods_to_gradebook_ids.items():
        response = requests.get(SCORES_BY_CLASS_URL.format(gradebook_id=gradebook_id), headers=headers)
        beautiful_soup = BeautifulSoup(response.text, 'html.parser')

        periods_to_assignment_information[period] = _get_assignment_information(beautiful_soup=beautiful_soup)

    return periods_to_assignment_information


def _get_assignment_information(beautiful_soup: BeautifulSoup) -> list[Assignment]:
    assignments = []
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

        assignment_point_total_match = (tag
                                        .find('tr', class_=ASSIGNMENT_SCORES_ROW)
                                        .find('div', class_='ellipsis')
                                        .find('span', title=ASSIGNMENT_TOTAL_SCORE_TITLE)
                                        .string)

        point_total_match = re.match(ASSIGNMENT_POINT_TOTAL_PATTERN, assignment_point_total_match)

        if not point_total_match:
            raise ValueError(f'Unexpected format for Aeries assignment point total: {assignment_description}. '
                             'Expected it to look like " : <Point total>"')

        assignment_point_total = int(point_total_match.group(1))
        assignment_number = int(tag.get(ASSIGNMENT_NUMBER_TAG_NAME))

        assignments.append(Assignment(id=assignment_number,
                                      name=assignment_name,
                                      point_total=assignment_point_total))

    return assignments
