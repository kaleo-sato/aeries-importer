# aeries-importer
Import grades from Google Classroom to Aeries.

Setup Google authentication using steps here: https://developers.google.com/classroom/quickstart/go

### Algorithm

1. Crawl scoresByClass to get a mapping of student ID and student number.
2. Crawl the list of gradebooks for Gradebook ID.
3. Crawl the list of assignments in each Gradebook to get a list of Assignment IDs.
4. Fetch all student grades for published assignments and questions.
Extrac the student email address to get student number and map to their Aeries ID.
5. Match assignments to their Aeries Assignment ID by crawling the Gradebook for the class.
6. Milpitas School code: 341
7. Use Gradebook ID, Student ID, School Code, Assignment number to patch the grade in Aeries.
8. Validate that the overall grades are accurate and consistent.