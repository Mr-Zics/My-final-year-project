"""
Downloads authentic book cover images for all 30 library catalogue books
directly into static/img/books/ using Open Library Covers API.
"""

import os
import sys
import time
import urllib.request
import urllib.parse
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOKS_DIR = os.path.join(BASE_DIR, "static", "img", "books")
os.makedirs(BOOKS_DIR, exist_ok=True)

# 30 collection books mapping: (filename, search query, fallback_cover_id)
BOOK_LIST = [
    ("algorithms.jpg", "Introduction to Algorithms Cormen", None),
    ("database.jpg", "Database System Concepts Silberschatz", None),
    ("software_engineering.jpg", "Software Engineering Sommerville", 3973371),
    ("computer_networks.jpg", "Computer Networks Tanenbaum", 9378629),
    ("operating_systems.jpg", "Operating System Concepts Silberschatz", 302591),
    ("artificial_intelligence.jpg", "Artificial Intelligence A Modern Approach Russell Norvig", 92018),
    ("clean_code.jpg", "Clean Code Robert Martin", None),
    ("python_crash_course.jpg", "Python Crash Course Eric Matthes", 8800209),
    ("fundamentals_database.jpg", "Fundamentals of Database Systems Elmasri Navathe", 8479708),
    ("systems_analysis.jpg", "Systems Analysis and Design Alan Dennis", 7006856),
    ("computer_organization.jpg", "Computer Organization and Architecture William Stallings", 8459639),
    ("discrete_math.jpg", "Discrete Mathematics and Its Applications Kenneth Rosen", None),
    ("calculus.jpg", "Calculus James Stewart", 364094),
    ("linear_algebra.jpg", "Linear Algebra and Its Applications David Lay", 13054058),
    ("probability_statistics.jpg", "Probability and Statistics for Engineers and Scientists Walpole", 9070857),
    ("advanced_engineering_math.jpg", "Advanced Engineering Mathematics Stroud", 7076997),
    ("electric_circuits.jpg", "Fundamentals of Electric Circuits Alexander Sadiku", None),
    ("thermodynamics.jpg", "Thermodynamics An Engineering Approach Cengel Boles", 8459528),
    ("principles_economics.jpg", "Principles of Economics Gregory Mankiw", 19884),
    ("principles_marketing.jpg", "Principles of Marketing Philip Kotler", 8480397),
    ("financial_accounting.jpg", "Financial Accounting Jerry Weygandt", 8459664),
    ("things_fall_apart.jpg", "Things Fall Apart Chinua Achebe", None),
    ("half_yellow_sun.jpg", "Half of a Yellow Sun Chimamanda Ngozi Adichie", 8472660),
    ("lion_and_jewel.jpg", "The Lion and the Jewel Wole Soyinka", 14319795),
    ("purple_hibiscus.jpg", "Purple Hibiscus Chimamanda Ngozi Adichie", 12063933),
    ("university_physics.jpg", "University Physics Hugh Young Freedman", 8459582),
    ("physics.jpg", "Fundamentals of Physics Halliday Resnick Walker", None),
    ("chemistry.jpg", "Chemistry The Central Science Theodore Brown", 9407725),
    ("craft_of_research.jpg", "The Craft of Research Wayne Booth", 8479635),
    ("how_to_read_a_book.jpg", "How to Read a Book Mortimer Adler", 8479901),
]


def download_cover(filename, query, fallback_id):
    filepath = os.path.join(BOOKS_DIR, filename)
    if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
        print(f"[EXISTS] {filename} ({os.path.getsize(filepath)} bytes)")
        return True

    cover_id = fallback_id

    # If no fallback or we want to search OpenLibrary
    if not cover_id:
        try:
            q = urllib.parse.quote(query)
            search_url = f"https://openlibrary.org/search.json?q={q}&limit=1"
            req = urllib.request.Request(search_url, headers={"User-Agent": "UniLibrary/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
                docs = data.get("docs", [])
                if docs and "cover_i" in docs[0]:
                    cover_id = docs[0]["cover_i"]
        except Exception as e:
            print(f"[SEARCH ERROR] {query}: {e}")

    if cover_id:
        try:
            cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
            req = urllib.request.Request(cover_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read()
                # OpenLibrary returns a 1x1 pixel image or small content if not found
                if len(content) > 1000:
                    with open(filepath, "wb") as f:
                        f.write(content)
                    print(f"[DOWNLOADED] {filename} (from ID {cover_id}, {len(content)} bytes)")
                    return True
                else:
                    print(f"[TOO SMALL] {filename} (ID {cover_id} content only {len(content)} bytes)")
        except Exception as e:
            print(f"[DOWNLOAD ERROR] {filename} (ID {cover_id}): {e}")

    return False


def main():
    print(f"Checking and downloading covers for {len(BOOK_LIST)} books into {BOOKS_DIR}...")
    success = 0
    for filename, query, fallback_id in BOOK_LIST:
        ok = download_cover(filename, query, fallback_id)
        if ok:
            success += 1
        time.sleep(0.3)

    print(f"\nCompleted: {success}/{len(BOOK_LIST)} covers ready.")


if __name__ == "__main__":
    main()
