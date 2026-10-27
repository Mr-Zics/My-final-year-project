"""
Seed initial categories and books for Phase 2.
Directly implements Section 11.2 and 11.3 of the Build Specification.
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "library_project.settings")
django.setup()

from catalogue.models import Category, Book, Copy
from catalogue.services import create_book


CATEGORIES_DATA = [
    ("Computer Science", "CS"),
    ("Mathematics", "MA"),
    ("Engineering", "EN"),
    ("Economics and Business", "EB"),
    ("Literature", "LI"),
    ("Physics", "PH"),
    ("Chemistry", "CH"),
    ("General Studies", "GS"),
]

BOOKS_DATA = [
    (1, "Introduction to Algorithms", "Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, Clifford Stein", "CS", 2, "Main Library, Shelf CS-1", "9780000000010", "A comprehensive textbook on modern algorithms covering divide and conquer, dynamic programming, and graph algorithms."),
    (2, "Database System Concepts", "Abraham Silberschatz, Henry F. Korth, S. Sudarshan", "CS", 3, "Main Library, Shelf CS-2", "9780000000020", "Fundamental concepts of database management, relational algebra, SQL, transactions, and concurrency control."),
    (3, "Software Engineering", "Ian Sommerville", "CS", 3, "Main Library, Shelf CS-3", "9780000000030", "Comprehensive guide to software design processes, agile methodologies, requirements engineering, and software architectures."),
    (4, "Computer Networks", "Andrew S. Tanenbaum, David J. Wetherall", "CS", 2, "Main Library, Shelf CS-1", "9780000000040", "Detailed principles of network architectures, physical and data link layers, routing algorithms, and transport protocols."),
    (5, "Operating System Concepts", "Abraham Silberschatz, Peter B. Galvin, Greg Gagne", "CS", 3, "Main Library, Shelf CS-2", "9780000000050", "The classic dinosaur book on OS architecture, process scheduling, memory virtualization, and file systems."),
    (6, "Artificial Intelligence: A Modern Approach", "Stuart Russell, Peter Norvig", "CS", 2, "Main Library, Shelf CS-3", "9780000000060", "The authoritative overview of artificial intelligence, intelligent agents, search algorithms, logic, and machine learning."),
    (7, "Clean Code: A Handbook of Agile Software Craftsmanship", "Robert C. Martin", "CS", 2, "Main Library, Shelf CS-1", "9780000000070", "Principles, patterns, and practices of writing readable, maintainable, and robust object-oriented code."),
    (8, "Python Crash Course", "Eric Matthes", "CS", 3, "Main Library, Shelf CS-2", "9780000000080", "Hands-on, project-based introduction to programming in Python, data structures, and web development."),
    (9, "Fundamentals of Database Systems", "Ramez Elmasri, Shamkant B. Navathe", "CS", 2, "Main Library, Shelf CS-3", "9780000000090", "In-depth reference on database modeling, normalization, indexing, query optimization, and transaction processing."),
    (10, "Systems Analysis and Design", "Alan Dennis, Barbara Haley Wixom, Roberta M. Roth", "CS", 2, "Main Library, Shelf CS-1", "9780000000100", "Practical approach to building business information systems, UML modeling, and project management."),
    (11, "Computer Organization and Architecture", "William Stallings", "CS", 2, "Main Library, Shelf CS-2", "9780000000110", "Structure and function of computers, CPU pipelining, cache memory hierarchies, and instruction set architectures."),
    (12, "Discrete Mathematics and Its Applications", "Kenneth H. Rosen", "MA", 3, "Main Library, Shelf MA-1", "9780000000120", "Standard discrete math textbook covering mathematical logic, set theory, combinatorics, and graph theory."),
    (13, "Calculus", "James Stewart", "MA", 3, "Main Library, Shelf MA-2", "9780000000130", "Single and multivariable calculus, derivatives, integrals, infinite series, and vector analysis."),
    (14, "Linear Algebra and Its Applications", "David C. Lay", "MA", 2, "Main Library, Shelf MA-3", "9780000000140", "Core principles of matrix algebra, vector spaces, eigenvalues, eigenvectors, and linear transformations."),
    (15, "Probability and Statistics for Engineers and Scientists", "Ronald E. Walpole et al.", "MA", 2, "Main Library, Shelf MA-1", "9780000000150", "Applied probability models, statistical hypothesis testing, regression analysis, and variance analysis."),
    (16, "Advanced Engineering Mathematics", "K. A. Stroud", "EN", 2, "Main Library, Shelf EN-1", "9780000000160", "Step-by-step mathematical techniques for engineering students including differential equations and Laplace transforms."),
    (17, "Fundamentals of Electric Circuits", "Charles K. Alexander, Matthew N. O. Sadiku", "EN", 2, "Main Library, Shelf EN-2", "9780000000170", "Clear circuit analysis textbook covering Kirchhoff's laws, operational amplifiers, AC analysis, and frequency response."),
    (18, "Thermodynamics: An Engineering Approach", "Yunus A. Cengel, Michael A. Boles", "EN", 2, "Main Library, Shelf EN-3", "9780000000180", "Fundamental laws of thermodynamics, energy transfer, entropy, and refrigeration cycles with engineering applications."),
    (19, "Principles of Economics", "N. Gregory Mankiw", "EB", 3, "Main Library, Shelf EB-1", "9780000000190", "Foundational introduction to microeconomics, macroeconomics, supply and demand, market structures, and monetary policy."),
    (20, "Principles of Marketing", "Philip Kotler, Gary Armstrong", "EB", 2, "Main Library, Shelf EB-2", "9780000000200", "Strategic marketing management, customer value creation, branding, market segmentation, and digital marketing."),
    (21, "Financial Accounting", "Jerry J. Weygandt et al.", "EB", 2, "Main Library, Shelf EB-3", "9780000000210", "Corporate financial reporting, double-entry bookkeeping, balance sheets, income statements, and cash flows."),
    (22, "Things Fall Apart", "Chinua Achebe", "LI", 3, "Main Library, Shelf LI-1", "9780000000220", "The seminal African novel chronicling Okonkwo and the Igbo community during the onset of British colonialism."),
    (23, "Half of a Yellow Sun", "Chimamanda Ngozi Adichie", "LI", 2, "Main Library, Shelf LI-2", "9780000000230", "Haunting historical fiction following three characters caught in the turmoil of the Nigerian Civil War."),
    (24, "The Lion and the Jewel", "Wole Soyinka", "LI", 2, "Main Library, Shelf LI-3", "9780000000240", "Vibrant comic play contrasting modern westernization and Yoruba traditional heritage in Ilujinle."),
    (25, "Purple Hibiscus", "Chimamanda Ngozi Adichie", "LI", 2, "Main Library, Shelf LI-1", "9780000000250", "A coming-of-age story of Kambili Achike set amidst domestic tyranny and political upheaval in Enugu."),
    (26, "University Physics", "Hugh D. Young, Roger A. Freedman", "PH", 2, "Main Library, Shelf PH-1", "9780000000260", "Calculus-based physics textbook covering classical mechanics, thermodynamics, electromagnetism, and optics."),
    (27, "Fundamentals of Physics", "David Halliday, Robert Resnick, Jearl Walker", "PH", 2, "Main Library, Shelf PH-2", "9780000000270", "Renowned physics reference on mechanics, wave phenomena, relativity, and quantum fundamentals."),
    (28, "Chemistry: The Central Science", "Theodore L. Brown et al.", "CH", 2, "Main Library, Shelf CH-1", "9780000000280", "Authoritative general chemistry text on atomic structure, chemical bonding, stoichiometry, and kinetics."),
    (29, "The Craft of Research", "Wayne C. Booth, Gregory G. Colomb, Joseph M. Williams", "GS", 2, "Main Library, Shelf GS-1", "9780000000290", "Essential guide to formulating research questions, structuring arguments, evaluating evidence, and writing academic papers."),
    (30, "How to Read a Book", "Mortimer J. Adler, Charles Van Doren", "GS", 2, "Main Library, Shelf GS-2", "9780000000300", "Classic guide to intelligent reading, analytical reading levels, inspectional synthesis, and critical thinking."),
]


def seed():
    print("Seeding Phase 2 categories and books...")

    category_map = {}
    for name, code in CATEGORIES_DATA:
        cat, created = Category.objects.get_or_create(
            category_name=name,
            defaults={"code": code}
        )
        category_map[code] = cat

    print(f"Created/verified {len(category_map)} categories.")

    books_created = 0
    copies_created = 0

    for num, title, author, cat_code, num_copies, location, isbn, desc in BOOKS_DATA:
        category = category_map[cat_code]
        if not Book.objects.filter(isbn=isbn).exists():
            book = create_book(
                title=title,
                author=author,
                isbn=isbn,
                category=category,
                num_copies=num_copies,
                location=location,
                description=desc
            )
            books_created += 1
            copies_created += num_copies

    print(f"Seeding completed: {books_created} books created, {copies_created} copies generated.")
    print(f"Total in Database: {Category.objects.count()} categories, {Book.objects.count()} books, {Copy.objects.count()} physical copies.")


if __name__ == "__main__":
    seed()
